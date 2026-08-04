"""
Firebase Admin SDK — Django backend integration.

Initializes the Admin SDK once (singleton) using the service account JSON.

Usage anywhere in Django:
    from config.integrations.firebase_admin_sdk import get_firestore_client
    db = get_firestore_client()
    db.collection("community_chat").add({ ... })

Security:
    The service account JSON is loaded from:
    1. FIREBASE_SERVICE_ACCOUNT_JSON env var (raw JSON string, used on Railway)
    2. FIREBASE_SERVICE_ACCOUNT_PATH env var (file path)
    3. config/firebase/firebase-service-account.json (local dev fallback)
    The JSON file is listed in .gitignore and MUST NEVER be committed to Git.
"""

import json
import os
import tempfile
import threading
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

_lock = threading.Lock()
_app = None


def _get_service_account_path() -> str:
    """Return path to the service account JSON.

    Priority:
        1. FIREBASE_SERVICE_ACCOUNT_JSON env var → write to temp file
        2. FIREBASE_SERVICE_ACCOUNT_PATH env var → file path
        3. Default gitignored location
    """
    # 1. Raw JSON string in env var (for Railway / cloud deployments)
    json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    if json_str:
        # Validate it's valid JSON and write to a temp file
        try:
            parsed = json.loads(json_str)
            tmp = tempfile.NamedTemporaryFile(
                prefix="firebase-sa-",
                suffix=".json",
                mode="w",
                delete=False,
            )
            json.dump(parsed, tmp)
            tmp.close()
            return tmp.name
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(
                f"FIREBASE_SERVICE_ACCOUNT_JSON env var contains invalid JSON: {e}"
            ) from e

    # 2. Explicit file path
    env_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    if env_path and Path(env_path).exists():
        return env_path

    # 3. Default location (local dev, gitignored)
    base = Path(__file__).resolve().parent.parent.parent
    default = base / "config" / "firebase" / "firebase-service-account.json"
    return str(default)


def _init_app() -> firebase_admin.App:
    """Initialize the Firebase Admin SDK exactly once (thread-safe singleton)."""
    global _app
    if _app is not None:
        return _app

    with _lock:
        if _app is not None:
            return _app

        sa_path = _get_service_account_path()
        if not Path(sa_path).exists():
            raise RuntimeError(
                f"Firebase service account file not found at: {sa_path}\n"
                "Set FIREBASE_SERVICE_ACCOUNT_PATH in your environment or place the JSON at "
                "config/firebase/firebase-service-account.json"
            )

        cred = credentials.Certificate(sa_path)
        _app = firebase_admin.initialize_app(cred)
        return _app


def get_firestore_client():
    """Return an authenticated Firestore client, initializing the SDK if needed."""
    try:
        _init_app()
        return firestore.client()
    except Exception as e:
        raise RuntimeError(f"Firebase Admin SDK initialization failed: {e}") from e


def create_custom_token(uid: str) -> str:
    """Mint a Firebase custom token for the given UID.

    The UID is the string form of the Django user's primary key. The frontend
    exchanges this token via `firebase.auth().signInWithCustomToken(...)`, after
    which `request.auth.uid` in Firestore security rules equals that UID.

    Django authentication remains the source of truth; this token simply maps a
    Django-authenticated session onto a Firebase Authentication identity so the
    Firestore security rules can be enforced.
    """
    try:
        _init_app()
        from firebase_admin import auth

        token = auth.create_custom_token(uid, app=_app)
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token
    except Exception as e:
        raise RuntimeError(f"Failed to create Firebase custom token: {e}") from e
