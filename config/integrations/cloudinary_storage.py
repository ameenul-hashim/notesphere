"""
Cloudinary storage integration for NoteSphere.

Handles upload and deletion of uploaded images (profile photos,
subject thumbnails, semester thumbnails) to Cloudinary.

DOES NOT handle Avatar images — those remain on local storage.
"""

import logging
import os

import cloudinary
import cloudinary.uploader
from django.core.files.storage import FileSystemStorage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_configured = False


def _ensure_configured():
    """Configure Cloudinary from environment variables (once)."""
    global _configured
    if _configured:
        return True

    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.environ.get("CLOUDINARY_API_KEY", "")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")

    if not all([cloud_name, api_key, api_secret]):
        logger.warning(
            "Cloudinary credentials not fully configured. "
            "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET."
        )
        return False

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    _configured = True
    logger.info("Cloudinary configured successfully for cloud_name=%s", cloud_name)
    return True


# ---------------------------------------------------------------------------
# Hybrid storage — handles both local files and Cloudinary URLs
# ---------------------------------------------------------------------------

class CloudinaryAwareStorage(FileSystemStorage):
    """Storage backend that returns Cloudinary URLs as-is.

    When a field stores a Cloudinary URL (e.g. https://res.cloudinary.com/...),
    the url() method returns it directly. For local file paths, it delegates
    to the normal FileSystemStorage behavior.

    This allows existing local images and new Cloudinary uploads to coexist.
    """

    def url(self, name):
        if name and isinstance(name, str) and name.startswith("http"):
            return name
        return super().url(name)

    def _save(self, name, content):
        # Skip local save for Cloudinary URLs
        if name and isinstance(name, str) and name.startswith("http"):
            return name
        return super()._save(name, content)

    def exists(self, name):
        if name and isinstance(name, str) and name.startswith("http"):
            return False
        return super().exists(name)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_image(file_obj, folder="notesphere/misc"):
    """Upload an image file to Cloudinary.

    Args:
        file_obj: A Django UploadedFile or file-like object.
        folder:   Cloudinary folder path (e.g. "notesphere/profile").

    Returns:
        Cloudinary URL string on success, None on failure.
    """
    if not _ensure_configured():
        logger.error("Cloudinary upload failed: not configured")
        return None

    try:
        # Reset file pointer to beginning
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        result = cloudinary.uploader.upload(
            file_obj,
            folder=folder,
            resource_type="image",
            allowed_formats=["jpg", "jpeg", "png", "gif", "webp", "svg"],
            transformation=[
                {"quality": "auto", "fetch_format": "auto"}
            ],
        )
        url = result.get("secure_url") or result.get("url")
        public_id = result.get("public_id", "unknown")

        logger.info(
            "Cloudinary upload successful | public_id=%s | folder=%s | url=%s",
            public_id, folder, url,
        )
        return url

    except Exception as exc:
        logger.exception(
            "Cloudinary upload failed | folder=%s | error=%s",
            folder, exc,
        )
        return None


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_image(public_id):
    """Delete an image from Cloudinary by public_id.

    Args:
        public_id: The Cloudinary public_id (e.g. "notesphere/profile/abc123").
                   Can also be a full URL — will be extracted.

    Returns:
        True on success, False on failure.
    """
    if not _ensure_configured():
        logger.error("Cloudinary delete failed: not configured")
        return False

    # Extract public_id from URL if a full URL was passed
    if public_id and public_id.startswith("http"):
        public_id = _extract_public_id(public_id)

    if not public_id:
        logger.warning("Cloudinary delete skipped: no public_id")
        return False

    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        result_type = result.get("result", "unknown")

        if result_type == "ok":
            logger.info("Cloudinary delete successful | public_id=%s", public_id)
            return True
        else:
            logger.warning(
                "Cloudinary delete returned %s | public_id=%s",
                result_type, public_id,
            )
            return False

    except Exception as exc:
        logger.exception(
            "Cloudinary delete failed | public_id=%s | error=%s",
            public_id, exc,
        )
        return False


def delete_image_by_url(url):
    """Delete a Cloudinary image given its full URL.

    Args:
        url: The full Cloudinary URL.

    Returns:
        True on success, False on failure.
    """
    if not url:
        return False
    public_id = _extract_public_id(url)
    return delete_image(public_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_public_id(url):
    """Extract Cloudinary public_id from a full URL.

    Example:
        https://res.cloudinary.com/demo/image/upload/v1234567890/notesphere/profile/abc.jpg
        -> notesphere/profile/abc
    """
    if not url or "cloudinary.com" not in url:
        return None

    try:
        # Split on /upload/ to get the path after it
        parts = url.split("/upload/")
        if len(parts) < 2:
            return None

        path = parts[1]
        # Remove version prefix if present (e.g. "v1234567890/")
        if path.startswith("v") and "/" in path:
            path = path.split("/", 1)[1]

        # Remove file extension
        if "." in path:
            path = path.rsplit(".", 1)[0]

        return path

    except (IndexError, ValueError):
        return None


def get_public_id_from_field(field_file):
    """Extract Cloudinary public_id from a Django ImageField file.

    Works with both Cloudinary-managed fields and URL-based fields.
    """
    if not field_file:
        return None

    # If the field has a URL, extract from URL
    try:
        url = field_file.url
        if "cloudinary.com" in url:
            return _extract_public_id(url)
    except Exception:
        pass

    # Fallback: use the file name
    name = getattr(field_file, "name", None)
    if name:
        return name.rsplit(".", 1)[0] if "." in name else name

    return None
