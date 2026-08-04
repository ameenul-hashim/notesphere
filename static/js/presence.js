/**
 * NoteSphere Presence — Firebase Realtime Database
 * ─────────────────────────────────────────────────────────────────────────────
 * Uses Firebase Realtime Database (NOT Firestore) for presence tracking.
 *
 * • onDisconnect() automatically removes user when connection drops
 * • localStorage persists identity across refreshes (portal-userId)
 * • Heartbeat every 10s keeps lastActive fresh
 * • Stale cleanup (>90s) removes dead nodes
 * • Grace period (6s) prevents flickering on quick reconnects
 */
(function () {
  'use strict';

  var FB = null;
  var userName = '';
  var userId = '';
  var myPresenceRef = null;
  var heartbeatTimer = null;
  var latestPresenceData = {};
  var staleThreshold = 90000;   // 90 seconds
  var activeThreshold = 35000;  // 35 seconds
  var gracePeriod = 6000;       // 6 seconds
  var removedCache = {};        // key -> timestamp of removal (for grace period)

  function me() { return window.CURRENT_USER_JSON || {}; }

  /* ─── localStorage Identity ─────────────────────────────────── */

  function initIdentity() {
    userName = localStorage.getItem('portal-username') || me().full_name || me().username || 'User';
    userId = localStorage.getItem('portal-userId');
    if (!userId) {
      userId = 'u_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('portal-userId', userId);
    }
    localStorage.setItem('portal-username', userName);
  }

  /* ─── Presence Write ────────────────────────────────────────── */

  function writePresence() {
    if (!FB || !FB.rtdb || !myPresenceRef) return;
    myPresenceRef.set({
      name: userName,
      userId: userId,
      lastActive: firebase.database.ServerValue.TIMESTAMP,
    }).catch(function (e) {
      console.warn('[presence] write failed', e);
    });
  }

  /* ─── Heartbeat Loop (every 10s) ────────────────────────────── */

  function startHeartbeat() {
    heartbeatTimer = setInterval(writePresence, 10000);
  }

  /* ─── Online Count & Filtering ──────────────────────────────── */

  function updateOnlineCount() {
    var now = Date.now();
    var activeCount = 0;
    var keys = Object.keys(latestPresenceData);

    keys.forEach(function (key) {
      var entry = latestPresenceData[key];
      if (!entry) return;
      var lastActive = entry.lastActive || 0;

      // Stale cleanup: remove dead nodes older than 90s
      if (now - lastActive > staleThreshold) {
        FB.rtdb.ref('presence_v2/' + key).remove().catch(function () {});
        delete latestPresenceData[key];
        return;
      }

      // Active check: count if lastActive within 35s
      if (now - lastActive < activeThreshold) {
        activeCount++;
      }
    });

    renderOnlinePanel(activeCount);
  }

  /* ─── Render Online Users Panel ─────────────────────────────── */

  function renderOnlinePanel(count) {
    var el = document.getElementById('chat-online-users-sidebar');
    if (el) {
      el.textContent = '';
      if (count === 0) {
        el.innerHTML = '<div class="p-3 text-center text-xs text-muted">No members online</div>';
      } else {
        var now = Date.now();
        Object.keys(latestPresenceData).forEach(function (key) {
          var entry = latestPresenceData[key];
          if (!entry) return;
          if (now - (entry.lastActive || 0) > activeThreshold) return;

          var item = document.createElement('div');
          item.className = 'online-member-item flex items-center justify-between p-2.5 rounded-xl bg-surface-2/60 hover:bg-surface-2 border border-border/50 transition-all';
          item.setAttribute('data-user-id', entry.userId || key);

          var initial = (entry.name || '?').charAt(0).toUpperCase();
          item.innerHTML =
            '<div class="flex items-center gap-2.5 min-w-0">' +
              '<div class="relative w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center font-bold text-xs flex-shrink-0 border border-emerald-500/40">' +
                '<span>' + escHtml(initial) + '</span>' +
                '<span class="online-indicator absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-surface animate-pulse"></span>' +
              '</div>' +
              '<div class="truncate">' +
                '<span class="text-xs font-bold text-foreground truncate block leading-tight">' + escHtml(entry.name) + '</span>' +
                '<span class="online-status-text text-[10px] text-emerald-500 font-medium">Online</span>' +
              '</div>' +
            '</div>';
          el.appendChild(item);
        });
      }
    }

    var drawer = document.getElementById('chat-online-users-drawer');
    if (drawer) {
      drawer.textContent = '';
      var now = Date.now();
      Object.keys(latestPresenceData).forEach(function (key) {
        var entry = latestPresenceData[key];
        if (!entry) return;
        if (now - (entry.lastActive || 0) > activeThreshold) return;

        var item = document.createElement('div');
        item.className = 'drawer-member-item flex flex-shrink-0 items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-2 border border-border text-foreground text-xs font-semibold';
        item.setAttribute('data-user-id', entry.userId || key);
        item.innerHTML =
          '<span class="drawer-online-dot w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>' +
          '<span>' + escHtml(entry.name) + '</span>';
        drawer.appendChild(item);
      });
    }

    var sub = document.getElementById('chat-online-subtitle');
    if (sub) sub.textContent = count + (count === 1 ? ' member online' : ' members online');
  }

  function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ─── Boot ──────────────────────────────────────────────────── */

  function boot() {
    if (!window.NoteSphereFB || !window.NoteSphereFB.isReady || !me().id) return;
    FB = window.NoteSphereFB;

    initIdentity();
    myPresenceRef = FB.rtdb.ref('presence_v2/' + userId);

    // Write presence on connect
    FB.rtdb.ref('.info/connected').on('value', function (snap) {
      if (snap.val() === true) {
        writePresence();

        // Arm onDisconnect — Firebase server removes node if connection drops
        myPresenceRef.onDisconnect().remove();

        startHeartbeat();
      }
    });

    // Listen for all presence changes
    FB.rtdb.ref('presence_v2').on('value', function (snapshot) {
      latestPresenceData = snapshot.val() || {};
      updateOnlineCount();
    });

    // Clean up on logout
    document.querySelectorAll("form[action*='logout']").forEach(function (form) {
      form.addEventListener('submit', function () {
        clearInterval(heartbeatTimer);
        myPresenceRef.remove().catch(function () {});
        localStorage.removeItem('portal-username');
        localStorage.removeItem('portal-userId');
        if (FB.auth && FB.auth.currentUser) FB.auth.signOut().catch(function () {});
      });
    });

    // Clean up on page unload (best-effort)
    window.addEventListener('pagehide', function () {
      clearInterval(heartbeatTimer);
      myPresenceRef.remove().catch(function () {});
    });
  }

  document.addEventListener('NoteSphereFBReady', boot);
  if (window.NoteSphereFB && window.NoteSphereFB.isReady) boot();

  /* ─── Public API ────────────────────────────────────────────── */

  window.NoteSpherePresence = {
    isOnline: function () { return !!myPresenceRef; },
    getOnlineUsers: function () { return latestPresenceData; },
  };
})();
