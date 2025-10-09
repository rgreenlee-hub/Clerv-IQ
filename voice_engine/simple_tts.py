"""
Simple TTS Engine - Lightweight alternative
Uses gTTS for high-quality online TTS
"""

from gtts import gTTS
import os
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class VoiceGender(Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class Accent(Enum):
    AMERICAN = "en"
    BRITISH = "en-gb"
    AUSTRALIAN = "en-au"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    POLISH = "pl"
    TURKISH = "tr"
    RUSSIAN = "ru"
    DUTCH = "nl"
    CZECH = "cs"
    ARABIC = "ar"
    CHINESE = "zh-cn"
    JAPANESE = "ja"
    KOREAN = "ko"


class Emotion(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CALM = "calm"
    CONFIDENT = "confident"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    ENTHUSIASTIC = "enthusiastic"


@dataclass
class VoiceConfig:
    name: str
    gender: VoiceGender
    accent: Accent
    emotion: Emotion = Emotion.NEUTRAL
    speed: float = 1.0
    pitch_shift: float = 0.0
    energy: float = 1.0
    is_cloned: bool = False
    voice_sample_path: str = None
    embedding: any = None


class TTSEngine:
    """Simple, reliable TTS engine using gTTS"""
    
    def __init__(self):
        print("✓ Simple TTS Engine ready!")
    
    def synthesize(self, text: str, voice_config: VoiceConfig, output_path: str = None):
        """Generate speech from text"""
        if not output_path:
            output_path = "output/speech.mp3"
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Map accent to gTTS TLD
        accent_map = {
            "en": "com",
            "en-gb": "co.uk",
            "en-au": "com.au",
            "es": "es",
            "fr": "fr",
            "de": "de",
            "it": "it",
            "pt": "pt"
        }
        
        tld = accent_map.get(voice_config.accent.value, "com")
        
        # Generate speech
        tts = gTTS(text=text, lang='en', tld=tld, slow=False)
        tts.save(output_path)
        
        return output_path


class PresetVoices:
    """Preset voice configurations"""
    
    @staticmethod
    def professional_male():
        return VoiceConfig(
            name="Professional Male",
            gender=VoiceGender.MALE,
            accent=Accent.AMERICAN,
            emotion=Emotion.PROFESSIONAL
        )
    
    @staticmethod
    def professional_female():
        return VoiceConfig(
            name="Professional Female",
            gender=VoiceGender.FEMALE,
            accent=Accent.AMERICAN,
            emotion=Emotion.PROFESSIONAL
        )
    
    @staticmethod
    def friendly_receptionist():
        return VoiceConfig(
            name="Friendly Receptionist",
            gender=VoiceGender.FEMALE,
            accent=Accent.AMERICAN,
            emotion=Emotion.FRIENDLY
        )
    
    @staticmethod
    def luxury_concierge():
        return VoiceConfig(
            name="Luxury Concierge",
            gender=VoiceGender.MALE,
            accent=Accent.BRITISH,
            emotion=Emotion.CALM
        )
    
    @staticmethod
    def enthusiastic_sales():
        return VoiceConfig(
            name="Enthusiastic Sales",
            gender=VoiceGender.FEMALE,
            accent=Accent.AMERICAN,
            emotion=Emotion.ENTHUSIASTIC
        )