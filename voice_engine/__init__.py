"""
Voice Engine package for ClervIQ.

This module handles all text-to-speech (TTS) and voice cloning functionality.
It integrates with the AI receptionist and provides voice generation,
cloning, and playback support for calls, SMS, and emails.

Files in this package:
- clerviq_voice_generator.py : Core voice generation logic (advanced, requires heavy dependencies)
- simple_tts.py              : Simple TTS using gTTS (lightweight, always works)
- api_server.py              : Flask API for handling speech requests (if exists)
- voice_integration_js.js    : Front-end integration script for real-time playback (if exists)
"""

# Try to import advanced voice engine first, fall back to simple TTS
try:
    from .clerviq_voice_generator import (
        TTSEngine,
        VoiceCloningEngine,
        PresetVoices,
        VoiceConfig,
        Accent,
        Emotion,
        VoiceGender,
        ClientVoiceManager
    )
    print("✓ Using advanced voice cloning engine")
    VOICE_ENGINE_TYPE = "advanced"
except ImportError as e:
    print(f"Advanced voice engine not available ({e}), using simple TTS")
    from .simple_tts import (
        TTSEngine,
        PresetVoices,
        VoiceConfig,
        Accent,
        Emotion,
        VoiceGender
    )
    # Set dummy values for advanced features
    VoiceCloningEngine = None
    ClientVoiceManager = None
    VOICE_ENGINE_TYPE = "simple"

__all__ = [
    'TTSEngine',
    'VoiceCloningEngine', 
    'PresetVoices',
    'VoiceConfig',
    'Accent',
    'Emotion',
    'VoiceGender',
    'ClientVoiceManager',
    'VOICE_ENGINE_TYPE'
]