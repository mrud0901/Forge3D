"""
Forge3D – Authentication Routes
POST /api/signup  → register a new user
POST /api/login   → authenticate and return JWT
GET  /api/me      → return current user profile (protected)
"""

import re
import bcrypt
from flask import Blueprint, request, jsonify, g

from utils.db import get_db
from utils.auth import generate_token, require_auth

auth_bp = Blueprint("auth", __name__)

# ── Helpers ───────────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def _validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

def _check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── POST /api/signup ──────────────────────────────────────────────────────────
@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    Register a new user.
    Body: { "email": str, "password": str }
    Returns: { "token": str, "user": { id, email, created_at } }
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # ── Validation ────────────────────────────────────────────────────────────
    errors = []
    if not email:
        errors.append("Email is required.")
    elif not _validate_email(email):
        errors.append("Invalid email format.")
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    password_hash = _hash_password(password)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check for duplicate
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    return jsonify({"error": "An account with this email already exists."}), 409

                cur.execute(
                    """
                    INSERT INTO users (email, password_hash)
                    VALUES (%s, %s)
                    RETURNING id, email, created_at
                    """,
                    (email, password_hash),
                )
                row = cur.fetchone()

    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    user_id, user_email, created_at = row
    token = generate_token(str(user_id), user_email)

    return jsonify({
        "token": token,
        "user": {
            "id": str(user_id),
            "email": user_email,
            "created_at": created_at.isoformat(),
        },
    }), 201


# ── POST /api/login ───────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user.
    Body: { "email": str, "password": str }
    Returns: { "token": str, "user": { id, email, created_at } }
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
                    (email,),
                )
                row = cur.fetchone()
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    # Use constant-time comparison to prevent user-enumeration timing attacks
    if not row or not _check_password(password, row[2]):
        return jsonify({"error": "Invalid email or password."}), 401

    user_id, user_email, _, created_at = row
    token = generate_token(str(user_id), user_email)

    return jsonify({
        "token": token,
        "user": {
            "id": str(user_id),
            "email": user_email,
            "created_at": created_at.isoformat(),
        },
    }), 200


# ── GET /api/me ───────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    """Return the currently authenticated user's profile."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, created_at FROM users WHERE id = %s",
                    (g.user_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        return jsonify({"error": "Database error", "detail": str(e)}), 500

    if not row:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "user": {
            "id": str(row[0]),
            "email": row[1],
            "created_at": row[2].isoformat(),
        }
    }), 200
