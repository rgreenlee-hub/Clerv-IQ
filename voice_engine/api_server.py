"""
ClervIQ Voice API Server
Production-ready REST API for voice cloning and synthesis

Run with:
    uvicorn api_server:app --reload --host 0.0.0.0 --port 8000

API Docs available at:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
from pathlib import Path
from typing import Optional, List
import uvicorn

# Import from your voice engine
try:
    from clerviq_voice_engine import (
        TTSEngine,
        VoiceCloningEngine,
        ClientVoiceManager,
        PresetVoices,
        VoiceConfig,
        VoiceGender,
        Accent,
        Emotion
    )
except ImportError:
    print("ERROR: Cannot import clerviq_voice_engine.py")
    print("Make sure the file is named: clerviq_voice_engine.py")
    print("(Rename 'clerviq voice generator.py' to 'clerviq_voice_engine.py')")
    exit(1)

# ============================================================================
# INITIALIZE APP
# ============================================================================

app = FastAPI(
    title="ClervIQ Voice Engine API",
    description="High-quality voice cloning and text-to-speech API",
    version="1.0.0"
)

# Enable CORS for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# GLOBAL ENGINE INSTANCES
# ============================================================================

print("Starting ClervIQ Voice API Server...")
print("Initializing engines (this may take a minute)...")

tts_engine = None
cloning_engine = None
client_manager = None

@app.on_event("startup")
async def startup_event():
    """Initialize engines on startup"""
    global tts_engine, cloning_engine, client_manager
    
    print("Loading TTS Engine...")
    tts_engine = TTSEngine()
    
    print("Loading Voice Cloning Engine...")
    cloning_engine = VoiceCloningEngine()
    
    print("Loading Client Manager...")
    client_manager = ClientVoiceManager()
    
    print("✓ All engines ready!")

# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "ClervIQ Voice Engine API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "synthesize": "POST /api/synthesize",
            "clone_voice": "POST /api/clone-voice",
            "list_voices": "GET /api/voices",
            "list_clients": "GET /api/clients"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "tts_engine": tts_engine is not None,
        "cloning_engine": cloning_engine is not None,
        "client_manager": client_manager is not None
    }

# ============================================================================
# VOICE SYNTHESIS ENDPOINTS
# ============================================================================

@app.post("/api/synthesize")
async def synthesize_speech(
    text: str = Form(..., description="Text to synthesize"),
    voice_preset: str = Form("professional_male", description="Preset voice name"),
    client_id: Optional[str] = Form(None, description="Client ID for custom voice"),
    voice_name: Optional[str] = Form(None, description="Custom voice name"),
    pitch_shift: float = Form(0.0, description="Pitch shift in semitones (-12 to +12)"),
    speed: float = Form(1.0, description="Speech speed (0.5 to 2.0)"),
    energy: float = Form(1.0, description="Energy/volume (0.5 to 1.5)"),
    emotion: str = Form("neutral", description="Emotion type"),
    output_format: str = Form("wav", description="Output format (wav/mp3)")
):
    """
    Synthesize speech from text
    
    Use either:
    - voice_preset for built-in voices
    - client_id + voice_name for custom cloned voices
    """
    try:
        # Get voice config
        if client_id and voice_name:
            # Load custom client voice
            voices = client_manager.get_client_voices(client_id)
            voice_data = next((v for v in voices if v["name"] == voice_name), None)
            if not voice_data:
                raise HTTPException(404, f"Voice '{voice_name}' not found for client '{client_id}'")
            
            voice_config = VoiceCloningEngine.load_voice(voice_data["path"])
        else:
            # Use preset voice
            preset_map = {
                "professional_male": PresetVoices.professional_male,
                "professional_female": PresetVoices.professional_female,
                "friendly_receptionist": PresetVoices.friendly_receptionist,
                "luxury_concierge": PresetVoices.luxury_concierge,
                "enthusiastic_sales": PresetVoices.enthusiastic_sales
            }
            
            if voice_preset not in preset_map:
                raise HTTPException(400, f"Unknown preset: {voice_preset}")
            
            voice_config = preset_map[voice_preset]()
        
        # Apply adjustments
        voice_config.pitch_shift = pitch_shift
        voice_config.speed = speed
        voice_config.energy = energy
        try:
            voice_config.emotion = Emotion(emotion)
        except ValueError:
            raise HTTPException(400, f"Invalid emotion: {emotion}")
        
        # Generate speech
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}") as tmp:
            tmp_path = tmp.name
        
        tts_engine.synthesize(text, voice_config, tmp_path)
        
        # Return audio file
        media_type = "audio/wav" if output_format == "wav" else "audio/mpeg"
        return FileResponse(
            tmp_path,
            media_type=media_type,
            filename=f"speech.{output_format}"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Synthesis failed: {str(e)}")

@app.post("/api/synthesize-batch")
async def synthesize_batch(
    texts: List[str] = Form(..., description="List of texts to synthesize"),
    voice_preset: str = Form("professional_male"),
    pitch_shift: float = Form(0.0),
    speed: float = Form(1.0),
    energy: float = Form(1.0)
):
    """Synthesize multiple texts in batch"""
    try:
        preset_map = {
            "professional_male": PresetVoices.professional_male,
            "professional_female": PresetVoices.professional_female,
            "friendly_receptionist": PresetVoices.friendly_receptionist,
            "luxury_concierge": PresetVoices.luxury_concierge,
            "enthusiastic_sales": PresetVoices.enthusiastic_sales
        }
        
        voice_config = preset_map[voice_preset]()
        voice_config.pitch_shift = pitch_shift
        voice_config.speed = speed
        voice_config.energy = energy
        
        # Create temp directory for batch
        temp_dir = tempfile.mkdtemp()
        output_paths = tts_engine.synthesize_batch(texts, voice_config, temp_dir)
        
        return JSONResponse({
            "status": "success",
            "count": len(output_paths),
            "files": output_paths
        })
        
    except Exception as e:
        raise HTTPException(500, f"Batch synthesis failed: {str(e)}")

# ============================================================================
# VOICE CLONING ENDPOINTS
# ============================================================================

@app.post("/api/clone-voice")
async def clone_voice(
    client_id: str = Form(..., description="Client ID"),
    voice_name: str = Form(..., description="Name for the cloned voice"),
    gender: str = Form(..., description="Voice gender (male/female/neutral)"),
    accent: str = Form(..., description="Voice accent (en/en-gb/es/etc)"),
    audio_file: UploadFile = File(..., description="Audio sample (30-60 seconds, WAV/MP3)")
):
    """
    Clone a voice from an audio sample
    
    Audio requirements:
    - Duration: 30-60 seconds recommended
    - Format: WAV or MP3
    - Quality: Clear speech, minimal background noise
    - Content: Natural speech (not singing or whispering)
    """
    try:
        # Validate inputs
        try:
            gender_enum = VoiceGender(gender.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid gender: {gender}. Use: male, female, or neutral")
        
        try:
            accent_enum = Accent(accent.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid accent: {accent}")
        
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio_file.filename).suffix) as tmp:
            shutil.copyfileobj(audio_file.file, tmp)
            tmp_path = tmp.name
        
        # Clone voice
        voice_config = client_manager.upload_voice(
            client_id=client_id,
            audio_path=tmp_path,
            voice_name=voice_name,
            gender=gender_enum,
            accent=accent_enum,
            cloning_engine=cloning_engine
        )
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return JSONResponse({
            "status": "success",
            "message": f"Voice '{voice_name}' cloned successfully",
            "voice": {
                "name": voice_config.name,
                "gender": voice_config.gender.value,
                "accent": voice_config.accent.value,
                "is_cloned": voice_config.is_cloned
            }
        })
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Voice cloning failed: {str(e)}")

# ============================================================================
# CLIENT MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/clients")
async def create_client(
    client_id: str = Form(..., description="Unique client ID"),
    client_name: str = Form(..., description="Client name"),
    company: str = Form("", description="Company name (optional)")
):
    """Create a new client"""
    try:
        client_manager.add_client(client_id, client_name, company)
        return JSONResponse({
            "status": "success",
            "message": f"Client '{client_name}' created",
            "client_id": client_id
        })
    except Exception as e:
        raise HTTPException(500, f"Failed to create client: {str(e)}")

@app.get("/api/clients")
async def list_clients():
    """List all clients"""
    try:
        clients = client_manager.list_clients()
        return JSONResponse({
            "status": "success",
            "count": len(clients),
            "clients": clients
        })
    except Exception as e:
        raise HTTPException(500, f"Failed to list clients: {str(e)}")

@app.get("/api/clients/{client_id}/voices")
async def get_client_voices(client_id: str):
    """Get all voices for a specific client"""
    try:
        voices = client_manager.get_client_voices(client_id)
        return JSONResponse({
            "status": "success",
            "client_id": client_id,
            "count": len(voices),
            "voices": voices
        })
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to get voices: {str(e)}")

# ============================================================================
# VOICE CATALOG ENDPOINTS
# ============================================================================

@app.get("/api/voices")
async def list_all_voices():
    """List all available voices (presets and custom)"""
    try:
        preset_voices = [
            {
                "id": "professional_male",
                "name": "Professional Male",
                "gender": "male",
                "accent": "American",
                "type": "preset"
            },
            {
                "id": "professional_female",
                "name": "Professional Female",
                "gender": "female",
                "accent": "American",
                "type": "preset"
            },
            {
                "id": "friendly_receptionist",
                "name": "Friendly Receptionist",
                "gender": "female",
                "accent": "American",
                "type": "preset"
            },
            {
                "id": "luxury_concierge",
                "name": "Luxury Concierge",
                "gender": "male",
                "accent": "British",
                "type": "preset"
            },
            {
                "id": "enthusiastic_sales",
                "name": "Enthusiastic Sales",
                "gender": "female",
                "accent": "American",
                "type": "preset"
            }
        ]
        
        # Get all custom voices from clients
        custom_voices = []
        for client in client_manager.list_clients():
            client_id = client["id"]
            voices = client_manager.get_client_voices(client_id)
            for voice in voices:
                custom_voices.append({
                    "client_id": client_id,
                    "client_name": client["name"],
                    "voice_name": voice["name"],
                    "gender": voice["gender"],
                    "accent": voice["accent"],
                    "type": "custom"
                })
        
        return JSONResponse({
            "status": "success",
            "presets": preset_voices,
            "custom": custom_voices,
            "total": len(preset_voices) + len(custom_voices)
        })
        
    except Exception as e:
        raise HTTPException(500, f"Failed to list voices: {str(e)}")

@app.get("/api/voices/presets")
async def list_preset_voices():
    """List only preset voices"""
    return JSONResponse({
        "status": "success",
        "presets": [
            "professional_male",
            "professional_female",
            "friendly_receptionist",
            "luxury_concierge",
            "enthusiastic_sales"
        ]
    })

@app.get("/api/accents")
async def list_accents():
    """List all supported accents"""
    accents = [accent.value for accent in Accent]
    return JSONResponse({
        "status": "success",
        "accents": accents
    })

@app.get("/api/emotions")
async def list_emotions():
    """List all supported emotions"""
    emotions = [emotion.value for emotion in Emotion]
    return JSONResponse({
        "status": "success",
        "emotions": emotions
    })

# ============================================================================
# INTEGRATION ENDPOINTS (for elite_ai_receptionist.py)
# ============================================================================

@app.post("/api/receptionist/speak")
async def receptionist_speak(
    text: str = Form(...),
    voice_id: str = Form("friendly_receptionist"),
    client_id: Optional[str] = Form(None)
):
    """
    Dedicated endpoint for AI receptionist integration
    Optimized for real-time conversation
    """
    try:
        # Use client voice if provided, otherwise use preset
        if client_id:
            voices = client_manager.get_client_voices(client_id)
            if voices:
                voice_data = voices[0]  # Use first voice
                voice_config = VoiceCloningEngine.load_voice(voice_data["path"])
            else:
                voice_config = PresetVoices.friendly_receptionist()
        else:
            preset_map = {
                "friendly_receptionist": PresetVoices.friendly_receptionist,
                "professional_male": PresetVoices.professional_male,
                "professional_female": PresetVoices.professional_female,
            }
            voice_config = preset_map.get(voice_id, PresetVoices.friendly_receptionist)()
        
        # Generate speech
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
        
        tts_engine.synthesize(text, voice_config, tmp_path)
        
        return FileResponse(tmp_path, media_type="audio/wav")
        
    except Exception as e:
        raise HTTPException(500, f"Receptionist speak failed: {str(e)}")

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("ClervIQ Voice Engine API Server")
    print("="*60)
    print("\nStarting server...")
    print("API Docs: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
