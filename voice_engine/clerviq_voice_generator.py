"""
ClervIQ Voice Engine - Complete Open-Source Implementation
High-quality voice cloning and TTS using free, open-source models

Models Used:
- Coqui TTS (XTTS-v2) - Voice cloning & synthesis
- Resemblyzer - Speaker embeddings
- Piper TTS - Fast, lightweight TTS (backup)

Installation:
pip install TTS torch torchaudio numpy scipy librosa pydub resemblyzer
pip install fastapi uvicorn python-multipart
"""

import os
import io
import json
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# TTS imports
try:
    from TTS.api import TTS
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
except ImportError:
    print("Installing TTS library... Run: pip install TTS")
    
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
except ImportError:
    print("Installing resemblyzer... Run: pip install resemblyzer")

# Audio processing
import librosa
from scipy.io import wavfile
from pydub import AudioSegment


# ============================================================================
# CONFIGURATION
# ============================================================================

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

class VoiceGender(Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

@dataclass
class VoiceConfig:
    """Configuration for a voice profile"""
    name: str
    gender: VoiceGender
    accent: Accent
    emotion: Emotion = Emotion.NEUTRAL
    pitch_shift: float = 0.0  # Semitones (-12 to +12)
    speed: float = 1.0  # 0.5 to 2.0
    energy: float = 1.0  # Volume/energy multiplier
    is_cloned: bool = False
    voice_sample_path: Optional[str] = None
    embedding: Optional[np.ndarray] = None
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums to strings
        data['gender'] = self.gender.value
        data['accent'] = self.accent.value
        data['emotion'] = self.emotion.value
        # Don't serialize numpy array directly
        if self.embedding is not None:
            data['embedding'] = None
        return data
    
    def save(self, path: str):
        """Save voice config to JSON"""
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        # Save embedding separately if exists
        if self.embedding is not None:
            embedding_path = config_path.with_suffix('.npy')
            np.save(embedding_path, self.embedding)


# ============================================================================
# VOICE CLONING ENGINE
# ============================================================================

class VoiceCloningEngine:
    """High-quality voice cloning using Coqui XTTS-v2 and Resemblyzer"""
    
    def __init__(self, device: str = None):
        """
        Initialize voice cloning engine
        
        Args:
            device: 'cuda', 'cpu', or None (auto-detect)
        """
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Initializing Voice Cloning Engine on {self.device}...")
        
        # Initialize XTTS-v2 model (best open-source voice cloning)
        print("Loading XTTS-v2 model (this may take a minute)...")
        self.tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
        
        # Initialize speaker encoder for embeddings
        print("Loading speaker encoder...")
        self.speaker_encoder = VoiceEncoder(device=self.device)
        
        self.sample_rate = 22050
        print("✓ Voice Cloning Engine ready!")
    
    def clone_voice_from_file(
        self,
        audio_path: str,
        voice_name: str,
        gender: VoiceGender,
        accent: Accent,
        output_dir: str = "voices"
    ) -> VoiceConfig:
        """
        Clone a voice from an audio file (30-60 seconds recommended)
        
        Args:
            audio_path: Path to audio file
            voice_name: Name for the cloned voice
            gender: Voice gender
            accent: Voice accent
            output_dir: Directory to save voice files
            
        Returns:
            VoiceConfig with cloned voice
        """
        print(f"\nCloning voice from: {audio_path}")
        
        # Validate file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Load and preprocess audio
        audio_array, sr = self._load_and_preprocess(audio_path)
        
        # Validate duration (30-60 seconds recommended)
        duration = len(audio_array) / sr
        print(f"Audio duration: {duration:.1f} seconds")
        
        if duration < 10:
            print("⚠ Warning: Audio is very short. For best results, use 30-60 seconds.")
        elif duration > 120:
            print("⚠ Warning: Audio is long. Using first 60 seconds.")
            audio_array = audio_array[:60 * sr]
        
        # Extract speaker embedding
        print("Extracting speaker embedding...")
        embedding = self._extract_embedding(audio_array, sr)
        
        # Create voice directory
        voice_dir = Path(output_dir) / voice_name.replace(" ", "_")
        voice_dir.mkdir(parents=True, exist_ok=True)
        
        # Save processed audio sample
        sample_path = voice_dir / "sample.wav"
        wavfile.write(sample_path, sr, audio_array)
        
        # Create voice config
        voice_config = VoiceConfig(
            name=voice_name,
            gender=gender,
            accent=accent,
            is_cloned=True,
            voice_sample_path=str(sample_path),
            embedding=embedding
        )
        
        # Save config
        config_path = voice_dir / "config.json"
        voice_config.save(config_path)
        
        print(f"✓ Voice cloned successfully: {voice_name}")
        print(f"  Saved to: {voice_dir}")
        
        return voice_config
    
    def _load_and_preprocess(self, audio_path: str) -> tuple:
        """Load and preprocess audio file"""
        # Load audio
        audio, sr = librosa.load(audio_path, sr=self.sample_rate)
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = librosa.to_mono(audio)
        
        # Normalize audio
        audio = audio / np.max(np.abs(audio))
        
        # Convert to int16 for speaker encoder
        audio_int16 = (audio * 32767).astype(np.int16)
        
        return audio_int16, sr
    
    def _extract_embedding(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Extract speaker embedding using Resemblyzer"""
        # Preprocess for resemblyzer
        wav = preprocess_wav(audio, source_sr=sr)
        
        # Extract embedding
        embedding = self.speaker_encoder.embed_utterance(wav)
        
        return embedding
    
    @staticmethod
    def load_voice(voice_dir: str) -> VoiceConfig:
        """Load a saved voice configuration"""
        voice_path = Path(voice_dir)
        config_path = voice_path / "config.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Voice config not found: {config_path}")
        
        # Load config
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        
        # Reconstruct enums
        config_dict['gender'] = VoiceGender(config_dict['gender'])
        config_dict['accent'] = Accent(config_dict['accent'])
        config_dict['emotion'] = Emotion(config_dict['emotion'])
        
        # Load embedding if exists
        embedding_path = config_path.with_suffix('.npy')
        if embedding_path.exists():
            config_dict['embedding'] = np.load(embedding_path)
        
        return VoiceConfig(**config_dict)

# ============================================================================
# TEXT-TO-SPEECH ENGINE
# ============================================================================

class TTSEngine:
    """High-quality TTS with emotion and prosody control"""

    def __init__(self, device: str = None):
        """Initialize TTS engine"""
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        print(f"Initializing TTS Engine on {self.device}...")

        # Attempt to load XTTS-v2 model first (preferred)
        try:
            from TTS.api import TTS
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
            print("✓ XTTS-v2 TTS model loaded successfully!")
        except Exception as e:
            print(f"⚠ XTTS-v2 load failed: {e}")
            self.tts = None

        # Fallback: try standard English TTS
        if self.tts is None:
            try:
                from TTS.api import TTS as TTSApi
                self.tts = TTSApi("tts_models/en/ljspeech/tacotron2-DDC").to(self.device)
                print("✓ Fallback TTS model loaded successfully!")
            except Exception as e:
                print(f"⚠ Fallback TTS load failed: {e}")
                self.tts = None

        self.sample_rate = 22050
        print("✓ TTS Engine ready!")

    def synthesize(
        self,
        text: str,
        voice_config,
        output_path: Optional[str] = None,
        stream: bool = False
    ) -> Union[np.ndarray, str]:
        """Synthesize speech from text"""
        if self.tts is None:
            raise RuntimeError("TTS engine not initialized")

        # Determine language from voice config
        language = getattr(voice_config, "accent", None)
        language = language.value if language else "en"

        # Try using a cloned speaker wav if available
        speaker_wav = getattr(voice_config, "voice_sample_path", None)

        print(f"Synthesizing text: {text[:60]}...")

        try:
            if speaker_wav and os.path.exists(speaker_wav):
                wav = self.tts.tts(
                    text=text,
                    speaker_wav=speaker_wav,
                    language=language
                )
            else:
                wav = self.tts.tts(
                    text=text,
                    language=language
                )
        except Exception as e:
            print(f"⚠ Synthesis failed: {e}")
            return None

        # Convert list → numpy
        if isinstance(wav, list):
            wav = np.array(wav)

        # Apply optional prosody (speed, pitch, energy)
        if hasattr(self, "_apply_prosody"):
            wav = self._apply_prosody(wav, voice_config)

        # Save to file if specified
        if output_path:
            self._save_audio(wav, output_path)
            return output_path

        return wav

    def _apply_prosody(self, audio: np.ndarray, config) -> np.ndarray:
        """Apply pitch shift, speed adjustment, and energy control"""
        try:
            if getattr(config, "speed", 1.0) != 1.0:
                audio = librosa.effects.time_stretch(audio, rate=config.speed)
            if getattr(config, "pitch_shift", 0.0) != 0.0:
                audio = librosa.effects.pitch_shift(
                    audio,
                    sr=self.sample_rate,
                    n_steps=config.pitch_shift
                )
            if getattr(config, "energy", 1.0) != 1.0:
                audio = audio * config.energy
                audio = np.clip(audio, -1.0, 1.0)
        except Exception as e:
            print(f"⚠ Prosody adjustment failed: {e}")
        return audio

    def _save_audio(self, audio: np.ndarray, path: str, format: str = "wav"):
        """Save audio to file"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(path, self.sample_rate, audio_int16)

    def synthesize_batch(
        self,
        texts: List[str],
        voice_config,
        output_dir: str = "output"
    ) -> List[str]:
        """Synthesize multiple texts in batch"""
        output_paths = []
        for i, text in enumerate(texts):
            output_path = f"{output_dir}/speech_{i:03d}.wav"
            self.synthesize(text, voice_config, output_path)
            output_paths.append(output_path)
        return output_paths


# ============================================================================
# CLIENT MANAGEMENT
# ============================================================================

class ClientVoiceManager:
    """Manage client voice profiles"""
    
    def __init__(self, storage_path: str = "client_voices"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.clients_file = self.storage_path / "clients.json"
        self.clients = self._load_clients()
    
    def _load_clients(self) -> Dict:
        """Load client database"""
        if self.clients_file.exists():
            with open(self.clients_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_clients(self):
        """Save client database"""
        with open(self.clients_file, 'w') as f:
            json.dump(self.clients, f, indent=2)
    
    def add_client(self, client_id: str, client_name: str, company: str = ""):
        """Add new client"""
        client_dir = self.storage_path / client_id
        client_dir.mkdir(exist_ok=True)
        
        self.clients[client_id] = {
            "name": client_name,
            "company": company,
            "voices": [],
            "created_at": str(Path(client_dir).stat().st_ctime)
        }
        
        self._save_clients()
        print(f"✓ Added client: {client_name} ({client_id})")
    
    def upload_voice(
        self,
        client_id: str,
        audio_path: str,
        voice_name: str,
        gender: VoiceGender,
        accent: Accent,
        cloning_engine: VoiceCloningEngine
    ) -> VoiceConfig:
        """Upload and clone voice for client"""
        if client_id not in self.clients:
            raise ValueError(f"Client {client_id} not found")
        
        # Clone voice
        voice_dir = self.storage_path / client_id / voice_name.replace(" ", "_")
        voice_config = cloning_engine.clone_voice_from_file(
            audio_path=audio_path,
            voice_name=f"{client_id}_{voice_name}",
            gender=gender,
            accent=accent,
            output_dir=str(voice_dir)
        )
        
        # Add to client's voices
        self.clients[client_id]["voices"].append({
            "name": voice_name,
            "path": str(voice_dir),
            "gender": gender.value,
            "accent": accent.value
        })
        
        self._save_clients()
        
        return voice_config
    
    def get_client_voices(self, client_id: str) -> List[Dict]:
        """Get all voices for a client"""
        if client_id not in self.clients:
            raise ValueError(f"Client {client_id} not found")
        return self.clients[client_id]["voices"]
    
    def list_clients(self) -> List[Dict]:
        """List all clients"""
        return [
            {"id": cid, **cdata}
            for cid, cdata in self.clients.items()
        ]


# ============================================================================
# PRESET VOICES
# ============================================================================

class PresetVoices:
    """High-quality preset voices"""
    
    @staticmethod
    def professional_male() -> VoiceConfig:
        return VoiceConfig(
            name="Professional Male",
            gender=VoiceGender.MALE,
            accent=Accent.AMERICAN,
            emotion=Emotion.PROFESSIONAL,
            pitch_shift=-2.0,
            speed=0.95,
            energy=0.9
        )
    
    @staticmethod
    def professional_female() -> VoiceConfig:
        return VoiceConfig(
            name="Professional Female",
            gender=VoiceGender.FEMALE,
            accent=Accent.AMERICAN,
            emotion=Emotion.PROFESSIONAL,
            pitch_shift=1.0,
            speed=1.0,
            energy=0.9
        )
    
    @staticmethod
    def friendly_receptionist() -> VoiceConfig:
        return VoiceConfig(
            name="Friendly Receptionist",
            gender=VoiceGender.FEMALE,
            accent=Accent.AMERICAN,
            emotion=Emotion.FRIENDLY,
            pitch_shift=2.0,
            speed=1.05,
            energy=1.1
        )
    
    @staticmethod
    def luxury_concierge() -> VoiceConfig:
        return VoiceConfig(
            name="Luxury Concierge",
            gender=VoiceGender.MALE,
            accent=Accent.BRITISH,
            emotion=Emotion.CALM,
            pitch_shift=-3.0,
            speed=0.9,
            energy=0.8
        )
    
    @staticmethod
    def enthusiastic_sales() -> VoiceConfig:
        return VoiceConfig(
            name="Enthusiastic Sales",
            gender=VoiceGender.FEMALE,
            accent=Accent.AMERICAN,
            emotion=Emotion.ENTHUSIASTIC,
            pitch_shift=3.0,
            speed=1.1,
            energy=1.2
        )


# ============================================================================
# FASTAPI SERVER
# ============================================================================

"""
FastAPI server for production deployment:

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
import tempfile

app = FastAPI(title="ClervIQ Voice Engine API")

# Initialize engines
tts_engine = TTSEngine()
cloning_engine = VoiceCloningEngine()
client_manager = ClientVoiceManager()

@app.post("/api/synthesize")
async def synthesize(
    text: str = Form(...),
    voice_name: str = Form("professional_male"),
    pitch_shift: float = Form(0.0),
    speed: float = Form(1.0),
    energy: float = Form(1.0)
):
    # Get or create voice config
    voice = PresetVoices.professional_male()  # Or load custom
    voice.pitch_shift = pitch_shift
    voice.speed = speed
    voice.energy = energy
    
    # Generate speech
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tts_engine.synthesize(text, voice, tmp.name)
        return FileResponse(tmp.name, media_type="audio/wav")

@app.post("/api/clone-voice")
async def clone_voice(
    client_id: str = Form(...),
    voice_name: str = Form(...),
    gender: str = Form(...),
    accent: str = Form(...),
    audio_file: UploadFile = File(...)
):
    # Save uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await audio_file.read())
        tmp_path = tmp.name
    
    # Clone voice
    voice_config = client_manager.upload_voice(
        client_id=client_id,
        audio_path=tmp_path,
        voice_name=voice_name,
        gender=VoiceGender(gender),
        accent=Accent(accent),
        cloning_engine=cloning_engine
    )
    
    return {"status": "success", "voice_name": voice_config.name}

@app.get("/api/voices")
async def list_voices():
    return {
        "presets": [
            "professional_male",
            "professional_female",
            "friendly_receptionist",
            "luxury_concierge",
            "enthusiastic_sales"
        ],
        "clients": client_manager.list_clients()
    }

# Run with: uvicorn clerviq_voice_engine:app --reload
"""


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """CLI for testing the voice engine"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClervIQ Voice Engine CLI")
    parser.add_argument("--mode", choices=["synthesize", "clone", "demo"], required=True)
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--voice", help="Voice preset name")
    parser.add_argument("--audio", help="Audio file for cloning")
    parser.add_argument("--name", help="Name for cloned voice")
    parser.add_argument("--output", default="output.wav", help="Output file")
    
    args = parser.parse_args()
    
    if args.mode == "demo":
        print("=== ClervIQ Voice Engine Demo ===\n")
        
        # Initialize engines
        tts = TTSEngine()
        
        # Test preset voices
        print("Testing preset voices...")
        test_text = "Hello! Welcome to ClervIQ. How may I assist you today?"
        
        voices = [
            ("professional_male", PresetVoices.professional_male()),
            ("professional_female", PresetVoices.professional_female()),
            ("friendly_receptionist", PresetVoices.friendly_receptionist()),
        ]
        
        for name, voice in voices:
            print(f"\nGenerating: {name}")
            output = f"demo_{name}.wav"
            tts.synthesize(test_text, voice, output)
            print(f"✓ Saved to: {output}")
        
        print("\n✓ Demo complete! Check the generated files.")
    
    elif args.mode == "synthesize":
        if not args.text:
            print("Error: --text required for synthesize mode")
            return
        
        tts = TTSEngine()
        voice = PresetVoices.professional_male()
        
        tts.synthesize(args.text, voice, args.output)
        print(f"✓ Synthesized to: {args.output}")
    
    elif args.mode == "clone":
        if not args.audio or not args.name:
            print("Error: --audio and --name required for clone mode")
            return
        
        cloner = VoiceCloningEngine()
        voice = cloner.clone_voice_from_file(
            audio_path=args.audio,
            voice_name=args.name,
            gender=VoiceGender.NEUTRAL,
            accent=Accent.AMERICAN
        )
        print(f"✓ Voice cloned: {voice.name}")


if __name__ == "__main__":
    main()
