"""Real OTP service implementation"""

import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class RealOTPService:
    """Real OTP service for production SMS and call functionality without fallbacks"""

    def __init__(self, config):
        self.config = config
        self.sms_api_key = getattr(config, "SMS_API_KEY", None)
        self.call_api_key = getattr(config, "CALL_API_KEY", None)
        self.otp_store = {}  # In production, use Redis or database
        self.call_count = 0

    def fetch_otp(self, firebase_uid: str, company: str, order_id: str) -> dict:
        """
        Fetch OTP from backend

        Args:
            firebase_uid: User's Firebase UID
            company: Delivery company name
            order_id: Order identifier

        Returns:
            dict: {"success": bool, "otp": str, "message": str, "error": str}
        """
        backend_url = getattr(self.config, "NODEJS_BACKEND_URL", None)
        internal_api_key = getattr(self.config, "INTERNAL_API_KEY", None)

        if not backend_url or not internal_api_key:
            raise ValueError(
                "NODEJS_BACKEND_URL or INTERNAL_API_KEY is not configured. Real OTP backend is required."
            )

        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests library is not available. Real OTP service requires requests."
            )

        try:
            # Exact endpoint format from original.py line 98
            otp_endpoint = f"{backend_url}/api/delivery/otp/{firebase_uid}"

            # Exact params format from original.py line 100-103
            params = {"sender": company, "orderId": order_id}

            # Exact headers from original.py line 105-108
            headers = {
                "Authorization": f"Bearer {internal_api_key}",
                "User-Agent": "DeliveryBot/1.0",
            }

            print(f"📱 [OTP] Fetching from: {otp_endpoint}")
            print(f"📱 [OTP] Params: {params}")

            # Exact request format from original.py line 110-115
            response = requests.get(
                otp_endpoint, params=params, headers=headers, timeout=10
            )

            # Exact response handling from original.py line 117-133
            if response.status_code == 200:
                otp_data = response.json()
                print(f"✅ [OTP] Retrieved successfully: {otp_data}")
                self.call_count += 1
                return {
                    "success": True,
                    "otp": otp_data.get("otp"),
                    "message": otp_data.get("message", "OTP retrieved successfully"),
                }
            elif response.status_code == 404:
                print(f"❌ [OTP] No OTP found for the given parameters")
                return {"success": False, "error": "No OTP found for this delivery"}
            else:
                print(
                    f"❌ [OTP] Backend error: {response.status_code} - {response.text}"
                )
                raise RuntimeError(
                    f"Backend error retrieving OTP: HTTP {response.status_code} - {response.text}"
                )

        except requests.exceptions.Timeout as e:
            print("❌ [OTP] Connection timeout to Node.js backend")
            raise RuntimeError(f"Request timeout connecting to backend: {e}")
        except requests.exceptions.ConnectionError as e:
            print("❌ [OTP] Cannot connect to Node.js backend")
            raise RuntimeError(f"Backend connection failed: {e}")
        except Exception as e:
            print(f"❌ [OTP] Unexpected error: {e}")
            raise

    def configure_backend_connection(self, backend_url: str, api_key: str) -> dict:
        """
        Configure backend connection for OTP service
        """
        try:
            if not REQUESTS_AVAILABLE:
                raise ImportError("requests library not available")

            test_endpoint = f"{backend_url}/api/health"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "VoiceDrop-AI/1.0",
            }

            response = requests.get(test_endpoint, headers=headers, timeout=5)

            if response.status_code == 200:
                self.config.NODEJS_BACKEND_URL = backend_url
                self.config.INTERNAL_API_KEY = api_key

                return {
                    "success": True,
                    "message": f"Backend connected successfully: {backend_url}",
                    "backend_status": (
                        response.json() if response.content else {"status": "ok"}
                    ),
                }
            else:
                return {
                    "success": False,
                    "error": f"Backend connection failed: {response.status_code}",
                    "backend_url": backend_url,
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to connect to backend: {str(e)}",
                "backend_url": backend_url,
            }

    def generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return "".join(random.choices(string.digits, k=6))

    def send_otp_via_sms(
        self, phone_number: str, customer_name: str = None
    ) -> Dict[str, Any]:
        """Send OTP via SMS using real SMS service"""
        if not self.sms_api_key or not REQUESTS_AVAILABLE:
            return {
                "success": False,
                "message": "SMS API key not configured or requests library not available. Real SMS service is required.",
                "method": "SMS",
            }

        try:
            otp = self.generate_otp()

            self.otp_store[phone_number] = {
                "otp": otp,
                "expires_at": datetime.now() + timedelta(minutes=5),
                "attempts": 0,
            }

            result = self._send_real_sms(phone_number, otp, customer_name)
            if result["success"]:
                self.call_count += 1
                return {
                    "success": True,
                    "message": f"OTP sent via SMS to {phone_number}",
                    "otp": otp if self.config.DEBUG else None,
                    "method": "SMS",
                }
            else:
                return {
                    "success": False,
                    "message": f'Failed to send OTP via SMS: {result.get("error")}',
                    "method": "SMS",
                }

        except Exception as e:
            print(f"❌ SMS OTP error: {e}")
            return {
                "success": False,
                "message": f"Failed to send OTP via SMS: {str(e)}",
                "method": "SMS",
            }

    def send_otp_via_call(
        self, phone_number: str, customer_name: str = None
    ) -> Dict[str, Any]:
        """Send OTP via voice call using real call service"""
        if (
            not self.call_api_key
            or not self.config.TWILIO_ACCOUNT_SID
            or not self.config.TWILIO_PHONE_NUMBER
            or not REQUESTS_AVAILABLE
        ):
            return {
                "success": False,
                "message": "Twilio credentials not configured or requests library not available. Real Call service is required.",
                "method": "CALL",
            }

        try:
            otp = self.generate_otp()

            self.otp_store[phone_number] = {
                "otp": otp,
                "expires_at": datetime.now() + timedelta(minutes=5),
                "attempts": 0,
            }

            result = self._make_real_call(phone_number, otp, customer_name)
            if result["success"]:
                self.call_count += 1
                return {
                    "success": True,
                    "message": f"OTP sent via voice call to {phone_number}",
                    "otp": otp if self.config.DEBUG else None,
                    "method": "CALL",
                }
            else:
                return {
                    "success": False,
                    "message": f'Failed to send OTP via voice call: {result.get("error")}',
                    "method": "CALL",
                }

        except Exception as e:
            print(f"❌ Voice call OTP error: {e}")
            return {
                "success": False,
                "message": f"Failed to send OTP via voice call: {str(e)}",
                "method": "CALL",
            }

    def verify_otp(self, phone_number: str, provided_otp: str) -> Dict[str, Any]:
        """Verify the OTP provided by the customer"""
        if phone_number not in self.otp_store:
            return {
                "valid": False,
                "message": "No OTP found for this number. Please request a new OTP.",
            }

        otp_data = self.otp_store[phone_number]

        if datetime.now() > otp_data["expires_at"]:
            del self.otp_store[phone_number]
            return {
                "valid": False,
                "message": "OTP has expired. Please request a new OTP.",
            }

        if otp_data["attempts"] >= 3:
            del self.otp_store[phone_number]
            return {
                "valid": False,
                "message": "Too many attempts. Please request a new OTP.",
            }

        if provided_otp == otp_data["otp"]:
            del self.otp_store[phone_number]
            return {"valid": True, "message": "OTP verified successfully!"}
        else:
            otp_data["attempts"] += 1
            return {
                "valid": False,
                "message": f'Invalid OTP. {3 - otp_data["attempts"]} attempts remaining.',
            }

    def _send_real_sms(
        self, phone_number: str, otp: str, customer_name: str = None
    ) -> Dict[str, Any]:
        """Send SMS using real SMS service"""
        try:
            name_part = f"Hi {customer_name}, " if customer_name else ""
            message = f"{name_part}Your delivery verification OTP is: {otp}. Valid for 5 minutes. - VoiceDrop"

            url = "https://api.msg91.com/api/v5/otp"
            headers = {"authkey": self.sms_api_key, "Content-Type": "application/json"}
            payload = {
                "template_id": "YOUR_TEMPLATE_ID",
                "mobile": phone_number,
                "message": message,
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                return {"success": True, "response": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"SMS API error: {response.status_code}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _make_real_call(
        self, phone_number: str, otp: str, customer_name: str = None
    ) -> Dict[str, Any]:
        """Make voice call using real call service"""
        try:
            name_part = f"Hi {customer_name}, " if customer_name else ""
            message = f"{name_part}Your delivery verification O T P is: {' '.join(otp)}. I repeat, your O T P is: {' '.join(otp)}. Valid for 5 minutes."

            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.config.TWILIO_ACCOUNT_SID}/Calls.json"

            payload = {
                "From": self.config.TWILIO_PHONE_NUMBER,
                "To": phone_number,
                "Twiml": f"<Response><Say voice='alice'>{message}</Say></Response>",
            }

            response = requests.post(
                url,
                data=payload,
                auth=(self.config.TWILIO_ACCOUNT_SID, self.call_api_key),
                timeout=10,
            )

            if response.status_code == 201:
                return {"success": True, "response": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"Call API error: {response.status_code}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_otp_status(self, phone_number: str) -> Dict[str, Any]:
        """Get OTP status for a phone number"""
        if phone_number not in self.otp_store:
            return {"exists": False, "message": "No active OTP for this number"}

        otp_data = self.otp_store[phone_number]
        time_remaining = (otp_data["expires_at"] - datetime.now()).total_seconds()

        if time_remaining <= 0:
            del self.otp_store[phone_number]
            return {"exists": False, "message": "OTP has expired"}

        return {
            "exists": True,
            "time_remaining": int(time_remaining),
            "attempts_used": otp_data["attempts"],
            "attempts_remaining": 3 - otp_data["attempts"],
        }
