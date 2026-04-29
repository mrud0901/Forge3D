"""
Forge3D – Project Routes
All routes require JWT authentication.

POST   /api/projects          → create a project
GET    /api/projects          → list user's projects
DELETE /api/projects/<id>     → delete a project (cascade deletes assets)
"""

from flask import Blueprint, request, jsonify, g

from utils.db import get_db
from utils.auth import require_auth

project_bp = Blueprint("projects", __name__)


# ── POST /api/projects ────────────────────────────────────────────────────────
@project_bp.route("/projects", methods=["POST"])
@require_auth
def create_project():
    """
    Create a new project for the authenticated user.
    Body: { "name": str }
    Returns: { "project": { id, user_id, name, created_at } }
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()

    if not name:
        return jsonify({"error": "Project name is required."}), 400
    if len(name) > 120:
        return jsonify({"error": "Project name must be 120 characters or fewer."}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO projects (user_id, name)
                    VALUES (%s, %s)
                    RETURNING id, user_id, name, created_at
                    """,
                    (g.user_id, name),
                )
                row = cur.fetchone()
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    return jsonify({
        "project": {
            "id": str(row[0]),
            "user_id": str(row[1]),
            "name": row[2],
            "created_at": row[3].isoformat(),
        }
    }), 201


# ── GET /api/projects ─────────────────────────────────────────────────────────
@project_bp.route("/projects", methods=["GET"])
@require_auth
def list_projects():
    """
    Return all projects belonging to the authenticated user.
    Includes asset count per project.
    Query params: ?limit=50&offset=0
    """
    limit  = min(int(request.args.get("limit",  50)), 200)
    offset = max(int(request.args.get("offset",  0)),   0)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        p.id,
                        p.user_id,
                        p.name,
                        p.created_at,
                        COUNT(a.id) AS asset_count
                    FROM projects p
                    LEFT JOIN assets a ON a.project_id = p.id
                    WHERE p.user_id = %s
                    GROUP BY p.id
                    ORDER BY p.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (g.user_id, limit, offset),
                )
                rows = cur.fetchall()
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    return jsonify({
        "projects": [
            {
                "id": str(r[0]),
                "user_id": str(r[1]),
                "name": r[2],
                "created_at": r[3].isoformat(),
                "asset_count": r[4],
            }
            for r in rows
        ]
    }), 200


# ── DELETE /api/projects/<id> ─────────────────────────────────────────────────
@project_bp.route("/projects/<project_id>", methods=["DELETE"])
@require_auth
def delete_project(project_id):
    """
    Delete a project (and cascade-delete its assets).
    Only the owning user may delete.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Ownership check
                cur.execute(
                    "SELECT id FROM projects WHERE id = %s AND user_id = %s",
                    (project_id, g.user_id),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Project not found or access denied."}), 404

                # Delete assets first (or rely on DB cascade if configured)
                cur.execute("DELETE FROM assets WHERE project_id = %s", (project_id,))
                cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))

    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    return jsonify({"message": "Project deleted successfully."}), 200
