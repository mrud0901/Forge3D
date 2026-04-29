"""
Forge3D – JWT Authentication Utilities
Handles token creation, decoding, and route protection middleware.
"""

import os
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, g

# ── Config ────────────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "forge3d_change_me_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 24))


# ── Token Generation ──────────────────────────────────────────────────────────
def generate_token(user_id: str, email: str) -> str:
    """Generate a signed JWT for the given user."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── Token Decoding ────────────────────────────────────────────────────────────
def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ── Middleware Decorator ──────────────────────────────────────────────────────
def require_auth(f):
    """
    Route decorator that validates the Authorization: Bearer <token> header.
    Injects g.user_id and g.user_email into Flask's request context.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401

        token = auth_header.split(" ", 1)[1].strip()

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

        # Make user data available to the route handler
        g.user_id = payload["sub"]
        g.user_email = payload.get("email", "")

        return f(*args, **kwargs)

    return decorated
