/**
 * NoteSphere Firebase Initializer
 * Initializes Firebase, authenticates the Django-authenticated user against
 * Firebase Auth using a server-issued custom token, and exposes
 * `window.NoteSphereFB` so chat and presence can work.
 */
(function () {
  if (window.NoteSphereFB) return;
  const fbConfig = window.FIREBASE_CONFIG || {};
  const customToken = window.FIREBASE_CUSTOM_TOKEN || "";

  async function init() {
    try {
      if (!firebase.apps.length) {
        firebase.initializeApp(fbConfig);
      }
      const db = firebase.firestore();
      const auth = firebase.auth();

      window.NoteSphereFB = {
        app: firebase.app(),
        db: db,
        rtdb: null,
        auth: auth,
        serverTimestamp: firebase.firestore.FieldValue.serverTimestamp,
        arrayUnion: firebase.firestore.FieldValue.arrayUnion,
        arrayRemove: firebase.firestore.FieldValue.arrayRemove,
        isReady: false,
      };

      // Try to connect Realtime Database (optional — may not be enabled)
      try {
        window.NoteSphereFB.rtdb = firebase.database();
      } catch (e) {
        console.warn("[Firebase] Realtime Database not available:", e.message);
      }

      if (customToken) {
        await auth.signInWithCustomToken(customToken);
      } else {
        console.warn("[Firebase] No custom token available; skipping Firebase auth.");
      }

      window.NoteSphereFB.isReady = true;
      document.dispatchEvent(new CustomEvent("NoteSphereFBReady"));
    } catch (e) {
      console.error("NoteSphere Firebase init/auth error:", e);
      window.NoteSphereFB && (window.NoteSphereFB.authError = true);
    }
  }

  init();
})();
