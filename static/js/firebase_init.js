/**
 * NoteSphere Firebase Realtime Database Initializer
 * Dynamically loads Firebase SDK and exposes `window.NoteSphereFB` for presence and chat.
 */
(function () {
  if (window.NoteSphereFB) return;

  const fbConfig = window.FIREBASE_CONFIG || {};

  // Firebase v9 App + Database (compat CDN for zero-build browser compatibility)
  const appScript = document.createElement("script");
  appScript.src = "https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js";

  const dbScript = document.createElement("script");
  dbScript.src = "https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js";

  appScript.onload = function () {
    document.head.appendChild(dbScript);
  };

  dbScript.onload = function () {
    try {
      if (!firebase.apps.length) {
        firebase.initializeApp(fbConfig);
      }
      const db = firebase.database();
      window.NoteSphereFB = {
        app: firebase.app(),
        db: db,
        ServerValue: firebase.database.ServerValue,
        isReady: true,
      };
      document.dispatchEvent(new CustomEvent("NoteSphereFBReady"));
    } catch (e) {
      console.warn("NoteSphere Firebase init warning:", e);
    }
  };

  document.head.appendChild(appScript);
})();
