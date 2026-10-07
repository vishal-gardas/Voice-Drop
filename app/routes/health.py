"""Health check and status endpoints"""

import os
import sys
import time

from flask import Blueprint, jsonify

from ..config.config import Config
from ..models import HealthStatus

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Basic health check endpoint with Pydantic model"""
    config = Config()
    health_data = HealthStatus(
        status="healthy",
        timestamp=time.time(),
        app_name=config.APP_NAME,
        version=config.VERSION,
    )

    return jsonify(health_data.model_dump()), 200


@health_bp.route("/status", methods=["GET"])
def status_check():
    """Detailed status information"""
    config = Config()
    return (
        jsonify(
            {
                "application": {
                    "name": config.APP_NAME,
                    "version": config.VERSION,
                    "debug": config.DEBUG,
                },
                "system": {
                    "python_version": sys.version,
                    "platform": sys.platform,
                    "cwd": os.getcwd(),
                },
                "services": {
                    "gemini": (
                        "configured" if config.GEMINI_API_KEY else "not_configured"
                    ),
                    "mapbox": (
                        "configured" if config.MAPBOX_API_KEY else "not_configured"
                    ),
                    "notifications": (
                        "configured" if config.INTERNAL_API_KEY else "not_configured"
                    ),
                    "otp": "configured",
                },
                "timestamp": time.time(),
            }
        ),
        200,
    )


@health_bp.route("/ping", methods=["GET"])
def ping():
    """Simple ping endpoint"""
    return jsonify({"message": "pong", "timestamp": time.time()}), 200


@health_bp.route("/models/test", methods=["GET"])
def test_models():
    """Test endpoint to validate Pydantic models"""

    from ..models import (CallerType, ConversationAction, ConversationRequest,
                          ConversationResponse, ConversationStage,
                          LocationData, OrderData, OrderStatus,
                          UserIntent)

    # Test ConversationRequest
    test_request = ConversationRequest(
        message="Hello, I need help with delivery",
        caller_type=CallerType.DELIVERY_PERSON,
        caller_id="test_caller_123",
    )

    # Test ConversationResponse
    test_response = ConversationResponse(
        response="Hello! I can help you with your delivery. What do you need?",
        action=ConversationAction.ASK_FOR_INFO,
        stage=ConversationStage.PROCESSING_REQUEST,
        caller_type=CallerType.DELIVERY_PERSON,
        intent=UserIntent.GREETING,
        confidence=0.95,
        session_id="session_123",
    )

    # Test OrderData
    test_order = OrderData(
        order_id="ORDER_123",
        company="Swiggy",
        tracking_id="TRACK_456",
        status=OrderStatus.PENDING,
    )

    # Test LocationData
    test_location = LocationData(
        name="Pizza Hut",
        address="123 Main Street, City",
        latitude=12.9716,
        longitude=77.5946,
    )

    return (
        jsonify(
            {
                "message": "All Pydantic models working correctly!",
                "test_data": {
                    "conversation_request": test_request.model_dump(),
                    "conversation_response": test_response.model_dump(),
                    "order_data": test_order.model_dump(),
                    "location_data": test_location.model_dump(),
                },
                "timestamp": time.time(),
            }
        ),
        200,
    )
