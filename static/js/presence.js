/**
 * NoteSphere Presence — Django Session-Based
 * ─────────────────────────────────────────────────────────────────────────────
 * Online = has an active Django session (logged in).
 * Polls /community/online-users/ every 15 seconds.
 * No Firebase needed for presence.
 */
(function () {
  'use strict';

  var onlineUsers = {};
  var pollTimer = null;
  var myId = null;

  function me() { return window.CURRENT_USER_JSON || {}; }

  function init() {
    myId = me().id ? String(me().id) : null;
    if (!myId) return;
    fetchAndRender();
    pollTimer = setInterval(fetchAndRender, 15000);
  }

  function fetchAndRender() {
    fetch('/community/online-users/', {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      onlineUsers = {};
      (data.online || []).forEach(function (u) {
        onlineUsers[String(u.id)] = u;
      });
      renderSidebar();
      renderDrawer();
      updateCount();
    })
    .catch(function () {});
  }

  /* ─── UI Rendering ──────────────────────────────────────────── */

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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
      var mine = String(p.id) === myId;
      var item = document.createElement('div');
      item.className = 'online-member-item flex items-center justify-between p-2.5 rounded-xl bg-surface-2/60 hover:bg-surface-2 border border-border/50 transition-all';
      item.setAttribute('data-user-id', p.id);
      var initial = (p.display_name || p.username || '?').charAt(0).toUpperCase();
      item.innerHTML =
        '<div class="flex items-center gap-2.5 min-w-0">' +
          '<div class="relative w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center font-bold text-xs flex-shrink-0 border border-emerald-500/40">' +
            '<span>' + esc(initial) + '</span>' +
            '<span class="online-indicator absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-surface animate-pulse"></span>' +
          '</div>' +
          '<div class="truncate">' +
            '<span class="text-xs font-bold text-foreground truncate block leading-tight">' +
              esc(p.display_name || p.username) +
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
  }

  function renderDrawer() {
    var el = document.getElementById('chat-online-users-drawer');
    if (!el) return;
    el.textContent = '';
    var list = Object.keys(onlineUsers).map(function (k) { return onlineUsers[k]; });
    if (list.length === 0) {
      el.innerHTML = '<div class="p-6 text-center text-xs text-muted">No members online</div>';
      return;
    }
    list.forEach(function (p) {
      var mine = String(p.id) === myId;
      var item = document.createElement('div');
      item.className = 'flex items-center justify-between p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 border border-border/50 transition-all';
      item.setAttribute('data-user-id', p.id);
      var initial = (p.display_name || p.username || '?').charAt(0).toUpperCase();
      item.innerHTML =
        '<div class="flex items-center gap-3 min-w-0">' +
          '<div class="relative w-9 h-9 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center font-bold text-xs flex-shrink-0 border border-emerald-500/40">' +
            '<span>' + esc(initial) + '</span>' +
            '<span class="online-indicator absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-surface animate-pulse"></span>' +
          '</div>' +
          '<div class="truncate">' +
            '<span class="text-sm font-bold text-foreground truncate block leading-tight">' +
              esc(p.display_name || p.username) +
              (mine ? ' <span class="badge badge-primary text-[9px] px-1.5 py-0 font-bold ml-1">You</span>' : '') +
            '</span>' +
            '<span class="online-status-text text-[11px] text-emerald-500 font-medium">' +
              (p.role === 'ADMIN' ? 'Administrator' : 'Student') + ' &middot; online' +
            '</span>' +
          '</div>' +
        '</div>' +
        (p.role === 'ADMIN' ? '<span class="badge badge-warning text-[9px] px-1.5 py-0">Admin</span>' : '');
      el.appendChild(item);
    });
  }

  function updateCount() {
    var count = Object.keys(onlineUsers).length;
    var sub = document.getElementById('chat-online-subtitle');
    if (sub) sub.textContent = count + (count === 1 ? ' member online' : ' members online');
  }

  /* ─── Boot ──────────────────────────────────────────────────── */

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.NoteSpherePresence = {
    isOnline: function () { return myId != null && !!onlineUsers[myId]; },
    getOnlineUsers: function () { return onlineUsers; },
  };
})();
