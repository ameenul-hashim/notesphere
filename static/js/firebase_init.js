/**
 * NoteSphere Cloud Firestore Initializer
 * Initializes Firebase, authenticates the Django-authenticated user against
 * Firebase Auth using a server-issued custom token, and only then exposes
 * `window.NoteSphereFB` as ready so presence/chat never fire unauthenticated.
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
        auth: auth,
        serverTimestamp: firebase.firestore.FieldValue.serverTimestamp,
        arrayUnion: firebase.firestore.FieldValue.arrayUnion,
        arrayRemove: firebase.firestore.FieldValue.arrayRemove,
        isReady: false,
      };

      // Create random session ID for this browser tab (for multi-tab presence)
      window.NoteSphereFB.session_id = 'sess_' + Math.random().toString(36).substr(2, 9);

      if (customToken) {
        // Sign into Firebase Auth with the custom token minted by Django.
        await auth.signInWithCustomToken(customToken);
      } else {
        console.warn("[Firebase] No custom token available; skipping Firebase auth.");
      }

      window.NoteSphereFB.isReady = true;
      document.dispatchEvent(new CustomEvent("NoteSphereFBReady"));
    } catch (e) {
      // request.auth stays null -> Firestore rules deny reads/writes, so the
      // realtime features stay disabled rather than running unauthenticated.
      console.error("NoteSphere Firebase init/auth error:", e);
      window.NoteSphereFB && (window.NoteSphereFB.authError = true);
    }
  }

  init();
})();
