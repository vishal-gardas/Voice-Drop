"""
speech_service.py - Self-hosted Speech Recognition (STT) and Synthesis (TTS) Engine.

Replaces commercial APIs (Deepgram) with:
1. Local/Fine-tuned OpenAI Whisper via faster-whisper (CTranslate2 INT8/FP16)
2. Neural & Offline Telephony TTS (edge-tts / pyttsx3 / Piper) with direct 8kHz mu-law encoding.
"""

import asyncio
import io
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

from app.utils.audio_utils import (encode_tts_for_twilio, prepare_audio_for_whisper)

logger = logging.getLogger("VoiceDrop.SpeechService")

# ==============================================================================
# Speech-To-Text (Whisper STT Engine)
# ==============================================================================


class WhisperSTTEngine:
    """
    High-performance Speech-To-Text engine using Whisper / faster-whisper.
    Supports CPU INT8 quantization and CUDA FP16 acceleration.
    """

    def __init__(
        self,
        model_size_or_path: str = "tiny.en",
        device: str = "auto",
        compute_type: str = "auto",
    ):
        self.model_name = os.getenv("WHISPER_MODEL", model_size_or_path)
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._is_loaded = False

        # Domain-specific prompt biasing for delivery dialogues and OTPs
        self.delivery_initial_prompt = (
            "VoiceDrop delivery assistant conversation. "
            "Keywords: Flipkart, Amazon, Swiggy, Zomato, OTP, package, parcel, security guard, "
            "tower, flat, gate, door, call, deliver, arrived."
        )

    def _load_model(self):
        """Lazy load Whisper model on first request."""
        if self._is_loaded and self.model is not None:
            return

        logger.info(f"🎙️ [STT] Loading Whisper model: {self.model_name}...")
        start_time = time.time()

        try:
            from faster_whisper import WhisperModel

            # Select device and compute type
            selected_device = "cpu" if self.device == "auto" else self.device
            selected_compute = (
                "int8" if self.compute_type == "auto" else self.compute_type
            )

            self.model = WhisperModel(
                self.model_name,
                device=selected_device,
                compute_type=selected_compute,
                download_root=os.path.join(
                    os.path.expanduser("~"), ".cache", "whisper_models"
                ),
            )
            self._is_loaded = True
            load_duration = round((time.time() - start_time) * 1000, 1)
            logger.info(
                f"✅ [STT] Whisper ({self.model_name}) loaded in {load_duration}ms on {selected_device} ({selected_compute})"
            )
        except Exception as e:
            logger.error(f"❌ [STT] Failed to load faster-whisper model: {e}")
            self.model = None
            self._is_loaded = False

    def transcribe(
        self,
        audio_payload: Union[bytes, str, np.ndarray],
        language: Optional[str] = "en",
        beam_size: int = 2,
        initial_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe incoming audio (base64 8kHz mu-law, raw bytes, or float32 PCM array).

        Returns:
            Dict containing:
                - transcript (str): Transcribed text
                - language (str): Detected or specified language
                - confidence (float): Average log-probability converted to 0..1 scale
                - duration_ms (float): Inference duration in ms
                - word_count (int): Number of words transcribed
        """
        self._load_model()

        if self.model is None:
            return {
                "transcript": "",
                "language": language or "en",
                "confidence": 0.0,
                "duration_ms": 0.0,
                "error": "Whisper model failed to load",
            }

        start_time = time.time()

        # 1. Convert input audio to 16kHz float32 numpy array
        if isinstance(audio_payload, np.ndarray):
            audio_data = audio_payload
        else:
            audio_data = prepare_audio_for_whisper(
                audio_payload, input_sample_rate=8000
            )

        # Check audio length & energy
        if len(audio_data) < 1600:  # Less than 0.1 seconds of audio
            return {
                "transcript": "",
                "language": language or "en",
                "confidence": 0.0,
                "duration_ms": round((time.time() - start_time) * 1000, 1),
                "word_count": 0,
            }

        prompt = initial_prompt or self.delivery_initial_prompt

        # 2. Run Whisper Transcription
        try:
            segments, info = self.model.transcribe(
                audio_data,
                language=language if language and language != "auto" else None,
                beam_size=beam_size,
                initial_prompt=prompt,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400),
            )

            transcript_parts = []
            avg_logprobs = []

            for segment in segments:
                text = segment.text.strip()
                if text:
                    transcript_parts.append(text)
                    avg_logprobs.append(segment.avg_logprob)

            full_transcript = " ".join(transcript_parts).strip()

            # Convert logprob to confidence score (0.0 - 1.0)
            confidence = 0.85
            if avg_logprobs:
                mean_logprob = float(np.mean(avg_logprobs))
                # logprob is usually in range [-2.0, 0.0]
                confidence = float(np.clip(np.exp(mean_logprob), 0.1, 1.0))

            elapsed_ms = round((time.time() - start_time) * 1000, 1)

            logger.info(
                f'🎙️ [STT] Result: "{full_transcript}" | Conf: {confidence:.2f} | Time: {elapsed_ms}ms'
            )

            return {
                "transcript": full_transcript,
                "language": getattr(info, "language", language or "en"),
                "confidence": round(confidence, 3),
                "duration_ms": elapsed_ms,
                "word_count": len(full_transcript.split()) if full_transcript else 0,
            }
        except Exception as e:
            logger.error(f"❌ [STT] Transcription error: {e}", exc_info=True)
            return {
                "transcript": "",
                "language": language or "en",
                "confidence": 0.0,
                "duration_ms": round((time.time() - start_time) * 1000, 1),
                "error": str(e),
            }


# ==============================================================================
# Text-To-Speech (Neural & Local TTS Engine)
# ==============================================================================


class NeuralTTSEngine:
    """
    High-fidelity Neural Text-To-Speech Engine.
    Primary: edge-tts (Microsoft Natural Neural Voices: English-IN, English-US, Hindi)
    Fallback: pyttsx3 (System SAPI5 offline engine)
    Output: 8kHz ITU-T G.711 mu-law Base64 audio matching Twilio stream format.
    """

    VOICE_MAP = {
        "en": "en-IN-NeerjaNeural",  # Indian English Female (natural for Indian deliveries)
        "en-IN": "en-IN-NeerjaNeural",
        "en-US": "en-US-JennyNeural",  # US English Female
        "hi": "hi-IN-SwaraNeural",  # Hindi Female
        "hi-IN": "hi-IN-SwaraNeural",
        "default": "en-IN-NeerjaNeural",
    }

    def __init__(self):
        self.default_rate = "+5%"
        self.default_pitch = "+0Hz"

    async def _synthesize_edge_tts(self, text: str, voice: str) -> Optional[np.ndarray]:
        """Synthesize using edge-tts async API and return float32 audio array sampled at 24kHz."""
        try:
            import edge_tts
            import soundfile as sf

            communicate = edge_tts.Communicate(
                text=text, voice=voice, rate=self.default_rate, pitch=self.default_pitch
            )

            audio_stream = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])

            audio_stream.seek(0)
            data, sample_rate = sf.read(audio_stream, dtype="float32")

            # If stereo, convert to mono
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            return data, sample_rate
        except Exception as e:
            logger.warning(
                f"⚠️ [TTS] edge-tts synthesis failed, falling back to pyttsx3: {e}"
            )
            return None

    def _synthesize_pyttsx3(self, text: str) -> Optional[Tuple[np.ndarray, int]]:
        """Fallback synthesis using offline pyttsx3."""
        try:
            import tempfile

            import pyttsx3
            import soundfile as sf

            engine = pyttsx3.init()
            engine.setProperty("rate", 160)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                temp_path = tmp_file.name

            engine.save_to_file(text, temp_path)
            engine.runAndWait()

            data, sample_rate = sf.read(temp_path, dtype="float32")

            if os.path.exists(temp_path):
                os.remove(temp_path)

            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            return data, sample_rate
        except Exception as e:
            logger.error(f"❌ [TTS] pyttsx3 fallback also failed: {e}")
            return None

    def synthesize_to_mulaw(
        self, text: str, language: str = "en", voice_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize text to 8kHz ITU-T G.711 mu-law Base64 string for Twilio streaming.

        Returns:
            Dict containing:
                - audio (str): Base64-encoded 8kHz mu-law audio
                - format (str): 'mulaw'
                - sample_rate (int): 8000
                - duration_ms (float): synthesis duration in ms
        """
        if not text or not text.strip():
            return {
                "audio": "",
                "format": "mulaw",
                "sample_rate": 8000,
                "duration_ms": 0,
            }

        start_time = time.time()
        clean_text = text.strip()

        # Select voice
        voice = voice_override or self.VOICE_MAP.get(
            language, self.VOICE_MAP["default"]
        )

        # Run async edge-tts in event loop
        pcm_result = None
        try:
            loop = asyncio.new_event_loop()
            pcm_result = loop.run_until_complete(
                self._synthesize_edge_tts(clean_text, voice)
            )
            loop.close()
        except Exception as e:
            logger.warning(f"⚠️ [TTS] Async loop error in edge-tts: {e}")

        # Fallback if edge-tts failed
        if pcm_result is None:
            pcm_result = self._synthesize_pyttsx3(clean_text)

        if pcm_result is None:
            logger.error("❌ [TTS] All TTS synthesizers failed.")
            return {
                "audio": "",
                "format": "mulaw",
                "sample_rate": 8000,
                "error": "TTS synthesis failed",
            }

        pcm_data, sample_rate = pcm_result

        # Transcode 24kHz/16kHz PCM -> 8kHz G.711 mu-law Base64
        mulaw_base64 = encode_tts_for_twilio(pcm_data, source_sample_rate=sample_rate)

        elapsed_ms = round((time.time() - start_time) * 1000, 1)
        logger.info(
            f'🔊 [TTS] Generated {len(mulaw_base64)} chars 8kHz mu-law audio for "{clean_text[:40]}..." in {elapsed_ms}ms'
        )

        return {
            "audio": mulaw_base64,
            "format": "mulaw",
            "sample_rate": 8000,
            "duration_ms": elapsed_ms,
        }


# ==============================================================================
# Singleton Instances
# ==============================================================================

stt_engine = WhisperSTTEngine()
tts_engine = NeuralTTSEngine()
