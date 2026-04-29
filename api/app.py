"""
Forge3D – Main Flask Application Entry Point
Vercel-compatible serverless deployment
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from flask import Flask, jsonify
from flask_cors import CORS
import os

from routes.auth_routes import auth_bp
from routes.project_routes import project_bp
from routes.asset_routes import asset_bp
from routes.upload_routes import upload_bp


def create_app():
    app = Flask(__name__)

    # ── CORS ──────────────────────────────────────────────────────────────────
    origins_env = os.getenv("ALLOWED_ORIGINS", "*")
    allowed_origins = [o.strip() for o in origins_env.split(",")] if origins_env != "*" else "*"
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
    )

    # ── Blueprints ─────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp,    url_prefix="/api")
    app.register_blueprint(project_bp, url_prefix="/api")
    app.register_blueprint(asset_bp,   url_prefix="/api")
    app.register_blueprint(upload_bp,  url_prefix="/api")

    # ── Health check ───────────────────────────────────────────────────────────
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "Forge3D API", "version": "1.0.0"}), 200

    # ── Global error handlers ──────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

    return app


# Vercel serverless handler — Vercel looks for `app` at module level
app = create_app()

# Local development
if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV", "production") == "development"
    app.run(debug=debug, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
