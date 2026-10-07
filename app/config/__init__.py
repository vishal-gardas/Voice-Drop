"""VoiceDrop - Flask Application Factory"""

import logging
import os

from flask import Flask
from flask_cors import CORS


def create_app(config_name="development"):
    """Create and configure Flask application"""

    app = Flask(__name__)

    # Basic configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-voice-drop")
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # Enable CORS for frontend integration
    CORS(app)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app.logger.info("🚀 VoiceDrop started successfully!")

    return app
