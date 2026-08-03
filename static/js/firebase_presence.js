/**
 * NoteSphere Firebase Presence System
 * - Sets user ONLINE when they open any page
 * - Sets user OFFLINE when they:
 *   a) Close the tab/browser (pagehide event)
 *   b) Tab becomes hidden for >5 minutes (visibilitychange)
 *   c) Click the Log out button (form submit intercept)
 * - Listens to ALL users in presence/ and updates sidebar/drawer/count in real time
 */
(function () {
  var presenceRef = null;
  var visibilityTimer = null;

  function setOffline() {
    if (presenceRef) {
      presenceRef.set({
        status: "offline",
        last_seen: Date.now(),
      });
    }
  }

  function initPresence() {
    if (!window.NoteSphereFB || !window.NoteSphereFB.isReady) return;
    var currentUser = window.CURRENT_USER_JSON;
    if (!currentUser || !currentUser.id) return;

    var db = window.NoteSphereFB.db;
    var ServerValue = window.NoteSphereFB.ServerValue;

    presenceRef = db.ref("presence/" + currentUser.id);
    var connectedRef = db.ref(".info/connected");

    // Set ONLINE on Firebase connection
    connectedRef.on("value", function (snap) {
      if (snap.val() === true) {
        // Register onDisconnect first (fires when TCP connection drops e.g. tab closed)
        presenceRef.onDisconnect().set({
          status: "offline",
          last_seen: ServerValue.TIMESTAMP,
          full_name: currentUser.full_name,
          role: currentUser.role,
          username: currentUser.username,
        }).then(function () {
          // Then set current status to online
          presenceRef.set({
            status: "online",
            last_seen: ServerValue.TIMESTAMP,
            full_name: currentUser.full_name,
            role: currentUser.role,
            username: currentUser.username,
          });
        });
      }
    });

    // pagehide fires reliably on tab close, browser close, and page navigation
    window.addEventListener("pagehide", function () {
      setOffline();
    });

    // Detect tab hidden: start a 5-min timer, set offline if still hidden
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        visibilityTimer = setTimeout(function () {
          setOffline();
        }, 5 * 60 * 1000); // 5 minutes
      } else {
        // Tab visible again — cancel the timer and restore online
        clearTimeout(visibilityTimer);
        presenceRef.set({
          status: "online",
          last_seen: ServerValue.TIMESTAMP,
          full_name: currentUser.full_name,
          role: currentUser.role,
          username: currentUser.username,
        });
      }
    });

    // Intercept ALL logout form submissions — set offline before navigating
    document.querySelectorAll("form[action*='logout']").forEach(function (form) {
      form.addEventListener("submit", function () {
        setOffline();
      });
    });

    // ─── Realtime Listener: Update ALL connected users in UI ─────────────────
    var presenceAllRef = db.ref("presence");
    presenceAllRef.on("value", function (snapshot) {
      var data = snapshot.val() || {};
      var onlineSet = new Set();

      Object.keys(data).forEach(function (uId) {
        var u = data[uId];
        if (u && u.status === "online") {
          onlineSet.add(String(uId));
        }
      });

      // Current user is always online while page is open
      onlineSet.add(String(currentUser.id));

      var onlineCount = onlineSet.size;

      // 1. Topbar count
      var countEl = document.getElementById("firebase-online-count");
      if (countEl) countEl.textContent = onlineCount + " Online";

      // 2. Chat header subtitle
      var chatSubEl = document.getElementById("chat-online-subtitle");
      if (chatSubEl) chatSubEl.textContent = onlineCount + (onlineCount === 1 ? " member online" : " members online");

      // 3. Chat Sidebar — show/hide online member cards
      var sidebarContainer = document.getElementById("chat-online-users-sidebar");
      if (sidebarContainer) {
        sidebarContainer.querySelectorAll(".online-member-item").forEach(function (item) {
          var uId = item.getAttribute("data-user-id");
          var isOnline = onlineSet.has(String(uId));
          item.classList.toggle("hidden", !isOnline);
          item.classList.toggle("flex", isOnline);
        });
      }

      // 4. Mobile Drawer — show/hide online member pills
      var drawerContainer = document.getElementById("chat-online-users-drawer");
      if (drawerContainer) {
        drawerContainer.querySelectorAll(".drawer-member-item").forEach(function (item) {
          var uId = item.getAttribute("data-user-id");
          var isOnline = onlineSet.has(String(uId));
          item.classList.toggle("hidden", !isOnline);
          item.classList.toggle("flex", isOnline);
        });
      }

      // 5. Active Members Page Grid — green dot = online, red dot = offline
      var membersGrid = document.getElementById("members-grid");
      if (membersGrid) {
        var cards = Array.from(membersGrid.querySelectorAll(".member-card"));

        cards.forEach(function (card) {
          var uId = card.getAttribute("data-member-id");
          var dot = card.querySelector(".member-status-dot");
          var label = card.querySelector(".member-status-label");
          var isOnline = onlineSet.has(String(uId));

          if (isOnline) {
            if (dot) { dot.className = "member-status-dot absolute top-2 right-2 w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse border-2 border-surface-2"; dot.title = "Online"; }
            if (label) { label.textContent = "Online"; label.className = "member-status-label text-[10px] font-semibold text-emerald-500 mt-1"; }
            card.dataset.onlineOrder = "0";
          } else {
            if (dot) { dot.className = "member-status-dot absolute top-2 right-2 w-2.5 h-2.5 rounded-full bg-rose-500 border-2 border-surface-2"; dot.title = "Offline"; }
            if (label) { label.textContent = "Offline"; label.className = "member-status-label text-[10px] font-semibold text-rose-400 mt-1"; }
            card.dataset.onlineOrder = "1";
          }
        });

        // Sort: online first
        cards.sort(function (a, b) {
          return parseInt(a.dataset.onlineOrder || "1") - parseInt(b.dataset.onlineOrder || "1");
        });
        cards.forEach(function (c) { membersGrid.appendChild(c); });
      }
    });
  }

  document.addEventListener("NoteSphereFBReady", initPresence);
  if (window.NoteSphereFB && window.NoteSphereFB.isReady) {
    initPresence();
  }
})();
