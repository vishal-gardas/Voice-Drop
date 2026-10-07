"""Notification service for sending push notifications to the owner"""

import time
import uuid
from typing import Any, Dict

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class NotificationService:
    """Service for sending notifications to the owner about unknown callers"""

    def __init__(self, config):
        self.config = config
        self.backend_url = config.NODEJS_BACKEND_URL
        self.api_key = config.INTERNAL_API_KEY
        self.owner_phone = getattr(config, "OWNER_PHONE_NUMBER", None)
        self.call_count = 0

    def send_push_notification(
        self, phone_number: str, message: str, approval_token: str = None
    ) -> bool:
        """Send push notification to Android app via Node.js backend"""
        if not REQUESTS_AVAILABLE or not self.backend_url:
            print(
                "⚠️ Notification service not available (missing requests or backend URL)"
            )
            return False

        try:
            if not approval_token:
                approval_token = str(uuid.uuid4())

            notification_endpoint = f"{self.backend_url}/api/send-notification"

            payload = {
                "user_phone": phone_number,
                "title": "Delivery Verification Required",
                "message": message,
                "type": "delivery_approval",
                "approval_token": approval_token,
                "action_required": True,
                "timestamp": int(time.time()),
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "DeliveryBot/1.0",
            }

            print(f"📱 [NOTIFICATION] Sending to Node.js: {notification_endpoint}")
            print(f"📱 [NOTIFICATION] Payload: {payload}")

            response = requests.post(
                notification_endpoint, json=payload, headers=headers, timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                print(
                    f"✅ [NOTIFICATION] Push notification sent successfully: {result}"
                )
                self.call_count += 1
                return True
            else:
                print(
                    f"❌ [NOTIFICATION] Failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            if "Timeout" in str(e):
                print("❌ [NOTIFICATION] Timeout connecting to Node.js backend")
            elif "Connection" in str(e):
                print("❌ [NOTIFICATION] Cannot connect to Node.js backend")
            else:
                print(f"❌ [NOTIFICATION] Unexpected error: {e}")
            return False

    def send_unknown_caller_notification(self, caller_info: Dict[str, Any]) -> bool:
        """Send notification about unknown caller to the owner"""
        if not self.owner_phone:
            print("⚠️ Owner phone number not configured")
            return False

        name = caller_info.get("name", "Unknown caller")
        purpose = caller_info.get("purpose", "Not specified")
        callback_number = caller_info.get("phone", "Not provided")

        additional_details = caller_info.get("additional_details", [])
        details_text = ""
        if additional_details:
            details_text = f" Additional info: {' | '.join(additional_details)}"

        message = f"Unknown caller: {name}. Purpose: {purpose}. Callback: {callback_number}{details_text}"

        return self.send_push_notification(
            phone_number=self.owner_phone,
            message=message,
            approval_token=str(uuid.uuid4()),
        )

    def send_urgent_notification(self, message: str) -> bool:
        """Send urgent notification to the owner"""
        if not self.owner_phone:
            print("⚠️ Owner phone number not configured for urgent notifications")
            return False

        return self.send_push_notification(
            phone_number=self.owner_phone,
            message=f"🚨 URGENT: {message}",
            approval_token=str(uuid.uuid4()),
        )

    def get_notification_status(self) -> Dict[str, Any]:
        """Get notification service status for debugging"""
        return {
            "service_name": "NotificationService",
            "backend_configured": bool(self.backend_url),
            "api_key_configured": bool(self.api_key),
            "owner_phone_configured": bool(self.owner_phone),
            "requests_available": REQUESTS_AVAILABLE,
            "notifications_sent": self.call_count,
        }
