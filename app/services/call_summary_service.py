"""Call Summary Service for generating intelligent summaries from call transcripts"""

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

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config.config import Config

try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    types = None


class CallSummaryService:
    """Service for generating call summaries using Google Gemini's native API"""

    def __init__(self, config: Config):
        self.config = config
        self.client = None

        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-genai package not available for call summary. Real service is required."
            )
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "Gemini API key not configured for call summary. Real Gemini service is required."
            )

        try:
            self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        except Exception as e:
            raise RuntimeError(f"Client initialization failed for call summary: {e}")

    def _generate_content_with_retry(self, contents, config):
        """Execute generate_content with automatic retry/fallback during high demand (503) or rate limits (429)"""
        models_to_try = ["gemini-3.5-flash", "gemini-flash-latest"]
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

    def generate_summary(
        self, call_data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate comprehensive summary for a completed call, supporting both dict input or keyword arguments
        """
        if not self.client:
            raise RuntimeError("Gemini client is not configured.")

        data = call_data or kwargs
        call_sid = data.get("call_sid") or data.get("callSid") or "unknown"
        transcript = data.get("transcript", "")
        duration = data.get("duration", 0)
        call_type = data.get("call_type", "delivery")
        caller_number = data.get("caller_number") or data.get("callerNumber", "")
        user_name = data.get("user_name") or data.get("userName", "")

        print(
            f"📊 [CALL SUMMARY] Generating summary for call {call_sid} (duration: {duration}s)"
        )

        start_time = time.time()

        try:
            summary_text = self._generate_summary_text(transcript, call_type, duration)
            key_points = self._extract_key_points(transcript)

            processing_time = round(time.time() - start_time, 2)

            summary_result = {
                "success": True,
                "call_sid": call_sid,
                "summary": summary_text,
                "key_points": key_points,
                "caller_number": caller_number,
                "user_name": user_name,
                "metadata": {
                    "duration_seconds": duration,
                    "call_type": call_type,
                    "generated_at": datetime.now().isoformat(),
                    "processing_time_seconds": processing_time,
                    "ai_model": "gemini-3.5-flash",
                    "transcript_length": len(transcript),
                },
            }

            print(f"✅ [CALL SUMMARY] Summary generated in {processing_time}s")
            return summary_result

        except Exception as e:
            print(
                f"❌ [CALL SUMMARY ERROR] Failed to generate summary for {call_sid}: {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "summary": "Failed to generate call summary.",
            }

    def _generate_summary_text(
        self, transcript: str, call_type: str, duration: int
    ) -> str:
        """Generate the main summary paragraph using Gemini"""
        system_prompt = f"""You are an expert executive assistant specializing in summarizing phone calls for busy professionals.
        
Analyze the following phone call transcript and generate a concise, professional summary.
        
Call Type: {call_type}
Duration: {self._format_duration(duration)}
        
Focus on:
- Main purpose of the call
- Key actions taken by the AI assistant
- Outcome/resolution status
- Any important details (delivery company, OTP provided, directions given, etc.)

Keep the summary under 150 words and write in a professional, clear style."""

        try:
            response = self._generate_content_with_retry(
                contents=f"Transcript:\n{transcript}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    max_output_tokens=200,
                ),
            )

            return response.text.strip()

        except Exception as e:
            print(f"❌ Gemini summary generation failed: {e}")
            raise RuntimeError(f"Gemini API call failed: {e}")

    def _extract_key_points(self, transcript: str) -> List[str]:
        """Extract key points using Gemini"""
        try:
            response = self._generate_content_with_retry(
                contents=transcript,
                config=types.GenerateContentConfig(
                    system_instruction="Extract 3-5 key points from this call transcript. Return as a simple list, one point per line, no formatting.",
                    temperature=0.2,
                    max_output_tokens=150,
                ),
            )

            key_points = response.text.strip().split("\n")
            return [
                point.strip().lstrip("- ").lstrip("• ")
                for point in key_points
                if point.strip()
            ]

        except Exception as e:
            raise RuntimeError(f"Gemini key points extraction failed: {e}")

    def _identify_call_type(self, transcript: str) -> str:
        """Identify the type of call from transcript"""
        clean_transcript = transcript.lower()

        delivery_keywords = [
            "delivery",
            "deliver",
            "parcel",
            "package",
            "otp",
            "code",
            "amazon",
            "swiggy",
            "zomato",
            "flipkart",
        ]
        if any(keyword in clean_transcript for keyword in delivery_keywords):
            return "delivery"

        inquiry_keywords = ["inquiry", "question", "help", "support", "information"]
        if any(keyword in clean_transcript for keyword in inquiry_keywords):
            return "inquiry"

        return "general"

    def _format_duration(self, duration_seconds: int) -> str:
        """Format duration in human-readable format"""
        if duration_seconds < 60:
            return f"{duration_seconds} seconds"
        elif duration_seconds < 3600:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the call summary service"""
        return {
            "gemini_available": self.client is not None,
            "gemini_configured": (
                bool(self.config.GEMINI_API_KEY)
                if hasattr(self.config, "GEMINI_API_KEY")
                else False
            ),
            "timestamp": time.time(),
        }
