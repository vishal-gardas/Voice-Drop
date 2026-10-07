"""
speech.py - Flask blueprint for self-hosted Speech and Language Processing (STT & TTS) routes.
"""

import logging

from flask import Blueprint, jsonify, request

from app.services.speech_service import stt_engine, tts_engine

logger = logging.getLogger("VoiceDrop.SpeechRoutes")
speech_bp = Blueprint("speech_bp", __name__, url_prefix="/api/speech")


@speech_bp.route("/stt", methods=["POST"])
def speech_to_text():
    """
    Transcribe incoming audio buffer.
    Accepts JSON with:
      - audio: Base64-encoded 8kHz mu-law audio (from Twilio) or WAV
      - language: Target language (default 'en', or 'auto' for detection)
      - initial_prompt: Optional context biasing prompt
    """
    try:
        data = request.get_json(silent=True)

        if not data or "audio" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing 'audio' field in JSON request body",
                    }
                ),
                400,
            )

        audio_payload = data.get("audio")
        language = data.get("language", "en")
        initial_prompt = data.get("initial_prompt")

        result = stt_engine.transcribe(
            audio_payload=audio_payload,
            language=language,
            initial_prompt=initial_prompt,
        )

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(
            f"❌ [API/STT] Internal error during speech recognition: {e}", exc_info=True
        )
        return jsonify({"success": False, "error": str(e), "transcript": ""}), 500


@speech_bp.route("/tts", methods=["POST"])
def text_to_speech():
    """
    Synthesize text into 8kHz ITU-T G.711 mu-law audio Base64 payload.
    Accepts JSON with:
      - text: String to speak
      - language: Target language ('en', 'hi', 'en-IN', 'en-US')
      - voice: Optional explicit voice model name
    """
    try:
        data = request.get_json(silent=True)

        if not data or "text" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing 'text' field in JSON request body",
                    }
                ),
                400,
            )

        text = data.get("text", "")
        language = data.get("language", "en")
        voice = data.get("voice")

        result = tts_engine.synthesize_to_mulaw(
            text=text, language=language, voice_override=voice
        )

        if not result.get("audio"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Failed to generate audio"),
                    }
                ),
                500,
            )

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(
            f"❌ [API/TTS] Internal error during speech synthesis: {e}", exc_info=True
        )
        return jsonify({"success": False, "error": str(e), "audio": ""}), 500


@speech_bp.route("/info", methods=["GET"])
def get_speech_info():
    """
    Return SLP model specs, device configuration, and pipeline telemetry.
    Useful for academic presentations and debugging.
    """
    return (
        jsonify(
            {
                "status": "active",
                "stt": {
                    "engine": "faster-whisper (CTranslate2)",
                    "model": stt_engine.model_name,
                    "quantization": "int8 / fp16",
                    "acoustic_features": "80-channel Log-Mel Filterbanks",
                    "input_audio_spec": "8kHz G.711 mu-law -> 16kHz Float32 Linear PCM",
                    "device": stt_engine.device,
                    "vocabulary_type": "Byte-Pair Encoding (BPE)",
                },
                "tts": {
                    "engine": "Neural TTS (edge-tts / pyttsx3 fallback)",
                    "output_audio_spec": "8kHz ITU-T G.711 mu-law Base64 (Twilio telephony native)",
                    "supported_voices": list(tts_engine.VOICE_MAP.keys()),
                },
            }
        ),
        200,
    )
