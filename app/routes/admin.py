"""Admin and backend configuration routes"""

from flask import Blueprint, jsonify, request

from ..config.config import Config
from ..services.service_factory import ServiceFactory

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Initialize services
config = Config()
service_factory = ServiceFactory(config)


@admin_bp.route("/configure-backend", methods=["POST"])
def configure_backend():
    """
    Configure backend connection for AI model
    Endpoint for your Node.js backend to register with the AI model
    """
    try:
        data = request.get_json()

        required_fields = ["backend_url", "api_key"]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Missing required fields: {', '.join(missing_fields)}",
                    }
                ),
                400,
            )

        backend_url = data.get("backend_url")
        api_key = data.get("api_key")

        admin_secret = data.get("admin_secret")
        expected_secret = getattr(config, "ADMIN_SECRET", "voice-drop-admin-secret")

        if admin_secret != expected_secret:
            return jsonify({"success": False, "error": "Invalid admin secret"}), 401

        print(f"🔧 [ADMIN] Configuring backend: {backend_url}")

        otp_service = service_factory.otp_service
        result = otp_service.configure_backend_connection(backend_url, api_key)

        if result["success"]:
            return jsonify(
                {
                    "success": True,
                    "message": "Backend configured successfully",
                    "backend_url": backend_url,
                    "configuration": result,
                    "ai_model_endpoints": {
                        "generate": "/generate",
                        "get_otp": "/api/get-otp",
                        "health": "/health",
                        "status": "/api/status",
                    },
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to configure backend",
                        "details": result,
                    }
                ),
                500,
            )

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Configuration failed: {str(e)}"}),
            500,
        )


@admin_bp.route("/test-backend", methods=["POST"])
def test_backend():
    """Test backend SMS connectivity and parsing"""
    try:
        data = request.get_json() or {}
        user_id = data.get("userId", data.get("firebase_uid", "test-user-123"))

        sms_service = service_factory.sms_service

        backend_result = sms_service.configure_backend_connection(
            getattr(config, "NODEJS_BACKEND_URL", "http://localhost:3000"),
            getattr(config, "INTERNAL_API_KEY", "test-key"),
        )

        bulk_result = sms_service.fetch_latest_otps(user_id, 10)
        otp_result = sms_service.get_otp_from_sms(user_id, "Zomato")

        return jsonify(
            {
                "success": True,
                "message": "Bulk SMS backend connectivity tests completed",
                "tests": {
                    "backend_connection": backend_result,
                    "bulk_sms_fetch": bulk_result,
                    "otp_extraction": otp_result,
                },
                "configuration": {
                    "backend_url": getattr(config, "NODEJS_BACKEND_URL", None),
                    "has_api_key": bool(getattr(config, "INTERNAL_API_KEY", None)),
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"Test failed: {str(e)}"}), 500


@admin_bp.route("/test-sms-parsing", methods=["POST"])
def test_sms_parsing():
    """Test SMS parsing functionality with sample messages"""
    try:
        data = request.get_json() or {}
        test_messages = data.get(
            "messages",
            [
                "Your Zomato order OTP is 1234. Order ID: ZMT123456789",
                "Swiggy delivery OTP: 5678. Track: SWG987654321",
                "Amazon delivery code 9999 for order AMZN1234567890",
                "Your OTP for delivery is 4444. Delivery by Raj: 9876543210",
            ],
        )

        from app.utils.sms_parser import SMSParser

        parser = SMSParser()

        results = []
        for message in test_messages:
            parsed = parser.parse_sms(message)
            results.append(
                {
                    "original_message": message,
                    "extracted_otp": parsed.otp,
                    "extracted_tracking": parsed.tracking_id,
                    "detected_company": parsed.company,
                    "confidence_score": parsed.confidence_score,
                    "delivery_details": parser.extract_delivery_details(message),
                }
            )

        return jsonify(
            {
                "success": True,
                "message": f"SMS parsing test completed for {len(test_messages)} messages",
                "results": results,
                "parser_info": {
                    "supported_companies": list(parser.company_patterns.keys()),
                    "total_patterns": len(parser.generic_patterns),
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/backend-status", methods=["GET"])
def backend_status():
    """Get current backend configuration status"""
    try:
        return jsonify(
            {
                "success": True,
                "configuration": {
                    "backend_url": getattr(config, "NODEJS_BACKEND_URL", None),
                    "has_internal_api_key": bool(
                        getattr(config, "INTERNAL_API_KEY", None)
                    ),
                    "ai_model_url": request.host_url.rstrip("/"),
                    "available_endpoints": [
                        "/generate",
                        "/api/get-otp",
                        "/api/admin/configure-backend",
                        "/api/admin/test-backend",
                        "/api/admin/backend-status",
                        "/health",
                        "/api/status",
                    ],
                },
                "service_status": service_factory.get_service_status(),
            }
        )

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Status check failed: {str(e)}"}),
            500,
        )


@admin_bp.route("/update-config", methods=["POST"])
def update_config():
    """Update AI model configuration"""
    try:
        data = request.get_json()

        admin_secret = data.get("admin_secret")
        expected_secret = getattr(config, "ADMIN_SECRET", "voice-drop-admin-secret")

        if admin_secret != expected_secret:
            return jsonify({"success": False, "error": "Invalid admin secret"}), 401

        updated_fields = []

        allowed_fields = {
            "NODEJS_BACKEND_URL": "backend_url",
            "INTERNAL_API_KEY": "internal_api_key",
            "OWNER_PHONE_NUMBER": "owner_phone",
        }

        for config_key, data_key in allowed_fields.items():
            if data_key in data:
                val = data[data_key]
                setattr(config, config_key, val)
                updated_fields.append(config_key)

        service_factory.reset_services()

        return jsonify(
            {
                "success": True,
                "message": f"Updated {len(updated_fields)} configuration fields",
                "updated_fields": updated_fields,
                "current_config": {
                    "backend_url": getattr(config, "NODEJS_BACKEND_URL", None),
                    "has_api_key": bool(getattr(config, "INTERNAL_API_KEY", None)),
                },
            }
        )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "error": f"Configuration update failed: {str(e)}"}
            ),
            500,
        )
