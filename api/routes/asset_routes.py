"""
Forge3D – Asset Routes
All routes require JWT authentication.

POST   /api/assets                    → save file metadata after upload
GET    /api/projects/<id>/assets      → list assets in a project
DELETE /api/assets/<id>               → delete an asset record
"""

from flask import Blueprint, request, jsonify, g

from utils.db import get_db
from utils.auth import require_auth

asset_bp = Blueprint("assets", __name__)

# Allowed 3D file extensions
ALLOWED_EXTENSIONS = {".glb", ".gltf", ".obj", ".fbx", ".usd", ".usda", ".usdz", ".abc", ".blend", ".mtlx", ".mtl", ".exr", ".png", ".jpg", ".jpeg", ".zip", ".rar", ".stl", ".dae", ".3ds", ".step", ".stp"}


def _allowed_filename(filename: str) -> bool:
    """Check if the file extension is in the allowed set."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS


# ── POST /api/assets ──────────────────────────────────────────────────────────
@asset_bp.route("/assets", methods=["POST"])
@require_auth
def create_asset():
    """
    Save file metadata after the file has been uploaded directly to Supabase Storage.
    Body: { "project_id": str, "file_url": str, "filename": str }
    Returns: { "asset": { id, project_id, file_url, filename, created_at } }
    """
    data = request.get_json(silent=True) or {}
    project_id = (data.get("project_id") or "").strip()
    file_url   = (data.get("file_url")   or "").strip()
    filename   = (data.get("filename")   or "").strip()

    # ── Validation ────────────────────────────────────────────────────────────
    errors = []
    if not project_id:
        errors.append("project_id is required.")
    if not file_url:
        errors.append("file_url is required.")
    if not filename:
        errors.append("filename is required.")
    elif not _allowed_filename(filename):
        errors.append(f"File type not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify the project belongs to the requesting user
                cur.execute(
                    "SELECT id FROM projects WHERE id = %s AND user_id = %s",
                    (project_id, g.user_id),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Project not found or access denied."}), 404

                cur.execute(
                    """
                    INSERT INTO assets (project_id, file_url, filename)
                    VALUES (%s, %s, %s)
                    RETURNING id, project_id, file_url, filename, created_at
                    """,
                    (project_id, file_url, filename),
                )
                row = cur.fetchone()
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    return jsonify({
        "asset": {
            "id": str(row[0]),
            "project_id": str(row[1]),
            "file_url": row[2],
            "filename": row[3],
            "created_at": row[4].isoformat(),
        }
    }), 201


# ── GET /api/projects/<id>/assets ─────────────────────────────────────────────
@asset_bp.route("/projects/<project_id>/assets", methods=["GET"])
@require_auth
def list_assets(project_id):
    """
    Return all assets for a given project.
    Query params: ?limit=100&offset=0
    """
    limit  = min(int(request.args.get("limit",  100)), 500)
    offset = max(int(request.args.get("offset",   0)),   0)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Ensure the project belongs to the user before exposing its assets
                cur.execute(
                    "SELECT id FROM projects WHERE id = %s AND user_id = %s",
                    (project_id, g.user_id),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Project not found or access denied."}), 404

                cur.execute(
                    """
                    SELECT id, project_id, file_url, filename, created_at
                    FROM assets
                    WHERE project_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (project_id, limit, offset),
                )
                rows = cur.fetchall()
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    return jsonify({
        "assets": [
            {
                "id": str(r[0]),
                "project_id": str(r[1]),
                "file_url": r[2],
                "filename": r[3],
                "created_at": r[4].isoformat(),
            }
            for r in rows
        ]
    }), 200


# ── DELETE /api/assets/<id> ───────────────────────────────────────────────────
@asset_bp.route("/assets/<asset_id>", methods=["DELETE"])
@require_auth
def delete_asset(asset_id):
    """
    Delete an asset record.
    Only the user who owns the parent project may delete.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Join to verify ownership through the project
                cur.execute(
                    """
                    SELECT a.id
                    FROM assets a
                    JOIN projects p ON p.id = a.project_id
                    WHERE a.id = %s AND p.user_id = %s
                    """,
                    (asset_id, g.user_id),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Asset not found or access denied."}), 404

                cur.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    return jsonify({"message": "Asset deleted successfully."}), 200
