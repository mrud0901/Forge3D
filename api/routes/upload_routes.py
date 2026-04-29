"""
Forge3D – Upload URL Route
Generates a signed upload URL for Supabase Storage so the frontend
can upload files directly without proxying through the API server.

POST /api/upload-url
  Body:  { "filename": str, "project_id": str, "content_type": str }
  Returns: { "upload_url": str, "file_url": str, "path": str }
"""

import os
import uuid
import re
from flask import Blueprint, request, jsonify, g

from utils.auth import require_auth

try:
    from supabase import create_client, Client
    _supabase_available = True
except ImportError:
    _supabase_available = False

upload_bp = Blueprint("upload", __name__)

# ── Supabase client (lazy singleton) ──────────────────────────────────────────
_supabase: "Client | None" = None

def _get_supabase() -> "Client":
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")   # Use service key (not anon) for signed URLs
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        if not _supabase_available:
            raise RuntimeError("supabase-py is not installed. Run: pip install supabase")
        _supabase = create_client(url, key)
    return _supabase


# ── Helpers ───────────────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {
    "glb", "gltf", "obj", "fbx",
    "usd", "usda", "usdz",
    "abc", "blend", "mtlx", "mtl",
    "exr", "png", "jpg", "jpeg", "zip", "rar",
    "stl", "dae", "3ds", "step", "stp"
}

def _sanitise_filename(name: str) -> str:
    """Replace unsafe characters with underscores."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)

def _extension_allowed(filename: str) -> bool:
    parts = filename.rsplit(".", 1)
    return len(parts) == 2 and parts[-1].lower() in ALLOWED_EXTENSIONS


# ── POST /api/upload-url ──────────────────────────────────────────────────────
@upload_bp.route("/upload-url", methods=["POST"])
@require_auth
def get_upload_url():
    """
    Generate a signed Supabase Storage URL for direct client-side upload.

    The frontend workflow:
      1. Call POST /api/upload-url  →  receive { upload_url, file_url, path }
      2. PUT file bytes to upload_url (signed URL, no auth header needed)
      3. Call POST /api/assets with { project_id, file_url, filename }
    """
    data         = request.get_json(silent=True) or {}
    filename     = _sanitise_filename((data.get("filename") or "").strip())
    project_id   = (data.get("project_id")   or "").strip()
    content_type = (data.get("content_type") or "application/octet-stream").strip()

    # ── Validation ────────────────────────────────────────────────────────────
    errors = []
    if not filename:
        errors.append("filename is required.")
    elif not _extension_allowed(filename):
        errors.append(f"File type not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if not project_id:
        errors.append("project_id is required.")
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    # Build a unique storage path: <user_id>/<project_id>/<uuid>_<filename>
    unique_id   = uuid.uuid4().hex[:12]
    storage_path = f"{g.user_id}/{project_id}/{unique_id}_{filename}"
    bucket_name  = os.getenv("SUPABASE_BUCKET", "forge3d-assets")

    try:
        sb = _get_supabase()
        # Creates a signed URL valid for 5 minutes (300 s)
        response = sb.storage.from_(bucket_name).create_signed_upload_url(storage_path)
        signed_url = response.get("signed_url") or response.get("signedUrl")
    except Exception as e:
        print("Upload URL Generation Error:", e)
        return jsonify({"error": "Could not generate upload URL", "detail": str(e)}), 500

    # Public URL of the file once uploaded
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    public_file_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"

    return jsonify({
        "upload_url": signed_url,
        "file_url":   public_file_url,
        "path":       storage_path,
        "bucket":     bucket_name,
    }), 200
