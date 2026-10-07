"""Service imports and initialization"""

from ..config.config import Config
# Import real services
from .gemini_service import GeminiService
from .mapbox_service import MapboxService
from .notification_service import NotificationService
from .real_otp_service import RealOTPService
from .sms_service import SMSService

# Lazy/None service initialization to prevent crashing on import when keys are missing
gemini_service = None
maps_service = None
otp_service = None
sms_service = None
notification_service = None


def get_gemini_service():
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService(Config)
    return gemini_service


def get_maps_service():
    global maps_service
    if maps_service is None:
        maps_service = MapboxService(Config)
    return maps_service


def get_otp_service():
    global otp_service
    if otp_service is None:
        otp_service = RealOTPService(Config)
    return otp_service


def get_sms_service():
    global sms_service
    if sms_service is None:
        sms_service = SMSService(Config)
    return sms_service


def get_notification_service():
    global notification_service
    if notification_service is None:
        notification_service = NotificationService(Config)
    return notification_service


__all__ = [
    "GeminiService",
    "MapboxService",
    "RealOTPService",
    "SMSService",
    "NotificationService",
    "gemini_service",
    "maps_service",
    "otp_service",
    "sms_service",
    "notification_service",
    "get_gemini_service",
    "get_maps_service",
    "get_otp_service",
    "get_sms_service",
    "get_notification_service",
]
