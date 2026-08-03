/**
 * NoteSphere Firebase Presence System
 * Syncs online status in Realtime Database.
 * Dynamically unhides and highlights ALL connected online members in realtime.
 */
(function () {
  function initPresence() {
    if (!window.NoteSphereFB || !window.NoteSphereFB.isReady) return;
    const currentUser = window.CURRENT_USER_JSON;
    if (!currentUser || !currentUser.id) return;

    const db = window.NoteSphereFB.db;
    const ServerValue = window.NoteSphereFB.ServerValue;

    const userPresenceRef = db.ref("presence/" + currentUser.id);
    const connectedRef = db.ref(".info/connected");

    // Establish presence connection for current user
    connectedRef.on("value", function (snap) {
      if (snap.val() === true) {
        userPresenceRef
          .onDisconnect()
          .set({
            status: "offline",
            last_seen: ServerValue.TIMESTAMP,
            full_name: currentUser.full_name,
            role: currentUser.role,
            username: currentUser.username,
            avatar_id: currentUser.avatar_id || null,
          })
          .then(function () {
            userPresenceRef.set({
              status: "online",
              last_seen: ServerValue.TIMESTAMP,
              full_name: currentUser.full_name,
              role: currentUser.role,
              username: currentUser.username,
              avatar_id: currentUser.avatar_id || null,
            });
          });
      }
    });

    // Realtime Presence Listener: Listens for ALL online users across the database
    const presenceAllRef = db.ref("presence");
    presenceAllRef.on("value", function (snapshot) {
      const data = snapshot.val() || {};
      const onlineSet = new Set();

      // Collect all user IDs marked status === "online"
      Object.keys(data).forEach(function (uId) {
        const u = data[uId];
        if (u && (u.status === "online" || u === true)) {
          onlineSet.add(String(uId));
        }
      });

      // Logged-in user viewing the page is always online
      if (currentUser.id) {
        onlineSet.add(String(currentUser.id));
      }

      const onlineCount = onlineSet.size;

      // 1. Update Topbar Online Count Header
      const countEl = document.getElementById("firebase-online-count");
      if (countEl) {
        countEl.textContent = onlineCount + (onlineCount === 1 ? " Online" : " Online");
      }

      // 2. Update Chat Subtitle Badge in Header
      const chatSubEl = document.getElementById("chat-online-subtitle");
      if (chatSubEl) {
        chatSubEl.textContent = onlineCount + (onlineCount === 1 ? " member online" : " members online");
      }

      // 3. Dynamic DOM update for Desktop Sidebar Items
      const sidebarContainer = document.getElementById("chat-online-users-sidebar");
      if (sidebarContainer) {
        const items = sidebarContainer.querySelectorAll(".online-member-item");
        items.forEach(function (item) {
          const uId = item.getAttribute("data-user-id");
          const isOnline = onlineSet.has(String(uId));

          if (isOnline) {
            item.classList.remove("hidden");
            item.classList.add("flex");
          } else {
            item.classList.remove("flex");
            item.classList.add("hidden");
          }
        });
      }

      // 4. Dynamic DOM update for Small Devices Drawer Items
      const drawerContainer = document.getElementById("chat-online-users-drawer");
      if (drawerContainer) {
        const drawerItems = drawerContainer.querySelectorAll(".drawer-member-item");
        drawerItems.forEach(function (item) {
          const uId = item.getAttribute("data-user-id");
          const isOnline = onlineSet.has(String(uId));

          if (isOnline) {
            item.classList.remove("hidden");
            item.classList.add("flex");
          } else {
            item.classList.remove("flex");
            item.classList.add("hidden");
          }
        });
      }
    });
  }

  document.addEventListener("NoteSphereFBReady", initPresence);
  if (window.NoteSphereFB && window.NoteSphereFB.isReady) {
    initPresence();
  }
})();
