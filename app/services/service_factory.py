"""Service factory for managing real services"""

from app.config.config import Config


class ServiceFactory:
    """Factory class to provide services"""

    def __init__(self, config: Config):
        self.config = config
        self._gemini_service = None
        self._maps_service = None
        self._otp_service = None
        self._notification_service = None

    @property
    def gemini_service(self):
        """Get Gemini service"""
        if self._gemini_service is None:
            from app.services.gemini_service import GeminiService

            self._gemini_service = GeminiService(self.config)
        return self._gemini_service

    @property
    def maps_service(self):
        """Get Maps service"""
        if self._maps_service is None:
            from app.services.mapbox_service import MapboxService

            self._maps_service = MapboxService(self.config)
        return self._maps_service

    @property
    def notification_service(self):
        """Get Notification service"""
        if self._notification_service is None:
            from app.services.notification_service import NotificationService

            self._notification_service = NotificationService(self.config)
        return self._notification_service

    @property
    def otp_service(self):
        """Get SMS/OTP service"""
        if self._otp_service is None:
            from app.services.sms_service import SMSService

            self._otp_service = SMSService(self.config)
        return self._otp_service

    @property
    def sms_service(self):
        """Get SMS service - alias for otp_service"""
        return self.otp_service

    def get_service_status(self):
        """Get status of services"""
        try:
            return self.otp_service.get_service_status()
        except Exception as e:
            return {"sms_service": "unknown", "error": str(e)}

    def reset_services(self):
        """Reset service instances to pick up configuration updates"""
        self._gemini_service = None
        self._maps_service = None
        self._otp_service = None
        self._notification_service = None
