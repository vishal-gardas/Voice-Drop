"""
audio_utils.py - High-performance audio transcoding utilities for VoiceDrop-2.0.

Provides:
- ITU-T G.711 mu-law decoding (8kHz 8-bit mu-law -> 16kHz float32 linear PCM for Whisper STT)
- ITU-T G.711 mu-law encoding (16kHz/24kHz float32/int16 PCM -> 8kHz 8-bit mu-law for Twilio telephony)
- Resampling routines (8kHz <-> 16kHz <-> 24kHz)
- Energy-based Voice Activity Detection (VAD) and audio normalization
"""

import base64
from typing import Union

import numpy as np

# ==============================================================================
# ITU-T G.711 mu-law Precomputed Tables for O(1) Vectorized Conversion
# ==============================================================================


def _build_mulaw_to_linear_table() -> np.ndarray:
    """Build precomputed 256-entry lookup table: 8-bit mu-law -> 16-bit signed PCM."""
    table = np.zeros(256, dtype=np.int16)
    for i in range(256):
        u = ~i & 0xFF
        sign = 1 if (u & 0x80) != 0 else -1
        exponent = (u >> 4) & 0x07
        mantissa = u & 0x0F
        sample = sign * (((mantissa << 3) + 0x84) << exponent) - sign * 0x84
        table[i] = np.clip(sample, -32768, 32767)
    return table


def _build_linear_to_mulaw_table() -> np.ndarray:
    """Build precomputed 65536-entry lookup table: 16-bit signed PCM -> 8-bit mu-law."""
    table = np.zeros(65536, dtype=np.uint8)
    BIAS = 0x84
    CLIP = 32635

    for val in range(65536):
        sample = val - 32768
        sign = 0x80 if sample >= 0 else 0
        mag = abs(sample)
        if mag > CLIP:
            mag = CLIP
        mag += BIAS

        exponent = 7
        exp_mask = 0x4000
        while (mag & exp_mask) == 0 and exponent > 0:
            exponent -= 1
            exp_mask >>= 1

        mantissa = (mag >> (exponent + 3)) & 0x0F
        table[val] = (~(sign | (exponent << 4) | mantissa)) & 0xFF
    return table


MULAW_TO_LINEAR_TABLE = _build_mulaw_to_linear_table()
LINEAR_TO_MULAW_TABLE = _build_linear_to_mulaw_table()


def mulaw_to_pcm16(mulaw_bytes: bytes) -> np.ndarray:
    """Convert raw 8-bit mu-law byte string to 16-bit linear PCM int16 numpy array."""
    if not mulaw_bytes:
        return np.array([], dtype=np.int16)
    indices = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    return MULAW_TO_LINEAR_TABLE[indices]


def pcm16_to_mulaw(pcm16_samples: np.ndarray) -> bytes:
    """Convert 16-bit linear PCM int16 numpy array to raw 8-bit mu-law byte string."""
    if len(pcm16_samples) == 0:
        return b""
    clamped = np.clip(pcm16_samples, -32768, 32767).astype(np.int32)
    indices = (clamped + 32768).astype(np.uint16)
    mulaw_array = LINEAR_TO_MULAW_TABLE[indices]
    return mulaw_array.tobytes()


def mulaw_to_float32(mulaw_bytes: bytes) -> np.ndarray:
    """Convert 8-bit mu-law byte buffer directly to normalized float32 PCM in range [-1.0, 1.0]."""
    pcm16 = mulaw_to_pcm16(mulaw_bytes)
    return (pcm16.astype(np.float32) / 32768.0).astype(np.float32)


def float32_to_mulaw(float_samples: np.ndarray) -> bytes:
    """Convert normalized float32 PCM in range [-1.0, 1.0] to 8-bit mu-law bytes."""
    pcm16 = (np.clip(float_samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    return pcm16_to_mulaw(pcm16)


# ==============================================================================
# Audio Resampling
# ==============================================================================


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample 1D audio array between arbitrary sample rates.
    Uses scipy.signal.resample if available, else linear interpolation.
    """
    if orig_sr == target_sr or len(audio) == 0:
        return audio

    num_target_samples = int(round(len(audio) * float(target_sr) / float(orig_sr)))
    if num_target_samples == 0:
        return np.array([], dtype=audio.dtype)

    try:
        from scipy import signal

        resampled = signal.resample(audio, num_target_samples)
        return resampled.astype(audio.dtype)
    except Exception:
        orig_indices = np.linspace(0, len(audio) - 1, len(audio))
        target_indices = np.linspace(0, len(audio) - 1, num_target_samples)
        return np.interp(target_indices, orig_indices, audio).astype(audio.dtype)


def prepare_audio_for_whisper(
    mulaw_payload: Union[bytes, str], input_sample_rate: int = 8000
) -> np.ndarray:
    """
    Decode incoming Twilio 8kHz mu-law audio (raw bytes or base64 string),
    convert to float32 linear PCM, and resample to 16,000 Hz for Whisper.

    Returns:
        np.ndarray: float32 1D array sampled at 16kHz in range [-1.0, 1.0].
    """
    if isinstance(mulaw_payload, str):
        raw_bytes = base64.b64decode(mulaw_payload)
    else:
        raw_bytes = mulaw_payload

    if not raw_bytes:
        return np.array([], dtype=np.float32)

    float_audio_8k = mulaw_to_float32(raw_bytes)

    # Resample 8kHz -> 16kHz
    float_audio_16k = resample_audio(
        float_audio_8k, orig_sr=input_sample_rate, target_sr=16000
    )
    return float_audio_16k


def encode_tts_for_twilio(
    pcm_audio: np.ndarray, source_sample_rate: int = 24000
) -> str:
    """
    Take generated TTS audio array (float32 [-1, 1] or int16), resample to 8kHz,
    convert to ITU-T G.711 mu-law, and return base64-encoded string for Twilio stream.
    """
    if len(pcm_audio) == 0:
        return ""

    if pcm_audio.dtype == np.float32 or pcm_audio.dtype == np.float64:
        float_pcm = pcm_audio.astype(np.float32)
    elif pcm_audio.dtype == np.int16:
        float_pcm = pcm_audio.astype(np.float32) / 32768.0
    else:
        float_pcm = pcm_audio.astype(np.float32)

    # Resample source_sr -> 8000 Hz
    audio_8k = resample_audio(float_pcm, orig_sr=source_sample_rate, target_sr=8000)

    # Encode to mu-law bytes
    mulaw_bytes = float32_to_mulaw(audio_8k)

    # Return as base64 string
    return base64.b64encode(mulaw_bytes).decode("ascii")


# ==============================================================================
# Voice Activity Detection (VAD) & Energy Metrics
# ==============================================================================


def calculate_rms_energy(audio: np.ndarray) -> float:
    """Calculate Root Mean Square (RMS) energy of audio signal."""
    if len(audio) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


def is_speech_active(audio: np.ndarray, energy_threshold: float = 0.012) -> bool:
    """Determine if speech energy exceeds background noise threshold."""
    return calculate_rms_energy(audio) > energy_threshold
