"""
test_speech_pipeline.py - Verification script for self-hosted SLP pipeline in VoiceDrop-2.0.
"""

import sys
import os
import unittest
import numpy as np
import base64

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.audio_utils import (
    mulaw_to_float32,
    float32_to_mulaw,
    resample_audio,
    prepare_audio_for_whisper,
    encode_tts_for_twilio,
    calculate_rms_energy
)
from app.services.speech_service import stt_engine, tts_engine
from main import create_app


class TestSpeechPipeline(unittest.TestCase):
    
    def test_01_mulaw_codec_roundtrip(self):
        """Verify ITU-T G.711 mu-law encoder and decoder fidelity."""
        print("\n🧪 [TEST 1] Testing G.711 mu-law Codec Round-Trip...")
        # Create 1-second 440Hz sine wave at 8kHz
        t = np.linspace(0, 1.0, 8000, endpoint=False)
        original_signal = (0.7 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        
        # Encode to mu-law bytes
        mulaw_bytes = float32_to_mulaw(original_signal)
        self.assertEqual(len(mulaw_bytes), 8000)
        
        # Decode back to float32
        reconstructed = mulaw_to_float32(mulaw_bytes)
        self.assertEqual(len(reconstructed), 8000)
        
        # Compute Pearson correlation (should be > 0.999 for G.711)
        correlation = np.corrcoef(original_signal, reconstructed)[0, 1]
        print(f"  G.711 Signal Reconstruction Correlation: {correlation:.5f}")
        self.assertGreater(correlation, 0.99)
        print("  ✅ G.711 mu-law codec round-trip passed.")

    def test_02_resampling(self):
        """Verify polyphase/linear audio resampler from 8kHz to 16kHz."""
        print("\n🧪 [TEST 2] Testing Audio Resampler (8kHz <-> 16kHz)...")
        audio_8k = np.zeros(8000, dtype=np.float32)
        audio_16k = resample_audio(audio_8k, orig_sr=8000, target_sr=16000)
        self.assertEqual(len(audio_16k), 16000)
        print("  ✅ Resampling length verified.")

    def test_03_tts_synthesis(self):
        """Verify local neural TTS engine generates valid 8kHz mu-law audio."""
        print("\n🧪 [TEST 3] Testing Neural TTS Synthesis...")
        test_text = "Your OTP for Flipkart delivery is 4 8 2 0."
        result = tts_engine.synthesize_to_mulaw(test_text, language="en")
        
        self.assertIn("audio", result)
        self.assertEqual(result["format"], "mulaw")
        self.assertEqual(result["sample_rate"], 8000)
        self.assertGreater(len(result["audio"]), 1000)
        print(f"  Synthesized {len(result['audio'])} base64 chars in {result['duration_ms']}ms.")
        print("  ✅ TTS synthesis passed.")

    def test_04_stt_transcription(self):
        """Verify Whisper STT transcribes generated telephony audio."""
        print("\n🧪 [TEST 4] Testing Whisper STT on Telephony Audio...")
        test_text = "Please leave the parcel with security guard."
        tts_result = tts_engine.synthesize_to_mulaw(test_text, language="en")
        
        stt_result = stt_engine.transcribe(tts_result["audio"], language="en")
        transcript = stt_result.get("transcript", "").lower()
        print(f"  Expected: \"{test_text.lower()}\"")
        print(f"  Got:      \"{transcript}\" (Confidence: {stt_result.get('confidence')})")
        self.assertTrue(len(transcript) > 0)
        print("  ✅ Whisper STT transcription passed.")

    def test_05_flask_routes(self):
        """Verify Flask API endpoints /api/speech/info, /api/speech/tts, /api/speech/stt."""
        print("\n🧪 [TEST 5] Testing Flask Speech Blueprint Endpoints...")
        app = create_app()
        client = app.test_client()
        
        # Test /api/speech/info
        res_info = client.get("/api/speech/info")
        self.assertEqual(res_info.status_code, 200)
        info_data = res_info.get_json()
        self.assertEqual(info_data["status"], "active")
        print("  /api/speech/info OK")
        
        # Test /api/speech/tts
        res_tts = client.post("/api/speech/tts", json={"text": "Hello delivery agent", "language": "en"})
        self.assertEqual(res_tts.status_code, 200)
        tts_data = res_tts.get_json()
        self.assertTrue(tts_data["success"])
        self.assertIn("audio", tts_data)
        print("  /api/speech/tts OK")
        
        # Test /api/speech/stt
        res_stt = client.post("/api/speech/stt", json={"audio": tts_data["audio"], "language": "en"})
        self.assertEqual(res_stt.status_code, 200)
        stt_data = res_stt.get_json()
        self.assertTrue(stt_data["success"])
        self.assertIn("transcript", stt_data)
        print(f"  /api/speech/stt OK -> Transcript: \"{stt_data['transcript']}\"")
        print("  ✅ All Flask speech routes verified.")


if __name__ == "__main__":
    unittest.main()
