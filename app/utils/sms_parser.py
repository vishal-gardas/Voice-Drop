"""
SMS Message Parsing Utilities
Extracts OTP codes and tracking IDs from delivery company SMS messages
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ParsedSMSData:
    """Structure for parsed SMS data"""

    otp: Optional[str] = None
    tracking_id: Optional[str] = None
    company: Optional[str] = None
    order_id: Optional[str] = None
    delivery_info: Optional[str] = None
    confidence_score: float = 0.0
    raw_message: str = ""


class SMSParser:
    """Parses SMS messages to extract delivery information"""

    def __init__(self):
        self.company_patterns = self._init_company_patterns()
        self.generic_patterns = self._init_generic_patterns()

    def _init_company_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize company-specific SMS patterns"""
        return {
            "zomato": [
                {
                    "otp_pattern": r"(?:OTP|code|password).*?(\d{4,6})",
                    "tracking_pattern": r"(?:order|tracking).*?([A-Z0-9]{8,})",
                    "company_indicators": ["zomato", "zmt"],
                    "confidence_boost": 0.3,
                }
            ],
            "swiggy": [
                {
                    "otp_pattern": r"(?:OTP|code|verification).*?(\d{4,6})",
                    "tracking_pattern": r"(?:order|track).*?([A-Z0-9]{8,})",
                    "company_indicators": ["swiggy", "swg"],
                    "confidence_boost": 0.3,
                }
            ],
            "amazon": [
                {
                    "otp_pattern": r"(?:OTP|code|pin).*?(\d{4,6})",
                    "tracking_pattern": r"(?:tracking|order).*?([A-Z0-9]{10,})",
                    "company_indicators": ["amazon", "amzn"],
                    "confidence_boost": 0.3,
                }
            ],
            "flipkart": [
                {
                    "otp_pattern": r"(?:OTP|code|verification).*?(\d{4,6})",
                    "tracking_pattern": r"(?:order|tracking).*?([A-Z0-9]{8,})",
                    "company_indicators": ["flipkart", "fkrt"],
                    "confidence_boost": 0.3,
                }
            ],
            "bigbasket": [
                {
                    "otp_pattern": r"(?:OTP|code).*?(\d{4,6})",
                    "tracking_pattern": r"(?:order|delivery).*?([A-Z0-9]{8,})",
                    "company_indicators": ["bigbasket", "bb"],
                    "confidence_boost": 0.3,
                }
            ],
            "dunzo": [
                {
                    "otp_pattern": r"(?:OTP|code).*?(\d{4,6})",
                    "tracking_pattern": r"(?:task|order).*?([A-Z0-9]{8,})",
                    "company_indicators": ["dunzo"],
                    "confidence_boost": 0.3,
                }
            ],
        }

    def _init_generic_patterns(self) -> List[Dict]:
        """Initialize generic SMS parsing patterns"""
        return [
            {"otp_pattern": r"\b(\d{4})\b", "confidence": 0.6},  # 4-digit numbers
            {"otp_pattern": r"\b(\d{6})\b", "confidence": 0.7},  # 6-digit numbers
            {
                "otp_pattern": r"(?:OTP|code|verification|pin).*?(\d{4,6})",
                "confidence": 0.8,
            },
            {
                "tracking_pattern": r"\b([A-Z]{2,4}\d{8,12})\b",  # Tracking format
                "confidence": 0.7,
            },
            {
                "tracking_pattern": r"\b([A-Z0-9]{8,15})\b",  # General alphanumeric
                "confidence": 0.5,
            },
        ]

    def parse_sms(self, message: str, expected_company: str = None) -> ParsedSMSData:
        """
        Parse SMS message to extract OTP and tracking information

        Args:
            message: Raw SMS message text
            expected_company: Expected delivery company (optional)

        Returns:
            ParsedSMSData: Extracted information with confidence score
        """
        result = ParsedSMSData(raw_message=message)
        message_lower = message.lower()

        # Try company-specific patterns first
        if expected_company:
            company_data = self._parse_with_company_pattern(
                message, expected_company.lower()
            )
            if company_data:
                return company_data

        # Auto-detect company and parse
        detected_company = self._detect_company(message_lower)
        if detected_company:
            company_data = self._parse_with_company_pattern(message, detected_company)
            if company_data:
                return company_data

        # Fallback to generic patterns
        return self._parse_with_generic_patterns(message)

    def _detect_company(self, message_lower: str) -> Optional[str]:
        """Detect delivery company from message content"""
        for company, patterns in self.company_patterns.items():
            for pattern_set in patterns:
                indicators = pattern_set.get("company_indicators", [])
                for indicator in indicators:
                    if indicator in message_lower:
                        return company
        return None

    def _parse_with_company_pattern(
        self, message: str, company: str
    ) -> Optional[ParsedSMSData]:
        """Parse message using company-specific patterns"""
        if company not in self.company_patterns:
            return None

        patterns = self.company_patterns[company]
        message_lower = message.lower()

        for pattern_set in patterns:
            result = ParsedSMSData(raw_message=message, company=company)
            confidence = 0.5

            # Check company indicators
            indicators = pattern_set.get("company_indicators", [])
            if any(indicator in message_lower for indicator in indicators):
                confidence += pattern_set.get("confidence_boost", 0)

            # Extract OTP
            if "otp_pattern" in pattern_set:
                otp_match = re.search(
                    pattern_set["otp_pattern"], message, re.IGNORECASE
                )
                if otp_match:
                    result.otp = otp_match.group(1)
                    confidence += 0.2

            # Extract tracking ID
            if "tracking_pattern" in pattern_set:
                tracking_match = re.search(
                    pattern_set["tracking_pattern"], message, re.IGNORECASE
                )
                if tracking_match:
                    result.tracking_id = tracking_match.group(1)
                    confidence += 0.2

            result.confidence_score = min(confidence, 1.0)

            if result.otp or result.tracking_id:
                return result

        return None

    def _parse_with_generic_patterns(self, message: str) -> ParsedSMSData:
        """Parse message using generic patterns"""
        result = ParsedSMSData(raw_message=message)
        best_otp_confidence = 0
        best_tracking_confidence = 0

        for pattern_set in self.generic_patterns:
            # Extract OTP
            if "otp_pattern" in pattern_set:
                otp_matches = re.findall(
                    pattern_set["otp_pattern"], message, re.IGNORECASE
                )
                if otp_matches:
                    confidence = pattern_set.get("confidence", 0.5)
                    if confidence > best_otp_confidence:
                        result.otp = otp_matches[0]
                        best_otp_confidence = confidence

            # Extract tracking ID
            if "tracking_pattern" in pattern_set:
                tracking_matches = re.findall(
                    pattern_set["tracking_pattern"], message, re.IGNORECASE
                )
                if tracking_matches:
                    confidence = pattern_set.get("confidence", 0.5)
                    if confidence > best_tracking_confidence:
                        result.tracking_id = tracking_matches[0]
                        best_tracking_confidence = confidence

        result.confidence_score = max(best_otp_confidence, best_tracking_confidence)
        return result

    def extract_delivery_details(self, message: str) -> Dict[str, str]:
        """Extract additional delivery details from SMS"""
        details = {}

        # Extract phone numbers
        phone_matches = re.findall(r"\b(\d{10}|\+91\d{10})\b", message)
        if phone_matches:
            details["delivery_phone"] = phone_matches[0]

        # Extract delivery person name
        name_patterns = [
            r"(?:delivery boy|delivery partner|driver).*?([A-Z][a-z]+)",
            r"([A-Z][a-z]+).*?(?:is|will be|has been).*?deliver",
        ]

        for pattern in name_patterns:
            name_match = re.search(pattern, message, re.IGNORECASE)
            if name_match:
                details["delivery_person"] = name_match.group(1)
                break

        # Extract estimated time
        time_patterns = [
            r"(?:in|within|by).*?(\d+\s*(?:min|hour|hr)s?)",
            r"(\d+:\d+\s*(?:AM|PM))",
        ]

        for pattern in time_patterns:
            time_match = re.search(pattern, message, re.IGNORECASE)
            if time_match:
                details["estimated_time"] = time_match.group(1)
                break

        return details

    def analyze_bulk_otps(
        self, otp_messages: List[Dict], target_company: str = None
    ) -> Dict[str, Any]:
        """
        Analyze bulk OTP messages and provide intelligent insights
        """
        if not otp_messages:
            return {
                "total_messages": 0,
                "valid_otps": 0,
                "companies": [],
                "recommendation": "No messages to analyze",
            }

        analysis = {
            "total_messages": len(otp_messages),
            "valid_otps": 0,
            "companies": {},
            "recent_activity": [],
            "confidence_scores": [],
            "recommendation": "",
            "best_match": None,
        }

        for msg in otp_messages:
            otp = msg.get("otp")
            company = msg.get("company", "unknown")
            confidence = msg.get("confidence", 0)
            sender = msg.get("sender", "")

            if otp:
                analysis["valid_otps"] += 1

                # Track companies
                if company not in analysis["companies"]:
                    analysis["companies"][company] = 0
                analysis["companies"][company] += 1

                # Track confidence scores
                analysis["confidence_scores"].append(confidence)

                # Track recent activity
                analysis["recent_activity"].append(
                    {
                        "company": company,
                        "sender": sender,
                        "otp_length": len(otp),
                        "confidence": confidence,
                    }
                )

        # Generate recommendation
        if target_company:
            target_lower = target_company.lower()
            target_matches = [
                msg
                for msg in otp_messages
                if msg.get("company", "").lower() == target_lower
                or target_lower in msg.get("sender", "").lower()
            ]

            if target_matches:
                best = max(target_matches, key=lambda x: x.get("confidence", 0))
                analysis["best_match"] = best
                analysis["recommendation"] = (
                    f"Found {len(target_matches)} messages for {target_company}"
                )
            else:
                analysis["recommendation"] = (
                    f"No exact match for {target_company}, showing alternatives"
                )
        else:
            # Find best overall match
            if otp_messages:
                best = max(otp_messages, key=lambda x: x.get("confidence", 0))
                analysis["best_match"] = best
                analysis["recommendation"] = "Showing most confident OTP match"

        # Calculate average confidence
        if analysis["confidence_scores"]:
            analysis["avg_confidence"] = sum(analysis["confidence_scores"]) / len(
                analysis["confidence_scores"]
            )
        else:
            analysis["avg_confidence"] = 0

        return analysis

    def suggest_otp_alternatives(
        self, otp_messages: List[Dict], failed_company: str
    ) -> List[Dict]:
        """
        Suggest alternative OTP options when primary company search fails
        """
        suggestions = []

        if not otp_messages:
            return suggestions

        # Sort by confidence and recency
        sorted_messages = sorted(
            otp_messages,
            key=lambda x: (x.get("confidence", 0), -otp_messages.index(x)),
            reverse=True,
        )

        for i, msg in enumerate(sorted_messages[:3]):  # Top 3 suggestions
            if not msg.get("otp"):
                continue

            reason = []

            # Confidence reasoning
            confidence = msg.get("confidence", 0)
            if confidence > 0.8:
                reason.append("high confidence")
            elif confidence > 0.6:
                reason.append("good confidence")

            # Recency reasoning
            if i == 0:
                reason.append("most recent")

            # Company/sender reasoning
            company = msg.get("company", "")
            sender = msg.get("sender", "")

            if company and company != "unknown":
                reason.append(f"from {company}")
            elif sender:
                reason.append(f"sender: {sender}")

            suggestions.append(
                {
                    "otp": msg["otp"],
                    "company": company or "unknown",
                    "sender": sender,
                    "confidence": confidence,
                    "reasoning": ", ".join(reason) if reason else "available option",
                }
            )

        return suggestions
