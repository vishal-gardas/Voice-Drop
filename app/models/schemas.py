"""Core Pydantic data models for VoiceDrop"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ========== ENUMS ==========


class CallerType(str, Enum):
    """Types of callers"""

    UNKNOWN = "unknown"
    DELIVERY_PERSON = "delivery_person"
    CUSTOMER = "customer"
    OWNER = "owner"


class ConversationStage(str, Enum):
    """Conversation flow stages"""

    START = "start"
    IDENTIFYING_CALLER = "identifying_caller"
    PROCESSING_REQUEST = "processing_request"
    OTP_REQUEST = "otp_request"
    LOCATION_HELP = "location_help"
    ENDING = "ending"
    COMPLETED = "completed"


class UserIntent(str, Enum):
    """User intent classifications"""

    GET_OTP = "get_otp"
    LOCATION_HELP = "location_help"
    ORDER_STATUS = "order_status"
    COMPLAINT = "complaint"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"


class ConversationAction(str, Enum):
    """Actions the system can take"""

    ASK_FOR_INFO = "ask_for_info"
    PROVIDE_OTP = "provide_otp"
    PROVIDE_DIRECTIONS = "provide_directions"
    REQUEST_APPROVAL = "request_approval"
    ESCALATE = "escalate"
    END_CONVERSATION = "end_conversation"


class OrderStatus(str, Enum):
    """Order processing status"""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


# ========== CALL SUMMARY MODELS ==========


class CallSummaryRequest(BaseModel):
    """Request model for call summary generation"""

    callSid: str = Field(..., description="Unique call identifier from Twilio")
    callerNumber: str = Field(..., description="Phone number of the caller")
    userName: str = Field(..., description="Name of the user associated with the call")
    duration: int = Field(..., description="Call duration in seconds")
    transcript: str = Field(
        ..., description="Full conversation transcript with timestamps"
    )
    startTime: str = Field(..., description="Call start time in ISO 8601 format")
    requestType: str = Field(default="call_summary", description="Type of request")


class CallSummaryResponse(BaseModel):
    """Response model for call summary"""

    response_text: str = Field(..., description="Generated summary of the call")
    status: str = Field(
        default="success", description="Status of the summary generation"
    )
    call_duration: Optional[str] = Field(None, description="Formatted call duration")
    key_points: Optional[List[str]] = Field(
        None, description="Key points extracted from the call"
    )
    call_type: Optional[str] = Field(
        None, description="Type of call (delivery, inquiry, etc.)"
    )


# ========== REQUEST/RESPONSE MODELS ==========


class ConversationRequest(BaseModel):
    """Request model for conversation processing"""

    message: str = Field(..., description="User's message")
    caller_type: Optional[CallerType] = CallerType.UNKNOWN
    caller_id: Optional[str] = Field(None, description="Caller identifier")
    firebase_uid: Optional[str] = Field(None, description="Firebase UID")
    session_id: Optional[str] = Field(None, description="Session identifier")

    class Config:
        use_enum_values = True


class ConversationResponse(BaseModel):
    """Response model for conversation processing"""

    response: str = Field(..., description="AI response message")
    action: ConversationAction = Field(..., description="Recommended action")
    stage: ConversationStage = Field(..., description="Current conversation stage")
    caller_type: CallerType = Field(..., description="Identified caller type")
    intent: UserIntent = Field(..., description="Detected user intent")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


# ========== STATE MODELS ==========


class ConversationState(BaseModel):
    """Complete conversation state"""

    session_id: str = Field(..., description="Unique session identifier")
    stage: ConversationStage = ConversationStage.START
    caller_type: CallerType = CallerType.UNKNOWN
    caller_id: Optional[str] = None
    firebase_uid: Optional[str] = None

    # Conversation history
    messages: List[Dict[str, str]] = Field(default_factory=list)

    # Current context
    current_intent: UserIntent = UserIntent.UNKNOWN
    last_action: Optional[ConversationAction] = None

    # Extracted information
    extracted_info: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Flags
    requires_approval: bool = False
    is_escalated: bool = False

    class Config:
        use_enum_values = True


# ========== BUSINESS MODELS ==========


class LocationData(BaseModel):
    """Location information"""

    name: str = Field(..., description="Location name")
    address: Optional[str] = Field(None, description="Full address")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    place_id: Optional[str] = Field(None, description="Google Places ID")
    distance_from_user: Optional[float] = Field(None, description="Distance in KM")


class OrderData(BaseModel):
    """Order information"""

    order_id: str = Field(..., description="Unique order identifier")
    company: str = Field(..., description="Delivery company")
    tracking_id: Optional[str] = Field(None, description="Tracking ID")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    delivery_address: Optional[str] = Field(None, description="Delivery address")
    otp: Optional[str] = Field(None, description="Order OTP")
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class OTPRequest(BaseModel):
    """OTP request model"""

    firebase_uid: str = Field(..., description="Firebase user ID")
    company: str = Field(..., description="Delivery company")
    order_id: Optional[str] = Field(None, description="Order identifier")
    caller_phone: Optional[str] = Field(None, description="Caller phone number")


class OTPResponse(BaseModel):
    """OTP response model"""

    success: bool = Field(..., description="Request success status")
    otp: Optional[str] = Field(None, description="Retrieved OTP")
    order_id: Optional[str] = Field(None, description="Associated order ID")
    formatted_otp: Optional[str] = Field(None, description="OTP formatted for speech")
    error: Optional[str] = Field(None, description="Error message")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now)


# ========== NOTIFICATION MODELS ==========


class NotificationPayload(BaseModel):
    """Notification payload"""

    user_phone: str = Field(..., description="Target phone number")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    approval_token: Optional[str] = Field(None, description="Approval token")
    order_data: Optional[Dict[str, Any]] = Field(None, description="Order data")


# ========== HEALTH CHECK MODELS ==========


class HealthStatus(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Health status")
    timestamp: float = Field(..., description="Timestamp")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")


class ServiceStatus(BaseModel):
    """Individual service status"""

    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    last_check: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = Field(None, description="Last error message")
