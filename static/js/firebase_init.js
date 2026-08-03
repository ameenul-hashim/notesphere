/**
 * NoteSphere Cloud Firestore Initializer
 * Initializes Firebase Firestore and exposes `window.NoteSphereFB` for presence and chat.
 */
(function () {
  if (window.NoteSphereFB) return;
  const fbConfig = window.FIREBASE_CONFIG || {};

  try {
    if (!firebase.apps.length) {
      firebase.initializeApp(fbConfig);
    }
    const db = firebase.firestore();
    
    window.NoteSphereFB = {
      app: firebase.app(),
      db: db,
      serverTimestamp: firebase.firestore.FieldValue.serverTimestamp,
      arrayUnion: firebase.firestore.FieldValue.arrayUnion,
      arrayRemove: firebase.firestore.FieldValue.arrayRemove,
      isReady: true,
    };
    
    // Create random session ID for this browser tab (for multi-tab presence)
    window.NoteSphereFB.session_id = 'sess_' + Math.random().toString(36).substr(2, 9);

    document.dispatchEvent(new CustomEvent("NoteSphereFBReady"));
  } catch (e) {
    console.warn("NoteSphere Firebase init warning:", e);
  }
})();
