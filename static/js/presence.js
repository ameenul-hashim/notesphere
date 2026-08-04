/**
 * NoteSphere Realtime Presence System
 * ─────────────────────────────────────────────────────────────────────────────
 * Production-grade, Discord/WhatsApp-style browser presence built on Firestore.
 *
 * Architecture
 * ────────────
 *   Django is the authentication source of truth. Firebase is ONLY the realtime
 *   layer. Each browser tab owns one session document:
 *
 *     users/user_{uid}                       -> aggregated presence (status, counter,
 *                                                profile, current_page)
 *     users/user_{uid}/sessions/{session_id} -> one per browser tab/device
 *
 *   A user is ONLINE iff at least one of their sessions has a fresh heartbeat.
 *   Multi-tab and multi-device sessions aggregate into a single online user.
 *
 * Lifecycle
 * ─────────
 *   - Open page        -> ensureSession()  (transaction: create session, bump counter)
 *   - Heartbeat        -> every 20s via a Web Worker (immune to background-tab
 *                         timer throttling); falls back to setInterval
 *   - Close tab        -> pagehide best-effort endSession() + heartbeat timeout backstop
 *   - Crash / sleep /  -> session heartbeats go stale; the owner's reconcile
 *     lost network        (every 20s) and an elected global sweep delete them;
 *                         ghost "online" docs are filtered client-side by the
 *                         last_seen freshness window (no unsafe cross-user writes)
 *   - Reconnect        -> `online` event re-runs ensureSession() automatically
 *
 * Offline detection is heartbeat-based (Firestore has no onDisconnect), so
 * abrupt closure recovers within ~STALE_SESSION_MS + sweep interval.
 *
 * Future features (typing indicators, DMs, live classroom, presence activities)
 * can consume the user documents and window.NoteSpherePresence API without any
 * redesign of this module.
 */
(function () {
  'use strict';

  var CFG = {
    HEARTBEAT_MS: 20000,        // how often a tab refreshes its session heartbeat
    STALE_SESSION_MS: 90000,    // a session older than this is considered dead
    RECONCILE_MS: 20000,        // how often a client reconciles its OWN user doc
    SWEEP_MS: 20000,            // how often an elected client sweeps the cluster
    SWEEP_RATE: 0.12,           // fraction of sessions elected as global sweeper
    LAST_SEEN_REFRESH_EVERY: 3, // refresh user doc last_seen every N heartbeats
    ONLINE_WINDOW_MS: 120000,   // user considered offline if last_seen older than this
  };

  var FB = null;                 // window.NoteSphereFB (after Firebase auth)
  var timers = null;             // { worker, interval }
  var state = {
    ready: false,
    sessionId: null,
    online: false,
    sweepEligible: false,
    heartbeatsSinceRefresh: 0,
  };

  var onlineUsers = {};          // uid -> user doc data (for the exposed API)
  var listeners = [];            // subscribers notified on online-set changes

  /* ─────────────────────────── identity helpers ─────────────────────────── */

  function me() {
    return window.CURRENT_USER_JSON || {};
  }

  function uid() {
    var id = me().id;
    return id === undefined || id === null ? null : String(id);
  }

  function ownUserRef() {
    return FB.db.collection('users').doc('user_' + uid());
  }

  function ownSessionRef() {
    return ownUserRef().collection('sessions').doc(state.sessionId);
  }

  function getDeviceId() {
    try {
      var key = 'ns_presence_device';
      var existing = localStorage.getItem(key);
      if (existing) return existing;
      var created = 'dev_' + Math.random().toString(36).substr(2, 10);
      localStorage.setItem(key, created);
      return created;
    } catch (e) {
      return 'dev_' + Math.random().toString(36).substr(2, 10);
    }
  }

  function getSessionId() {
    // sessionStorage survives same-tab navigation (no churn on refresh) but is
    // unique per tab/incognito and is cleared when the tab closes.
    try {
      var key = 'ns_presence_session';
      var existing = sessionStorage.getItem(key);
      if (existing) return existing;
      var created = 'sess_' + Math.random().toString(36).substr(2, 9);
      sessionStorage.setItem(key, created);
      return created;
    } catch (e) {
      return 'sess_' + Math.random().toString(36).substr(2, 9);
    }
  }

  function clearSessionId() {
    try { sessionStorage.removeItem('ns_presence_session'); } catch (e) { /* ignore */ }
  }

  function detectDeviceLabel() {
    var ua = navigator.userAgent || '';
    if (/iPhone|iPad|iPod/i.test(ua)) return 'Mobile';
    if (/Android/i.test(ua)) return 'Mobile';
    if (/Mac|Windows|Linux/i.test(ua)) return 'Desktop';
    return 'Web';
  }

  function currentPage() {
    return location.pathname + location.search;
  }

  function toMillis(ts) {
    if (!ts) return null;
    return ts.toMillis ? ts.toMillis() : (ts instanceof Date ? ts.getTime() : Number(ts));
  }

  function isStaleTs(ts, now, windowMs) {
    var ms = toMillis(ts);
    if (ms == null) return false;
    return now - ms > (windowMs || CFG.STALE_SESSION_MS);
  }

  function timestamp() {
    return FB.serverTimestamp();
  }

  /* ─────────────────────────── document payloads ─────────────────────────── */

  function sessionPayload() {
    return {
      session_id: state.sessionId,
      user_id: uid(),
      device_id: getDeviceId(),
      device_label: detectDeviceLabel(),
      created_at: timestamp(),
      heartbeat: timestamp(),
      current_page: currentPage(),
    };
  }

  function userDocPayload(activeSessions, status) {
    var u = me();
    var reg = (window.USER_REGISTRY || {})[String(u.id)] || {};
    return {
      uid: uid(),
      status: status,
      role: u.role,
      display_name: u.full_name || reg.name || u.username,
      avatar_url: u.avatar_url || reg.avatar_url || '',
      active_sessions: activeSessions,
      last_seen: timestamp(),
      last_active: timestamp(),
      current_page: currentPage(),
    };
  }

  /* ─────────────────────────── write operations ─────────────────────────── */

  /**
   * Create (or re-create) this tab's session and bump the user's session count.
   * Runs in a transaction so the counter can never drift from concurrent tabs.
   * Safe to call repeatedly (idempotent per session id).
   */
  function ensureSession() {
    if (!FB || !FB.isReady || !uid() || !state.sessionId) return Promise.resolve();

    var sessionRef = ownSessionRef();
    var userRef = ownUserRef();

    return FB.db.runTransaction(function (tx) {
      return tx.get(sessionRef).then(function (sessSnap) {
        if (sessSnap.exists) {
          tx.update(sessionRef, {
            heartbeat: timestamp(),
            current_page: currentPage(),
            user_id: uid(),
            session_id: state.sessionId,
          });
          return;
        }
        return tx.get(userRef).then(function (userSnap) {
          var count = userSnap.exists ? (userSnap.data().active_sessions || 0) : 0;
          tx.set(sessionRef, sessionPayload());
          tx.set(userRef, userDocPayload(count + 1, 'online'), { merge: true });
        });
      });
    }).then(function () {
      state.online = true;
      return true;
    }).catch(function (err) {
      console.warn('[presence] ensureSession failed', err);
      return false;
    });
  }

  /** Cheap heartbeat: single-document merge write, every HEARTBEAT_MS. */
  function heartbeat() {
    if (!FB || !FB.isReady || !state.sessionId) return Promise.resolve(false);

    var sessionRef = ownSessionRef();
    return sessionRef.set({
      heartbeat: timestamp(),
      current_page: currentPage(),
      user_id: uid(),
      session_id: state.sessionId,
    }, { merge: true }).then(function () {
      state.online = true;
      state.heartbeatsSinceRefresh += 1;
      if (state.heartbeatsSinceRefresh >= CFG.LAST_SEEN_REFRESH_EVERY) {
        state.heartbeatsSinceRefresh = 0;
        return ownUserRef().set({
          last_seen: timestamp(),
          last_active: timestamp(),
          current_page: currentPage(),
        }, { merge: true }).then(function () { return true; });
      }
      return true;
    }).catch(function (err) {
      // Write failed (offline). The session will be reaped if it stays stale;
      // the `online` event will re-run ensureSession().
      console.warn('[presence] heartbeat failed', err);
      return false;
    });
  }

  /**
   * Tear down this tab's session and, if it was the last one, mark the user
   * offline. Best-effort: called from pagehide/logout. Abrupt crashes are
   * covered by the heartbeat timeout + sweeper instead.
   */
  function endSession() {
    if (!FB || !FB.isReady || !state.sessionId || !uid()) return Promise.resolve(false);

    var sessionRef = ownSessionRef();
    var userRef = ownUserRef();

    return FB.db.runTransaction(function (tx) {
      return tx.get(sessionRef).then(function (sessSnap) {
        if (!sessSnap.exists) return;
        tx.delete(sessionRef);
        return tx.get(userRef).then(function (userSnap) {
          if (!userSnap.exists) return;
          var count = (userSnap.data().active_sessions || 0) - 1;
          if (count <= 0) {
            tx.set(userRef, {
              status: 'offline',
              active_sessions: 0,
              last_seen: timestamp(),
              last_active: timestamp(),
            }, { merge: true });
          } else {
            tx.set(userRef, { active_sessions: count }, { merge: true });
          }
        });
      });
    }).then(function () {
      state.online = false;
      return true;
    }).catch(function (err) {
      console.warn('[presence] endSession failed', err);
      return false;
    });
  }

  /**
   * Authoritative per-user reconciliation, run by every connected client for
   * its OWN user: delete stale sessions, then align active_sessions / status to
   * reality. This is what makes same-user multi-tab crashes self-heal without
   * any global coordination.
   */
  function reconcileOwn() {
    if (!FB || !FB.isReady || !uid()) return Promise.resolve();

    var userRef = ownUserRef();
    var now = Date.now();

    return userRef.collection('sessions').get().then(function (snap) {
      var stale = [];
      snap.docs.forEach(function (doc) {
        if (isStaleTs(doc.data().heartbeat, now)) stale.push(doc.ref);
      });
      return Promise.all(stale.map(function (ref) {
        return ref.delete().catch(function () { /* already gone */ });
      })).then(function () {
        var count = snap.size - stale.length;
        if (count > 0) {
          return userRef.set({
            active_sessions: count,
            status: 'online',
            last_seen: timestamp(),
          }, { merge: true });
        }
        // This tab believes it is online but found no live session of its own
        // (e.g. it was reaped during an outage). Align the count and let the
        // `online`/visibility handlers re-create the session.
        return userRef.set({ active_sessions: 0, status: 'offline' }, { merge: true });
      });
    }).catch(function () { /* ignore transient errors */ });
  }

  /**
   * Global sweep, run ONLY by elected clients. Deletes session documents whose
   * owner has gone quiet (crash/sleep with no surviving tab). Online users are
   * never affected: Firestore rules refuse to delete any session whose
   * heartbeat is fresher than STALE_SESSION_MS, and the transaction re-checks
   * staleness against the latest data before deleting.
   *
   * The sweep deliberately does NOT rewrite the owner's user document (rules
   * can never safely allow a client to change another user's presence state).
   * Ghosts in the online list are instead handled client-side by the
   * last_seen freshness filter in startOnlineListener().
   */
  function sweepGlobal() {
    if (!FB || !FB.isReady || !state.sweepEligible) return Promise.resolve();

    var cutoff = new Date(Date.now() - CFG.STALE_SESSION_MS);

    return FB.db.collectionGroup('sessions')
      .where('heartbeat', '<', cutoff)
      .orderBy('heartbeat', 'asc')
      .limit(50)
      .get()
      .then(function (snap) {
        var jobs = snap.docs.map(function (doc) {
          var ownerUid = doc.data().user_id;
          if (ownerUid == null || String(ownerUid) === uid()) return Promise.resolve();
          return FB.db.runTransaction(function (tx) {
            return tx.get(doc.ref).then(function (current) {
              if (!current.exists) return;
              if (!isStaleTs(current.data().heartbeat, Date.now())) return; // re-check inside tx
              tx.delete(doc.ref);
            });
          }).catch(function () { /* raced with another sweeper */ });
        });
        return Promise.all(jobs);
      })
      .catch(function () { /* ignore */ });
  }

  /* ─────────────────────────── online members UI ─────────────────────────── */

  function roleLabel(role) {
    if (role === 'ADMIN') return 'Administrator';
    if (role === 'STUDENT') return 'Student';
    return role || '';
  }

  function resolveProfile(doc) {
    var data = doc.data() || {};
    var key = String(doc.id.replace(/^user_/, ''));
    var reg = (window.USER_REGISTRY || {})[key] || {};
    return {
      uid: String(data.uid != null ? data.uid : key),
      display_name: data.display_name || reg.name || 'User',
      role: data.role || reg.role || 'STUDENT',
      avatar_url: data.avatar_url || reg.avatar_url || '',
      current_page: data.current_page || '',
      active_sessions: data.active_sessions || 1,
    };
  }

  function avatarHtml(url, name) {
    if (url) {
      return '<img src="' + escapeAttr(url) + '" alt="" class="w-full h-full object-cover">';
    }
    var initial = escapeHtml((name || '?').charAt(0).toUpperCase());
    return '<span class="flex items-center justify-center w-full h-full">' + initial + '</span>';
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function escapeAttr(s) { return escapeHtml(s); }

  function renderSidebarItem(profile) {
    var mine = profile.uid === uid();
    var adminBadge = profile.role === 'ADMIN'
      ? '<span class="badge badge-warning text-[9px] px-1.5 py-0">Admin</span>'
      : '';
    var youBadge = mine
      ? '<span class="badge badge-primary text-[9px] px-1.5 py-0 font-bold ml-1">You</span>'
      : '';
    var el = document.createElement('div');
    el.className = 'online-member-item flex items-center justify-between p-2.5 rounded-xl bg-surface-2/60 hover:bg-surface-2 border border-border/50 transition-all';
    el.setAttribute('data-user-id', profile.uid);
    el.innerHTML =
      '<div class="flex items-center gap-2.5 min-w-0">' +
        '<div class="relative w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center font-bold text-xs flex-shrink-0 border border-emerald-500/40 overflow-hidden">' +
          avatarHtml(profile.avatar_url, profile.display_name) +
          '<span class="online-indicator absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-surface animate-pulse"></span>' +
        '</div>' +
        '<div class="truncate">' +
          '<span class="text-xs font-bold text-foreground truncate block leading-tight">' + escapeHtml(profile.display_name) + youBadge + '</span>' +
          '<span class="online-status-text text-[10px] text-emerald-500 font-medium">' + roleLabel(profile.role) + ' &middot; online</span>' +
        '</div>' +
      '</div>' +
      adminBadge;
    return el;
  }

  function renderDrawerItem(profile) {
    var mine = profile.uid === uid();
    var el = document.createElement('div');
    el.className = 'drawer-member-item flex flex-shrink-0 items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-2 border border-border text-foreground text-xs font-semibold';
    el.setAttribute('data-user-id', profile.uid);
    el.innerHTML =
      '<span class="drawer-online-dot w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>' +
      '<span>' + escapeHtml(profile.display_name) + (mine ? ' (You)' : '') + '</span>';
    return el;
  }

  function updateCounts(count) {
    var sub = document.getElementById('chat-online-subtitle');
    if (sub) sub.textContent = count + (count === 1 ? ' member online' : ' members online');
  }

  function renderOnlinePanels() {
    var profiles = Object.keys(onlineUsers)
      .map(function (k) { return onlineUsers[k]; })
      .sort(function (a, b) {
        var roleOrder = { ADMIN: 0, STUDENT: 1 };
        var ra = roleOrder[a.role] != null ? roleOrder[a.role] : 2;
        var rb = roleOrder[b.role] != null ? roleOrder[b.role] : 2;
        if (ra !== rb) return ra - rb;
        return a.display_name.localeCompare(b.display_name);
      });

    var sidebar = document.getElementById('chat-online-users-sidebar');
    if (sidebar) {
      sidebar.textContent = '';
      if (profiles.length === 0) {
        var empty = document.createElement('div');
        empty.className = 'p-3 text-center text-xs text-muted';
        empty.textContent = 'No members online';
        sidebar.appendChild(empty);
      } else {
        profiles.forEach(function (p) { sidebar.appendChild(renderSidebarItem(p)); });
      }
    }

    var drawer = document.getElementById('chat-online-users-drawer');
    if (drawer) {
      drawer.textContent = '';
      profiles.forEach(function (p) { drawer.appendChild(renderDrawerItem(p)); });
    }

    updateCounts(profiles.length);
  }

  function updateMemberGrid() {
    var grid = document.getElementById('members-grid');
    if (!grid) return;
    grid.querySelectorAll('.member-card').forEach(function (card) {
      var key = card.getAttribute('data-member-id');
      var isOnline = key != null && !!onlineUsers[String(key)];
      var dot = card.querySelector('.member-status-dot');
      var label = card.querySelector('.member-status-label');
      if (dot) {
        if (isOnline) {
          dot.className = 'member-status-dot absolute top-2 right-2 w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse border-2 border-surface-2';
          dot.title = 'Online';
          dot.classList.remove('hidden');
        } else {
          dot.classList.add('hidden');
        }
      }
      if (label) {
        if (isOnline) {
          label.textContent = 'Online';
          label.className = 'member-status-label text-[10px] font-semibold text-emerald-500 mt-1';
          label.classList.remove('hidden');
        } else {
          label.classList.add('hidden');
        }
      }
    });
  }

  function startOnlineListener() {
    FB.db.collection('users')
      .where('status', '==', 'online')
      .onSnapshot(function (snap) {
        var now = Date.now();
        onlineUsers = {};
        snap.forEach(function (doc) {
          var data = doc.data() || {};
          // A `status: online` doc whose last_seen has gone stale is a ghost
          // (the owner's last tab crashed/slept without a pagehide). The sweeper
          // deletes stale sessions but, for security, never touches another
          // user's doc — so we filter on freshness here instead.
          var lastSeenMs = toMillis(data.last_seen);
          if (lastSeenMs == null) return;
          if (now - lastSeenMs > CFG.ONLINE_WINDOW_MS) return;
          var p = resolveProfile(doc);
          onlineUsers[p.uid] = p;
        });
        renderOnlinePanels();
        updateMemberGrid();
        listeners.forEach(function (cb) { cb(Object.keys(onlineUsers)); });
      }, function (err) {
        console.warn('[presence] online users listener failed', err);
      });
  }

  /* ─────────────────────────── lifecycle wiring ─────────────────────────── */

  function startHeartbeat() {
    // Dedicated Web Worker keeps heartbeats flowing while the tab is in the
    // background (browsers otherwise throttle setInterval to ~1/min).
    try {
      if (window.PRESENCE_WORKER_URL && typeof Worker !== 'undefined') {
        var worker = new Worker(window.PRESENCE_WORKER_URL);
        worker.onmessage = function (e) {
          if (e.data === 'tick') heartbeat();
        };
        timers = { worker: worker };
        return;
      }
    } catch (e) { /* fall through to setInterval */ }

    timers = timers || {};
    timers.interval = setInterval(function () { heartbeat(); }, CFG.HEARTBEAT_MS);
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible') {
      heartbeat();
      ensureSession();
    }
  }

  function onOnline() {
    // Network recovered: heal this session in case it was reaped while offline.
    ensureSession();
    heartbeat();
  }

  function onPageHide() {
    endSession();
  }

  function onLogoutSubmit() {
    state.ready = false;
    endSession().then(function () {
      if (FB && FB.auth && FB.auth.currentUser) {
        FB.auth.signOut().catch(function () { /* ignore */ });
      }
      clearSessionId();
      if (timers && timers.worker) { try { timers.worker.terminate(); } catch (e) { /* ignore */ } }
      if (timers && timers.interval) clearInterval(timers.interval);
    });
  }

  function bindLogoutForms() {
    document.querySelectorAll("form[action*='logout']").forEach(function (form) {
      form.addEventListener('submit', onLogoutSubmit);
    });
  }

  function boot() {
    if (state.ready) return;
    if (!window.NoteSphereFB || !window.NoteSphereFB.isReady || !uid()) return;

    FB = window.NoteSphereFB;
    state.sessionId = getSessionId();
    // Deterministic election so only ~SWEEP_RATE of clients run the global sweep.
    state.sweepEligible = Math.random() < CFG.SWEEP_RATE;
    state.ready = true;

    startHeartbeat();
    bindLogoutForms();

    window.addEventListener('online', onOnline);
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('pagehide', onPageHide);

    // Only mark ourselves online AFTER Firebase auth has succeeded.
    ensureSession().then(function () {
      startOnlineListener();
      // Periodic tasks
      setInterval(reconcileOwn, CFG.RECONCILE_MS);
      setInterval(sweepGlobal, CFG.SWEEP_MS);
      heartbeat();
    });
  }

  document.addEventListener('NoteSphereFBReady', boot);
  if (window.NoteSphereFB && window.NoteSphereFB.isReady) boot();

  /* ─────────────────────────── public API ─────────────────────────── */

  window.NoteSpherePresence = {
    isOnline: function () { return state.online; },
    getOnlineUsers: function () { return onlineUsers; },
    setCurrentPage: function (page) {
      try { history.replaceState(null, '', page); } catch (e) { /* ignore */ }
      heartbeat();
    },
    onOnlineUsersChange: function (cb) {
      if (typeof cb === 'function') listeners.push(cb);
      return function () {
        var i = listeners.indexOf(cb);
        if (i >= 0) listeners.splice(i, 1);
      };
    },
  };
})();
