"""Gemini service implementation using Google GenAI SDK"""

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

import json
from typing import Any, Dict

try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    types = None


class GeminiService:
    """Gemini service configured to run on Google Gemini's native API"""

    def __init__(self, config):
        self.config = config
        self.api_key = config.GEMINI_API_KEY
        self.client = None
        self.call_count = 0

        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-genai package is not installed. Real Gemini service is required."
            )
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured in environment variables. Real Gemini service is required."
            )

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            raise RuntimeError(f"Client initialization failed for Gemini API: {e}")

    def _generate_content_with_retry(self, contents, config):
        """Execute generate_content with automatic retry/fallback during high demand (503) or rate limits (429)"""
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        last_error = None
        for model_name in models_to_try:
            try:
                return self.client.models.generate_content(
                    model=model_name, contents=contents, config=config
                )
            except Exception as e:
                last_error = e
                err_str = str(e)
                if any(
                    code in err_str
                    for code in [
                        "503",
                        "429",
                        "UNAVAILABLE",
                        "RESOURCE_EXHAUSTED",
                        "NOT_FOUND",
                    ]
                ):
                    print(
                        f"⚠️ [GEMINI RETRY] Model {model_name} encountered error ({err_str[:80]}), trying fallback model..."
                    )
                    continue
                raise e
        raise RuntimeError(
            f"All Gemini models failed due to rate limits or availability: {last_error}"
        )

    def extract_information_with_ai(
        self, message: str, collected_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI-powered extraction with intelligent company name correction for misheard audio"""
        if not self.client:
            raise RuntimeError("Gemini client is not configured.")

        print("--- [INFO EXTRACTION] Attempting to extract info ---")
        print(f"--- [INFO EXTRACTION] Message: '{message}' ---")

        try:
            system_prompt = """You are an expert at understanding phone conversations with delivery personnel, even when audio transcription is imperfect.

CONTEXT: Audio transcription systems often mishear company names. Your job is to intelligently identify and CORRECT these errors.

Common mishearings you should recognize and fix:
- "speaky", "sweegy", "sweeji" → Swiggy
- "zoomato", "zometto" → Zomato  
- "amazen", "amazone", "amzon" → Amazon
- "flipcart", "flipcard" → Flipkart
- "stick see", "dtic" → DTDC
- "uber eat" → Uber Eats
- And ANY OTHER similar phonetic errors for delivery/courier companies

Extract these fields:
- "name": ONLY the person's actual name (extract from "My name is X", "I am X", "This is X")
- "purpose": Reason for calling (if mentioned)
- "phone": Phone number (if mentioned)  
- "company": The CORRECTED company name (use your intelligence to fix mishearings)

CRITICAL RULES:
1. For names: Extract ONLY the actual name, NOT the phrase "my name is" or "I am"
2. Use your knowledge of common Indian/global delivery companies to correct misspellings
3. Return ONLY valid JSON

Examples:
- "My name is Vishal" → {"name": "Vishal"}
- "I am John calling" → {"name": "John"}
- "This is Priya" → {"name": "Priya"}
- "I have delivery from speaky" → {"company": "Swiggy"}
- "delivery from amazen" → {"company": "Amazon"}
- "My name is John from zoomato" → {"name": "John", "company": "Zomato"}
"""

            user_prompt = f'Current information: {json.dumps(collected_info)}\nUser\'s message: "{message}"'

            response = self._generate_content_with_retry(
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=150,
                ),
            )

            extracted = json.loads(response.text.strip())
            print(f"✅ [INFO EXTRACTION] Extracted: {extracted}")

            # Clean and format extracted name (in case AI didn't follow instructions perfectly)
            if extracted.get("name"):
                import re

                name = extracted["name"]
                # Remove common prefixes if they somehow got included
                name = re.sub(
                    r"^(my name is|i am|this is|i\'m)\s+", "", name, flags=re.IGNORECASE
                ).strip()
                # Capitalize properly
                extracted["name"] = name.title()

            # Format phone number if found
            if extracted.get("phone"):
                from ..utils.text_processing import format_phone_number

                formatted = format_phone_number(extracted["phone"])
                if formatted:
                    extracted["phone"] = formatted
                else:
                    del extracted["phone"]

            # Format company name
            if extracted.get("company"):
                extracted["company"] = extracted["company"].strip().title()

            self.call_count += 1
            return extracted

        except Exception as e:
            print(
                f"⚠️ [INFO EXTRACTION FALLBACK] Gemini API failed or rate limited ({e}), using rule-based extraction."
            )
            extracted = {}
            import re

            # Simple rule-based extraction
            name_match = re.search(
                r"\b(?:my name is|i am|this is|i\'m)\s+([a-zA-Z\u0900-\u097F]+)\b",
                message,
                re.IGNORECASE,
            )
            if name_match:
                extracted["name"] = name_match.group(1).title()

            companies = {
                "swiggy": ["swiggy", "speaky", "sweegy", "sweeji"],
                "zomato": ["zomato", "zoomato", "zometto"],
                "amazon": ["amazon", "amazen", "amazone", "amzon"],
                "flipkart": ["flipkart", "flipcart", "flipcard"],
                "dtdc": ["dtdc", "stick see"],
                "blue dart": ["blue dart", "bluedart"],
                "delhivery": ["delhivery", "delivery"],
            }
            msg_lower = message.lower()
            for comp, aliases in companies.items():
                if any(alias in msg_lower for alias in aliases):
                    extracted["company"] = comp.title()
                    break

            return extracted

    def generate_conversation_summary(
        self, conversation_history: list, collected_info: Dict[str, Any] = None
    ) -> str:
        """Generate a 50-70 word summary of the conversation"""
        if not self.client:
            raise RuntimeError("Gemini client is not configured.")
        if not conversation_history:
            raise ValueError("Conversation history is empty.")

        try:
            # Extract only the conversation parts
            conversation_text = ""
            for message in conversation_history:
                role = message.get("role", "")
                parts = message.get("parts", [])

                if role == "user":
                    conversation_text += f"Caller: {' '.join(parts)}\n"
                elif role == "model":
                    conversation_text += f"AI: {' '.join(parts)}\n"

            # Add context from collected info
            context_info = ""
            if collected_info:
                company = collected_info.get("company", "")
                stage = collected_info.get("stage", "")
                if company:
                    context_info += f"Company: {company}. "
                if stage:
                    context_info += f"Final stage: {stage}. "

            system_prompt = """You are an expert at summarizing phone conversations. Create a concise 50-70 word summary of this conversation between an AI assistant and a caller.

Focus on:
- Who called (delivery person, unknown caller, etc.)
- What they needed (directions, OTP, general inquiry)
- What assistance was provided
- How the call concluded

Keep it professional and factual. Don't include unnecessary details."""

            user_prompt = f"""Context: {context_info}

Conversation:
{conversation_text}

Please provide a 50-70 word summary of this conversation."""

            response = self._generate_content_with_retry(
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    max_output_tokens=150,
                ),
            )

            summary = response.text.strip()

            # Ensure it's within word count
            words = summary.split()
            if len(words) > 70:
                summary = " ".join(words[:70]) + "..."
            elif len(words) < 50:
                summary += f" Call completed successfully."

            self.call_count += 1
            return summary

        except Exception as e:
            print(f"❌ [SUMMARY ERROR] {e}")
            raise RuntimeError(
                f"Failed to generate conversation summary using Gemini API: {e}"
            )
