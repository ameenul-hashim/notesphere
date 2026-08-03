/**
 * NoteSphere Cloud Firestore Multi-Tab Presence System
 * - Supports multiple tabs using session_id heartbeats
 * - Sets user ONLINE on root when any session is active
 * - Sets user OFFLINE when all sessions are closed
 */
(function () {
  let isNavigatingAway = false;

  async function updatePresence(status) {
    if (!window.NoteSphereFB || !window.NoteSphereFB.isReady || !window.CURRENT_USER_JSON?.id) return;
    const db = window.NoteSphereFB.db;
    const userId = "user_" + window.CURRENT_USER_JSON.id;
    const sessionId = window.NoteSphereFB.session_id;
    
    const userRef = db.collection("users").doc(userId);
    const sessionRef = userRef.collection("sessions").doc(sessionId);

    try {
      if (status === "online") {
        await userRef.set({
          user_id: window.CURRENT_USER_JSON.id,
          role: window.CURRENT_USER_JSON.role,
          status: "online",
          last_seen: window.NoteSphereFB.serverTimestamp(),
          updated_at: window.NoteSphereFB.serverTimestamp(),
        }, { merge: true });
        
        await sessionRef.set({
          session_id: sessionId,
          last_heartbeat: window.NoteSphereFB.serverTimestamp(),
        });
      } else {
        await sessionRef.delete();
      }
    } catch(e) {
      console.warn("Presence err", e);
    }
  }

  function initPresence() {
    updatePresence("online");
    
    // Heartbeat every 2 mins
    setInterval(() => {
      if (!document.hidden && !isNavigatingAway) updatePresence("online");
    }, 2 * 60 * 1000);

    window.addEventListener("pagehide", () => {
      isNavigatingAway = true;
      updatePresence("offline");
    });
    
    document.querySelectorAll("form[action*='logout']").forEach(form => {
      form.addEventListener("submit", () => {
        isNavigatingAway = true;
        updatePresence("offline");
      });
    });

    // Listener for ALL active users
    const db = window.NoteSphereFB.db;
    db.collection("users").where("status", "==", "online").onSnapshot(snapshot => {
      const onlineSet = new Set();
      snapshot.forEach(doc => {
        onlineSet.add(String(doc.data().user_id));
      });
      // Ensure self is marked online in UI instantly
      if (window.CURRENT_USER_JSON?.id) {
          onlineSet.add(String(window.CURRENT_USER_JSON.id));
      }
      
      const onlineCount = onlineSet.size;
      const countEl = document.getElementById("firebase-online-count");
      if (countEl) countEl.textContent = onlineCount + " Online";

      const chatSubEl = document.getElementById("chat-online-subtitle");
      if (chatSubEl) chatSubEl.textContent = onlineCount + (onlineCount === 1 ? " member online" : " members online");

      ["chat-online-users-sidebar", "chat-online-users-drawer"].forEach(id => {
        const container = document.getElementById(id);
        if (container) {
          container.querySelectorAll(".online-member-item, .drawer-member-item").forEach(item => {
            const uId = item.getAttribute("data-user-id");
            const isOnline = onlineSet.has(String(uId));
            item.classList.toggle("hidden", !isOnline);
            item.classList.toggle("flex", isOnline);
          });
        }
      });

      const membersGrid = document.getElementById("members-grid");
      if (membersGrid) {
        const cards = Array.from(membersGrid.querySelectorAll(".member-card"));
        cards.forEach(card => {
          const uId = card.getAttribute("data-member-id");
          const dot = card.querySelector(".member-status-dot");
          const label = card.querySelector(".member-status-label");
          if (onlineSet.has(String(uId))) {
            if (dot) { dot.className = "member-status-dot absolute top-2 right-2 w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse border-2 border-surface-2"; dot.title = "Online"; }
            if (label) { label.textContent = "Online"; label.className = "member-status-label text-[10px] font-semibold text-emerald-500 mt-1"; }
            card.dataset.onlineOrder = "0";
          } else {
            if (dot) { dot.className = "member-status-dot absolute top-2 right-2 w-2.5 h-2.5 rounded-full bg-rose-500 border-2 border-surface-2"; dot.title = "Offline"; }
            if (label) { label.textContent = "Offline"; label.className = "member-status-label text-[10px] font-semibold text-rose-400 mt-1"; }
            card.dataset.onlineOrder = "1";
          }
        });
        cards.sort((a, b) => parseInt(a.dataset.onlineOrder || "1") - parseInt(b.dataset.onlineOrder || "1"));
        cards.forEach(c => membersGrid.appendChild(c));
      }
    });
  }

  document.addEventListener("NoteSphereFBReady", initPresence);
  if (window.NoteSphereFB && window.NoteSphereFB.isReady) initPresence();
})();
