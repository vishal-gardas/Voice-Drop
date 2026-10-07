import sys

# Reconfigure standard output streams to use UTF-8 to prevent encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

from app.config.config import Config
from app.routes.admin import admin_bp
from app.routes.call_summary import call_summary_bp
from app.routes.conversation import conversation_bp
from app.routes.health import health_bp
from app.routes.speech import speech_bp


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)

    # Load configuration
    config = Config()
    app.config.from_object(config)

    # Enable CORS
    CORS(app)

    # Register blueprints
    app.register_blueprint(conversation_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(call_summary_bp)
    app.register_blueprint(speech_bp)

    # Health check route
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(
            {
                "status": "healthy",
                "gemini_configured": bool(config.GEMINI_API_KEY),
                "mapbox_configured": bool(config.MAPBOX_API_KEY),
                "nodejs_backend_configured": bool(config.NODEJS_BACKEND_URL),
                "internal_api_configured": bool(config.INTERNAL_API_KEY),
            }
        )

    @app.route("/", methods=["GET"])
    def root():
        return jsonify(
            {
                "message": "VoiceDrop API",
                "version": config.VERSION,
                "mode": "production",
                "endpoints": [
                    "/health",
                    "/generate",
                    "/api/get-otp",
                    "/add-order",
                    "/list-orders",
                    "/api/status",
                ],
            }
        )

    # API status endpoint for debugging services
    @app.route("/api/status", methods=["GET"])
    def get_api_status():
        """Get detailed API and service status"""
        try:
            from datetime import datetime

            from app.services.conversation_handler import ConversationHandler

            handler = ConversationHandler(config)

            status = {
                "app_name": config.APP_NAME,
                "version": config.VERSION,
                "mode": "production",
                "services": handler.service_factory.get_service_status(),
                "api_keys": {
                    "gemini": bool(config.GEMINI_API_KEY),
                    "mapbox": bool(config.MAPBOX_API_KEY),
                    "sms": bool(getattr(config, "SMS_API_KEY", None)),
                    "call": bool(getattr(config, "CALL_API_KEY", None)),
                },
                "timestamp": datetime.now().isoformat(),
            }

            return jsonify(status)
        except Exception as e:
            from datetime import datetime

            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Failed to get status: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    return app


# Create app instance for serverless deployment
app = create_app()

if __name__ == "__main__":
    # Print startup information
    config = Config()
    print("🚀 Starting VoiceDrop Flask API...")
    print("📍 Mode: Production")
    print(
        f"🗝️ Gemini API: {'✅' if config.GEMINI_API_KEY else '❌ (Required for Operation)'}"
    )
    print(
        f"🗺️ Mapbox API: {'✅' if config.MAPBOX_API_KEY else '❌ (Required for Operation)'}"
    )
    print(f"📱 Node.js Backend: {config.NODEJS_BACKEND_URL}")
    print(
        f"🔐 Notification System: {'✅' if config.INTERNAL_API_KEY and config.OWNER_PHONE_NUMBER else '❌'}"
    )

    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Running on port: {port}")

    app.run(host="0.0.0.0", port=port, debug=config.DEBUG)
