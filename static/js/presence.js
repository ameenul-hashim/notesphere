/**
 * NoteSphere Presence — Simple Online/Offline
 * ─────────────────────────────────────────────────────────────────────────────
 * Logged in  → status: 'online'   (shown in online sidebar)
 * Logged out → status: 'offline'  (removed from online sidebar)
 *
 * That's it. No heartbeats, no sessions, no sweep.
 * Django is the source of truth for who is authenticated.
 */
(function () {
  'use strict';

  var FB = null;
  var onlineUsers = {};
  var callbacks = [];

  function me() { return window.CURRENT_USER_JSON || {}; }

  function uid() {
    var id = me().id;
    return id === undefined || id === null ? null : String(id);
  }

  function userRef() {
    return FB.db.collection('users').doc('user_' + uid());
  }

  /* ─── Mark self online ──────────────────────────────────────── */

  function goOnline() {
    if (!FB || !FB.isReady || !uid()) return;
    userRef().set({
      uid: uid(),
      status: 'online',
      role: me().role,
      display_name: me().full_name || me().username || '',
      avatar_url: me().avatar_url || '',
      last_seen: FB.serverTimestamp(),
    }, { merge: true }).catch(function (e) {
      console.warn('[presence] goOnline failed', e);
    });
  }

  /* ─── Mark self offline ─────────────────────────────────────── */

  function goOffline() {
    if (!FB || !FB.isReady || !uid()) return;
    userRef().set({
      status: 'offline',
      last_seen: FB.serverTimestamp(),
    }, { merge: true }).catch(function () {});
  }

  /* ─── Listen for online users ───────────────────────────────── */

  function startListener() {
    FB.db.collection('users')
      .where('status', '==', 'online')
      .onSnapshot(function (snap) {
        onlineUsers = {};
        snap.forEach(function (doc) {
          var d = doc.data() || {};
          var key = String(doc.id).replace('user_', '');
          var reg = (window.USER_REGISTRY || {})[key] || {};
          onlineUsers[key] = {
            uid: key,
            display_name: d.display_name || reg.name || 'User',
            role: d.role || reg.role || 'STUDENT',
            avatar_url: d.avatar_url || reg.avatar_url || '',
          };
        });
        renderSidebar();
        renderDrawer();
        callbacks.forEach(function (cb) { cb(Object.keys(onlineUsers)); });
      }, function (err) {
        console.warn('[presence] listener error', err);
      });
  }

  /* ─── UI Rendering ──────────────────────────────────────────── */

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function avatarHtml(url, name) {
    if (url) return '<img src="' + esc(url) + '" alt="" class="w-full h-full object-cover">';
    return '<span class="flex items-center justify-center w-full h-full">' + esc((name || '?').charAt(0).toUpperCase()) + '</span>';
  }

  function renderSidebar() {
    var el = document.getElementById('chat-online-users-sidebar');
    if (!el) return;
    el.textContent = '';
    var list = Object.keys(onlineUsers).map(function (k) { return onlineUsers[k]; });
    if (list.length === 0) {
      el.innerHTML = '<div class="p-3 text-center text-xs text-muted">No members online</div>';
      return;
    }
    list.forEach(function (p) {
      var mine = p.uid === uid();
      var item = document.createElement('div');
      item.className = 'online-member-item flex items-center justify-between p-2.5 rounded-xl bg-surface-2/60 hover:bg-surface-2 border border-border/50 transition-all';
      item.setAttribute('data-user-id', p.uid);
      item.innerHTML =
        '<div class="flex items-center gap-2.5 min-w-0">' +
          '<div class="relative w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center font-bold text-xs flex-shrink-0 border border-emerald-500/40 overflow-hidden">' +
            avatarHtml(p.avatar_url, p.display_name) +
            '<span class="online-indicator absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-surface animate-pulse"></span>' +
          '</div>' +
          '<div class="truncate">' +
            '<span class="text-xs font-bold text-foreground truncate block leading-tight">' +
              esc(p.display_name) +
              (mine ? ' <span class="badge badge-primary text-[9px] px-1.5 py-0 font-bold ml-1">You</span>' : '') +
            '</span>' +
            '<span class="online-status-text text-[10px] text-emerald-500 font-medium">' +
              (p.role === 'ADMIN' ? 'Administrator' : 'Student') + ' &middot; online' +
            '</span>' +
          '</div>' +
        '</div>' +
        (p.role === 'ADMIN' ? '<span class="badge badge-warning text-[9px] px-1.5 py-0">Admin</span>' : '');
      el.appendChild(item);
    });
    var sub = document.getElementById('chat-online-subtitle');
    if (sub) sub.textContent = list.length + (list.length === 1 ? ' member online' : ' members online');
  }

  function renderDrawer() {
    var el = document.getElementById('chat-online-users-drawer');
    if (!el) return;
    el.textContent = '';
    Object.keys(onlineUsers).forEach(function (k) {
      var p = onlineUsers[k];
      var mine = p.uid === uid();
      var item = document.createElement('div');
      item.className = 'drawer-member-item flex flex-shrink-0 items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-2 border border-border text-foreground text-xs font-semibold';
      item.setAttribute('data-user-id', p.uid);
      item.innerHTML =
        '<span class="drawer-online-dot w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>' +
        '<span>' + esc(p.display_name) + (mine ? ' (You)' : '') + '</span>';
      el.appendChild(item);
    });
  }

  /* ─── Boot ──────────────────────────────────────────────────── */

  function boot() {
    if (!window.NoteSphereFB || !window.NoteSphereFB.isReady || !uid()) return;
    FB = window.NoteSphereFB;
    goOnline();
    startListener();

    window.addEventListener('pagehide', goOffline);
    window.addEventListener('online', goOnline);

    document.querySelectorAll("form[action*='logout']").forEach(function (form) {
      form.addEventListener('submit', function () {
        goOffline();
        if (FB.auth && FB.auth.currentUser) FB.auth.signOut().catch(function () {});
      });
    });
  }

  document.addEventListener('NoteSphereFBReady', boot);
  if (window.NoteSphereFB && window.NoteSphereFB.isReady) boot();

  /* ─── Public API ────────────────────────────────────────────── */

  window.NoteSpherePresence = {
    isOnline: function () { return !!onlineUsers[uid()]; },
    getOnlineUsers: function () { return onlineUsers; },
    onOnlineUsersChange: function (cb) {
      if (typeof cb === 'function') callbacks.push(cb);
      return function () { var i = callbacks.indexOf(cb); if (i >= 0) callbacks.splice(i, 1); };
    },
  };
})();
