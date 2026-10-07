"""Conversation handler matching original.py flow exactly"""

import sys

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

import uuid
from typing import Any, Dict, Tuple

from ..utils.language_utils import get_response_templates
from ..utils.text_processing import (detect_user_intent,
                                     format_number_for_speech,
                                     format_otp_for_speech)
from .delivery_guidance_service import DeliveryGuidanceService
from .service_factory import ServiceFactory


class ConversationHandler:
    """Main conversation handler that matches original.py logic"""

    def __init__(self, config):
        self.config = config
        self.service_factory = ServiceFactory(config)

        # Initialize delivery guidance service (will use dynamic coordinates)
        self.delivery_guide = DeliveryGuidanceService(config)

        # ORDER_WALLET equivalent - stores pending orders
        self.order_wallet = {}

        # Store current delivery location (updated per call)
        self.current_delivery_location = None

    @property
    def gemini_service(self):
        return self.service_factory.gemini_service

    @property
    def maps_service(self):
        return self.service_factory.maps_service

    @property
    def otp_service(self):
        return self.service_factory.otp_service

    @property
    def notification_service(self):
        return self.service_factory.notification_service

    def extract_information_with_ai(
        self, message: str, collected_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegate information extraction to the gemini service"""
        return self.gemini_service.extract_information_with_ai(message, collected_info)

    def identify_caller_role(self, message: str) -> str:
        """Identify if the caller is delivery person or unknown"""
        message_lower = message.lower().strip()

        # Check for delivery-related keywords (exact matching)
        delivery_keywords = [
            "delivery",
            "parcel",
            "package",
            "courier",
            "order",
            "shipped",
        ]

        if any(keyword in message_lower for keyword in delivery_keywords):
            return "delivery"

        # Try fuzzy matching for company names that might be misheard
        from ..utils.text_processing import fuzzy_match_company_name

        fuzzy_result = fuzzy_match_company_name(message)
        if fuzzy_result and fuzzy_result["confidence"] >= 0.65:
            print(
                f"🎯 [CALLER ID] Identified as delivery person via fuzzy company match: {fuzzy_result['company']}"
            )
            return "delivery"

        # Otherwise, treat as unknown caller
        return "unknown"

    def handle_delivery_logic(
        self,
        message: str,
        stage: str,
        collected_info: Dict[str, Any],
        caller_id=None,
        response_language: str = "en",
        delivery_location: Dict[str, Any] = None,
    ) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """
        Enhanced delivery logic with proper conversational flow matching original.py:
        1. "How may I assist?"
        2. Caller: "I have delivery from Amazon"
        3. AI: "Do you need help getting here or are you here?"
        4. If help needed -> provide directions
        5. When reached -> "Do you need OTP?"
        """
        intent = detect_user_intent(message)
        action = {}
        templates = get_response_templates(response_language)

        # Update delivery location if provided (live coordinates from backend)
        if delivery_location:
            self.current_delivery_location = delivery_location
            lat = delivery_location.get("latitude")
            lng = delivery_location.get("longitude")
            print(f"📍 [DELIVERY LOCATION] Using live coordinates: {lat}, {lng}")

        print(f"\n--- [DELIVERY LOGIC] START ---")
        print(
            f"--- [DELIVERY LOGIC] Stage: {stage}, Intent: {intent}, Language: {response_language} ---"
        )
        print(f"--- [DELIVERY LOGIC] Message: '{message}' ---")
        print(f"--- [DELIVERY LOGIC] Current collected_info: {collected_info} ---")

        # Store language in collected_info for consistency
        collected_info["language"] = "en"

        # Enhanced OTP request detection
        message_lower = message.lower().strip()
        is_otp_request = intent == "requesting_otp" or any(
            phrase in message_lower
            for phrase in ["need otp", "want otp", "give otp", "otp code"]
        )

        # Handle OTP requests at any stage
        if is_otp_request:
            print("--- [DELIVERY LOGIC] OTP request detected, redirecting ---")
            return self.handle_direct_otp_request(message, stage, collected_info, "en")

        # Check if we're in an OTP-specific flow
        if stage in [
            "asking_otp_company",
            "asking_order_id",
            "providing_otp",
            "otp_provided",
        ]:
            return self.handle_direct_otp_request(message, stage, collected_info, "en")

        # Stage 1: Initial greeting - "How may I assist?"
        if stage == "start":
            print("--- [DELIVERY LOGIC] Initial greeting stage ---")

            # Check if this is already a delivery message
            if intent == "initial_delivery" or any(
                k in message.lower() for k in ["delivery", "parcel", "package"]
            ):
                extracted_info = self.extract_information_with_ai(
                    message, collected_info
                )
                collected_info.update(extracted_info)
                company = collected_info.get("company")

                if company:
                    print(
                        f"--- [DELIVERY LOGIC] Company '{company}' identified, asking for location help ---"
                    )
                    response = f"Hi! I see you have a delivery from {company}. Do you need help getting here, or are you already here?"
                    return response, "asking_location_help", collected_info, action
                else:
                    response = "Hi! I can help with your delivery. Which company is this delivery from?"
                    return response, "asking_company_first", collected_info, action
            elif any(
                greeting in message.lower() for greeting in ["hello", "hi", "hey"]
            ):
                response = "Hello! How can I help you today?"
                return response, "waiting_for_context", collected_info, action
            else:
                return templates["greeting"], "initial_greeting", collected_info, action

        # Stage 1.5: Waiting for context after greeting
        if stage == "waiting_for_context":
            if intent == "initial_delivery" or any(
                k in message.lower() for k in ["delivery", "parcel", "package"]
            ):
                extracted_info = self.extract_information_with_ai(
                    message, collected_info
                )
                collected_info.update(extracted_info)
                company = collected_info.get("company")

                if company:
                    print(
                        f"--- [DELIVERY LOGIC] Company '{company}' identified, asking for location help ---"
                    )
                    response = f"I see you have a delivery from {company}. Do you need help getting here, or are you already here?"
                    return response, "asking_location_help", collected_info, action
                else:
                    response = (
                        "I can help with your delivery. Which company is this from?"
                    )
                    return response, "asking_company_first", collected_info, action
            else:
                return self.handle_unknown_logic(
                    message, "start", collected_info, caller_id, "en"
                )

        # Stage 2: After initial greeting, waiting for delivery mention
        if stage == "initial_greeting":
            if intent == "initial_delivery" or any(
                k in message.lower() for k in ["delivery", "parcel", "package"]
            ):
                extracted_info = self.extract_information_with_ai(
                    message, collected_info
                )
                collected_info.update(extracted_info)
                company = collected_info.get("company")

                if company:
                    response = f"I see you have a delivery from {company}. Do you need help getting here, or are you already here?"
                    return response, "asking_location_help", collected_info, action
                else:
                    response = (
                        "I can help with your delivery. Which company is this from?"
                    )
                    return response, "asking_company_first", collected_info, action
            else:
                return self.handle_unknown_logic(
                    message, "start", collected_info, caller_id, "en"
                )

        # Stage 3: Asked for company name first
        if stage == "asking_company_first":
            extracted_info = self.extract_information_with_ai(message, collected_info)
            company = extracted_info.get("company") or message.strip().title()
            collected_info["company"] = company

            response = f"Thank you! So you have a delivery from {company}. Do you need help getting here, or are you already here?"
            return response, "asking_location_help", collected_info, action

        # Stage 4: Asking if they need location help
        if stage == "asking_location_help":
            print("--- [DELIVERY LOGIC] Processing location help response ---")
            message_lower = message.lower().strip()

            if any(
                phrase in message_lower
                for phrase in [
                    "need help",
                    "help",
                    "directions",
                    "how to get",
                    "where is",
                    "guide me",
                    "lost",
                ]
            ):
                response = "I'd be happy to help guide you here. What's your current location or a nearby landmark?"
                return response, "getting_current_location", collected_info, action

            elif any(
                phrase in message_lower
                for phrase in [
                    "here",
                    "arrived",
                    "at the location",
                    "reached",
                    "outside",
                    "at your place",
                    "at the door",
                ]
            ):
                print(
                    "--- [DELIVERY LOGIC] Caller says they're here, checking for OTP need ---"
                )
                return self.handle_arrival_and_otp_check(collected_info, "en")

            else:
                response = "Are you asking for directions to get here, or have you already arrived at the location?"
                return response, "asking_location_help", collected_info, action

        # Stage 5: Getting their current location for directions
        if stage == "getting_current_location":
            print("--- [DELIVERY LOGIC] Processing current location for directions ---")

            destination_coords = None
            if self.current_delivery_location:
                destination_coords = (
                    self.current_delivery_location.get("latitude"),
                    self.current_delivery_location.get("longitude"),
                )

            guidance_result = self.delivery_guide.guide_delivery_person(
                landmark_description=message,
                max_radius_km=1.0,
                destination_coords=destination_coords,
            )

            if guidance_result["success"]:
                landmark = guidance_result["landmark"]
                route = guidance_result["route"]
                directions = guidance_result["turn_by_turn_directions"]

                collected_info["current_location"] = {
                    "name": landmark["name"],
                    "address": landmark["address"],
                    "distance_km": landmark["distance_from_destination"],
                }

                response_parts = [
                    f"Perfect! I found you near {landmark['name']}.",
                    f"You're about {route['total_distance_km']}km away, roughly {route['estimated_time_minutes']} minutes walk.",
                    "Here are your directions:",
                ]

                for i, step in enumerate(directions[:3], 1):
                    response_parts.append(f"{i}. {step}")

                response_parts.append("Let me know when you arrive!")
                response_text = " ".join(response_parts)
                return response_text, "traveling_to_location", collected_info, action
            else:
                suggestion = guidance_result.get(
                    "suggestion", "Can you describe another nearby landmark?"
                )
                response = f"I couldn't find '{message}' near the delivery address. {suggestion}"
                return response, "getting_current_location", collected_info, action

        # Stage 6: They're traveling, waiting for arrival
        if stage == "traveling_to_location":
            message_lower = message.lower().strip()

            if any(
                phrase in message_lower
                for phrase in [
                    "arrived",
                    "here",
                    "reached",
                    "at the location",
                    "outside",
                    "at your place",
                    "at the door",
                ]
            ):
                print("--- [DELIVERY LOGIC] Caller has arrived, checking for OTP ---")
                return self.handle_arrival_and_otp_check(
                    collected_info, response_language
                )

            elif any(
                phrase in message_lower
                for phrase in ["lost", "can't find", "help", "confused", "where"]
            ):
                return (
                    "What landmarks can you see around you? I can help guide you from there.",
                    "getting_current_location",
                    collected_info,
                    action,
                )

            else:
                return (
                    "Let me know when you reach the location!",
                    "traveling_to_location",
                    collected_info,
                    action,
                )

        return self.handle_existing_delivery_logic(
            message, stage, collected_info, intent, action
        )

    def handle_arrival_and_otp_check(
        self, collected_info: Dict[str, Any], response_language: str = "en"
    ) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """Handle when delivery person arrives and check if they need OTP"""
        print("--- [DELIVERY LOGIC] Handling arrival and OTP check ---")

        company = collected_info.get("company")
        if not company:
            response = "Great! You're here. Which company is this delivery from?"
            return response, "asking_company_for_otp", collected_info, {}

        order_id = str(uuid.uuid4())
        self.order_wallet[order_id] = {
            "company": company,
            "status": "approved",
            "otp": "123456",
        }
        collected_info["order_id"] = order_id

        response = (
            f"Perfect! You've arrived with the {company} delivery. Do you need the OTP?"
        )

        return response, "asking_if_otp_needed", collected_info, {}

    def handle_existing_delivery_logic(
        self,
        message: str,
        stage: str,
        collected_info: Dict[str, Any],
        intent: str,
        action: Dict[str, Any],
    ) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """Handle the existing delivery logic for OTP verification"""

        if stage == "asking_if_otp_needed":
            message_lower = message.lower().strip()

            if any(
                phrase in message_lower
                for phrase in ["yes", "yeah", "yep", "need", "otp", "code"]
            ):
                company = collected_info.get("company") or "delivery"
                return (
                    "",
                    "requesting_sms_otp",
                    collected_info,
                    {"type": "REQUEST_SMS_OTP", "company": company},
                )

            elif any(
                phrase in message_lower
                for phrase in ["no", "nope", "don't need", "not needed"]
            ):
                goodbye_msg = "Alright! Have a great day and safe delivery!"
                return goodbye_msg, "end_of_call", collected_info, action
            else:
                clarify_msg = "Do you need me to provide the OTP for this delivery? Please say yes or no."
                return clarify_msg, "asking_if_otp_needed", collected_info, action

        if stage == "asking_company_for_otp":
            extracted_info = self.extract_information_with_ai(message, collected_info)
            company = extracted_info.get("company") or message.strip().title()
            collected_info["company"] = company
            return self.handle_arrival_and_otp_check(collected_info, "en")

        if stage == "asking_otp_company":
            extracted_info = self.extract_information_with_ai(message, collected_info)
            company = extracted_info.get("company") or message.strip().title()
            collected_info["company"] = company
            return self.handle_direct_otp_request(
                message, "providing_otp", collected_info, "en"
            )

        if intent == "ending_conversation":
            return (
                "You're welcome! Have a safe delivery!",
                "end_of_call",
                collected_info,
                action,
            )

        return (
            "I'm here to help with your delivery. What can I assist you with?",
            stage,
            collected_info,
            action,
        )

    def handle_direct_otp_request(
        self,
        message: str,
        stage: str,
        collected_info: Dict[str, Any],
        response_language: str = "en",
    ) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """Handle OTP requests directly without SMS integration"""
        action = {}

        print(f"🔐 [DIRECT OTP] Stage: {stage}, Message: '{message}'")

        company = collected_info.get("company")
        if not company:
            extracted_info = self.extract_information_with_ai(message, collected_info)
            company = extracted_info.get("company")

            if company:
                collected_info.update(extracted_info)
                print(f"🔐 [DIRECT OTP] Company extracted: {company}")
            else:
                response_text = "Which company is this OTP request for?"
                return response_text, "asking_otp_company", collected_info, action

        print(f"🔐 [DIRECT OTP] Providing OTP for company: {company}")

        order_id = collected_info.get("order_id")
        if not order_id:
            order_id = str(uuid.uuid4())
            self.order_wallet[order_id] = {
                "company": company,
                "status": "approved",
                "otp": "123456",
            }
            collected_info["order_id"] = order_id

        firebase_uid = collected_info.get("firebaseUid", "demo-user")
        otp_result = self.otp_service.fetch_otp(firebase_uid, company, order_id)

        if otp_result["success"]:
            formatted_otp = format_otp_for_speech(otp_result["otp"])
            response_text = f"Here's your {company} OTP: {formatted_otp}"

            if order_id in self.order_wallet:
                self.order_wallet[order_id]["status"] = "completed"

            return response_text, "otp_provided", collected_info, action
        else:
            error_msg = "I'm having trouble getting your OTP. Please try again."
            return error_msg, "otp_error", collected_info, action

    def handle_otp_request_logic(
        self,
        message: str,
        stage: str,
        collected_info: Dict[str, Any],
        response_language: str = "en",
        call_sid: str = None,
        conversation_history: list = None,
    ) -> Dict[str, Any]:
        """Handle OTP requests using the new requires_sms format"""
        intent = detect_user_intent(message)

        print(f"🔐 [OTP LOGIC] Stage: {stage}, Intent: {intent}")
        print(f"🔐 [OTP LOGIC] Collected info: {collected_info}")

        if conversation_history is None:
            conversation_history = []

        if intent == "requesting_otp" or stage == "providing_otp":
            company = collected_info.get("company")

            if not company:
                response_text = "Which company is this OTP request for?"

                return {
                    "response_text": response_text,
                    "requires_sms": False,
                    "call_sid": call_sid,
                    "conversation_stage": "asking_otp_company",
                    "intent": "clarify_company",
                    "updated_history": conversation_history
                    + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": response_text},
                    ],
                    "collected_info": collected_info,
                }

            waiting_message = f"I'll check your recent messages for the {company} OTP. Please give me a moment."

            return {
                "response_text": waiting_message,
                "requires_sms": True,
                "call_sid": call_sid,
                "conversation_stage": "checking_sms",
                "intent": "fetch_otp",
                "company_requested": company,
                "updated_history": conversation_history
                + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": waiting_message},
                ],
                "collected_info": collected_info,
            }

        return self._handle_non_sms_otp_logic(
            message,
            stage,
            collected_info,
            response_language,
            call_sid,
            conversation_history,
        )

    def handle_sms_reprocessing(
        self, original_request: Dict[str, Any], sms_data: list, call_sid: str
    ) -> Dict[str, Any]:
        """Process SMS data and provide final OTP response"""

        original_ai_response = original_request.get("original_ai_response", {})
        company = original_ai_response.get("company_requested", "delivery")
        conversation_history = original_request.get("original_ai_response", {}).get(
            "updated_history", []
        )
        collected_info = original_request.get("collected_info", {})
        response_language = collected_info.get("language", "en")

        print(
            f"🔄 [SMS REPROCESS] Processing {len(sms_data)} SMS messages for {company}"
        )

        from ..utils.sms_parser import SMSParser

        parser = SMSParser()

        processed_otps = []
        for sms in sms_data:
            message_text = sms.get("message", "")
            sender = sms.get("sender", "")

            parsed_sms = parser.parse_sms(message_text, company)

            processed_otps.append(
                {
                    "otp": parsed_sms.otp,
                    "sender": sender,
                    "message": message_text,
                    "company": parsed_sms.company
                    or self._detect_company_from_sender(sender),
                    "tracking_id": parsed_sms.tracking_id,
                    "confidence": parsed_sms.confidence_score,
                    "timestamp": sms.get("timestamp"),
                }
            )

        best_match = self._find_best_otp_match(processed_otps, company)

        if best_match and best_match.get("otp"):
            otp = best_match["otp"]
            formatted_otp = format_otp_for_speech(otp)
            sender = best_match.get("sender", "SMS")
            tracking_id = best_match.get("tracking_id")
            confidence = best_match.get("confidence", 0)

            if confidence >= 0.8:
                response_text = f"I found your {company} OTP! It's {formatted_otp}. Thank you and have a safe delivery!"
            else:
                response_text = f"I found an OTP from {sender}: {formatted_otp}. Please verify this is for {company}. Thank you!"

            if tracking_id:
                response_text += f" Tracking ID: {tracking_id}"

            return {
                "response_text": response_text,
                "requires_sms": False,
                "conversation_stage": "call_ending",
                "intent": "provide_otp",
                "otp_found": otp,
                "company": company,
                "confidence": confidence,
                "end_call": True,
                "updated_history": conversation_history
                + [{"role": "assistant", "content": response_text}],
            }

        else:
            if len(sms_data) == 0:
                response_text = "I don't see any recent SMS messages."
            else:
                response_text = f"I checked {len(sms_data)} messages but couldn't find a {company} OTP. Could you tell me the OTP manually?"

            return {
                "response_text": response_text,
                "requires_sms": False,
                "conversation_stage": "otp_not_found",
                "intent": "request_manual_otp",
                "messages_checked": len(sms_data),
                "updated_history": conversation_history
                + [{"role": "assistant", "content": response_text}],
            }

    def _handle_non_sms_otp_logic(
        self,
        message: str,
        stage: str,
        collected_info: Dict[str, Any],
        response_language: str,
        call_sid: str,
        conversation_history: list,
    ) -> Dict[str, Any]:
        """Handle OTP logic that doesn't require SMS data"""

        if stage == "asking_otp_company":
            from ..utils.text_processing import extract_company_from_text

            company = extract_company_from_text(message) or message.strip().title()
            collected_info["company"] = company

            waiting_message = f"Thank you! Now I'll look for the {company} OTP."

            return {
                "response_text": waiting_message,
                "requires_sms": True,
                "call_sid": call_sid,
                "conversation_stage": "checking_sms",
                "intent": "fetch_otp",
                "company_requested": company,
                "updated_history": conversation_history
                + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": waiting_message},
                ],
                "collected_info": collected_info,
            }

        response_text = "I can help you find an OTP. Which company is it for?"

        return {
            "response_text": response_text,
            "requires_sms": False,
            "call_sid": call_sid,
            "conversation_stage": "asking_otp_company",
            "intent": "clarify_company",
            "updated_history": conversation_history
            + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response_text},
            ],
            "collected_info": collected_info,
        }

    def _find_best_otp_match(self, processed_otps: list, company: str) -> dict:
        """Find the best matching OTP from processed SMS data"""
        if not processed_otps:
            return None

        for otp_item in processed_otps:
            if otp_item.get("confidence", 0) >= 0.8:
                return otp_item

        return processed_otps[0] if processed_otps else None

    def _detect_company_from_sender(self, sender: str) -> str:
        """Detect company from sender ID"""
        if not sender:
            return "unknown"

        sender_lower = sender.lower()

        company_mapping = {
            "zomato": ["zomato", "zmt", "zm-"],
            "swiggy": ["swiggy", "swg", "sg-"],
            "amazon": ["amazon", "amzn", "az-"],
            "flipkart": ["flipkart", "fkrt", "fk-"],
            "bigbasket": ["bigbasket", "bb-", "bigb"],
            "dunzo": ["dunzo", "dz-"],
        }

        for company, patterns in company_mapping.items():
            if any(pattern in sender_lower for pattern in patterns):
                return company

        return "unknown"

    def handle_unknown_logic(
        self,
        message: str,
        stage: str,
        collected_info: Dict[str, Any],
        caller_id=None,
        response_language: str = "en",
    ) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """Handle conversation flow for unknown callers"""
        templates = get_response_templates("en")

        if any(k in message.lower() for k in ["urgent", "asap", "emergency"]):
            name_to_use = collected_info.get("name", "An unknown caller")
            response_text = templates.get(
                "urgent_matter",
                "Okay, I understand this is urgent. I am notifying Vishal immediately.",
            )

            urgent_message = f"Urgent call from {name_to_use}."
            self.notification_service.send_urgent_notification(urgent_message)

            action = {"type": "URGENT_NOTIFICATION", "message": urgent_message}
            return response_text, "end_of_call", collected_info, action

        intent = detect_user_intent(message)
        action = {}

        if stage == "start":
            return templates["collect_name"], "asking_name", collected_info, action

        if stage == "collecting_contact" and intent == "provide_self_number":
            collected_info["phone"] = caller_id or "Caller's Number"
            self.notification_service.send_unknown_caller_notification(collected_info)
            return (
                "Okay, noted. Vishal will call you back on the number you are calling from. Thank you!",
                "end_of_call",
                collected_info,
                action,
            )

        extracted_info = self.extract_information_with_ai(message, collected_info)
        collected_info.update(extracted_info)

        if stage == "asking_name":
            if collected_info.get("name"):
                name = collected_info["name"]
                return (
                    f"Hi {name}! And what is the reason for your call?",
                    "asking_purpose",
                    collected_info,
                    action,
                )
            else:
                if len(message.strip()) > 0:
                    potential_name = message.strip()
                    if (
                        len(potential_name) <= 20
                        and any(c.isalpha() for c in potential_name)
                        and potential_name.lower() not in ["yes", "no", "hello", "hi"]
                    ):
                        collected_info["name"] = potential_name.title()
                        return (
                            f"Hi {potential_name.title()}! And what is the reason for your call?",
                            "asking_purpose",
                            collected_info,
                            action,
                        )

                return (
                    "I'm sorry, I didn't catch your name. Could you please spell it out?",
                    "asking_name",
                    collected_info,
                    action,
                )

        if stage == "asking_purpose":
            if not collected_info.get("purpose"):
                collected_info["purpose"] = message

            if not collected_info.get("followup_asked"):
                ai_followup = self._get_ai_followup_questions(message, collected_info)

                if ai_followup.get("needs_followup"):
                    collected_info["followup_asked"] = True
                    collected_info["ai_followup_plan"] = ai_followup
                    return (
                        ai_followup["first_question"],
                        "asking_followup",
                        collected_info,
                        action,
                    )

            if not collected_info.get("phone"):
                return (
                    "Got it. What's the best number for Vishal to call you back on?",
                    "collecting_contact",
                    collected_info,
                    action,
                )
            else:
                phone_for_speech = format_number_for_speech(collected_info["phone"])
                self.notification_service.send_unknown_caller_notification(
                    collected_info
                )
                return (
                    f"Perfect, I have your number as {phone_for_speech}. I'll make sure Vishal gets all this information and calls you back. Have a great day!",
                    "end_of_call",
                    collected_info,
                    action,
                )

        if stage == "asking_followup":
            if not collected_info.get("additional_details"):
                collected_info["additional_details"] = []
            collected_info["additional_details"].append(message)

            followup_plan = collected_info.get("ai_followup_plan", {})
            followup_count = len(collected_info.get("additional_details", []))

            if followup_count == 1 and followup_plan.get("second_question"):
                return (
                    followup_plan["second_question"],
                    "asking_second_followup",
                    collected_info,
                    action,
                )
            else:
                if not collected_info.get("phone"):
                    return (
                        "Thank you for those details. What's the best number for Vishal to call you back on?",
                        "collecting_contact",
                        collected_info,
                        action,
                    )
                else:
                    phone_for_speech = format_number_for_speech(collected_info["phone"])
                    self.notification_service.send_unknown_caller_notification(
                        collected_info
                    )
                    return (
                        f"Perfect, I have your number as {phone_for_speech}. I'll make sure Vishal gets all this information and calls you back. Have a great day!",
                        "end_of_call",
                        collected_info,
                        action,
                    )

        if stage == "asking_second_followup":
            if not collected_info.get("additional_details"):
                collected_info["additional_details"] = []
            collected_info["additional_details"].append(message)

            if not collected_info.get("phone"):
                return (
                    "Excellent, thank you for all that information. What's the best number for Vishal to call you back on?",
                    "collecting_contact",
                    collected_info,
                    action,
                )
            else:
                phone_for_speech = format_number_for_speech(collected_info["phone"])
                self.notification_service.send_unknown_caller_notification(
                    collected_info
                )
                return (
                    f"Perfect, I have your number as {phone_for_speech}. I'll make sure Vishal gets all this detailed information and calls you back soon. Have a great day!",
                    "end_of_call",
                    collected_info,
                    action,
                )

        if stage == "collecting_contact":
            if collected_info.get("phone"):
                phone_for_speech = format_number_for_speech(collected_info["phone"])
                self.notification_service.send_unknown_caller_notification(
                    collected_info
                )
                return (
                    f"Great, I have your number as {phone_for_speech}. I'll make sure Vishal gets all this information and calls you back. Thank you for calling, and have a wonderful day!",
                    "end_of_call",
                    collected_info,
                    action,
                )
            else:
                return (
                    "I didn't quite catch that. Could you please provide a callback number?",
                    "collecting_contact",
                    collected_info,
                    action,
                )

        if collected_info.get("name") or collected_info.get("purpose"):
            self.notification_service.send_unknown_caller_notification(collected_info)

        return (
            "Thank you for calling. I'll make sure Vishal gets your message. Have a great day!",
            "end_of_call",
            collected_info,
            action,
        )

    def _get_ai_followup_questions(
        self, purpose_message: str, collected_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to determine if follow-up questions are needed and what to ask"""
        caller_name = collected_info.get("name", "the caller")

        if hasattr(self.gemini_service, "client") and self.gemini_service.client:
            try:
                prompt = f"""
You are an AI assistant screening calls for Vishal Gardas. A caller named {caller_name} said their reason for calling is: "{purpose_message}"

Analyze the purpose and respond with JSON in this format:
{{
    "needs_followup": true/false,
    "importance_level": "high/medium/low",
    "first_question": "What specific question should I ask first?",
    "second_question": "What should I ask as a follow-up?" or null,
    "reasoning": "Why these questions are important"
}}
"""
                from google.genai import types

                response = self.gemini_service._generate_content_with_retry(
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                        max_output_tokens=300,
                    ),
                )
                import json

                return json.loads(response.text.strip())
            except Exception as e:
                print(f"⚠️ AI followup generation failed: {e}")

        return self._get_rule_based_followup(purpose_message)

    def _get_rule_based_followup(self, purpose_message: str) -> Dict[str, Any]:
        """Fallback rule-based follow-up question generation"""
        purpose_lower = purpose_message.lower()

        business_keywords = [
            "sponsorship",
            "business",
            "collaboration",
            "partnership",
            "investment",
            "project",
            "proposal",
            "meeting",
            "interview",
            "opportunity",
            "deal",
            "funding",
            "venture",
            "startup",
            "media",
            "press",
            "journalist",
            "article",
            "feature",
        ]

        needs_followup = any(keyword in purpose_lower for keyword in business_keywords)

        if not needs_followup:
            return {
                "needs_followup": False,
                "importance_level": "low",
                "reasoning": "Simple inquiry that doesn't require detailed follow-up",
            }

        if "sponsorship" in purpose_lower:
            return {
                "needs_followup": True,
                "importance_level": "high",
                "first_question": "I see you're interested in sponsorship. What type of sponsorship opportunity are you proposing?",
                "second_question": "And what's the scale or budget range you're considering?",
                "reasoning": "Sponsorship details help evaluate scale",
            }
        elif any(
            word in purpose_lower for word in ["investment", "funding", "venture"]
        ):
            return {
                "needs_followup": True,
                "importance_level": "high",
                "first_question": "I understand this is about investment. What kind of investment opportunity are you proposing?",
                "second_question": "What stage is your company or project currently at?",
                "reasoning": "Investment details help define next steps",
            }
        else:
            return {
                "needs_followup": True,
                "importance_level": "medium",
                "first_question": "That sounds important! Could you provide a bit more detail about what you'd like to discuss?",
                "second_question": "What would be the best time frame for Vishal to get back to you?",
                "reasoning": "Standard professional follow-up",
            }

    def generate_conversation_summary(
        self, conversation_history: list, collected_info: Dict[str, Any] = None
    ) -> str:
        """Generate a conversation summary using the Gemini service"""
        if not conversation_history:
            return "No conversation to summarize"
        return self.gemini_service.generate_conversation_summary(
            conversation_history, collected_info
        )
