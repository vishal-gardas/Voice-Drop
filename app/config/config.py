# Base configuration management for VoiceDrop
import logging
import os


class Config:
    """Base configuration"""

    # Flask settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-voice-drop")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # Application settings
    APP_NAME = "VoiceDrop"
    VERSION = "1.0.0"

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")

    # SMS/Call service API keys
    SMS_API_KEY = os.getenv("SMS_API_KEY")
    CALL_API_KEY = os.getenv("CALL_API_KEY")

    # Twilio specific
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

    # Service configuration
    # Backend Integration
    NODEJS_BACKEND_URL = os.getenv("NODEJS_BACKEND_URL", "http://localhost:3000")
    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

    # Admin Configuration
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "voice-drop-admin-secret")

    # Notification Settings
    OWNER_PHONE_NUMBER = os.getenv("OWNER_PHONE_NUMBER")

    # Mock Mode is disabled in production
    MOCK_MODE = False

    # User Location Settings (VIT Vellore coordinates as default)
    USER_LAT = os.getenv("USER_LAT", "12.974072987767554")
    USER_LNG = os.getenv("USER_LNG", "79.16395954535963")

    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        # Configure logging
        log_level = getattr(logging, Config.LOG_LEVEL.upper())
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        app.logger.info(f"🔧 {Config.APP_NAME} v{Config.VERSION} configured")
        app.logger.info("🧪 Mock mode is disabled")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
