"""
receptionist_bridge.py
----------------------
Central integration hub for ClervIQ's Elite AI Receptionist.

Connects:
- AI Brain (conversation analysis + intent detection)
- Receptionist (data logging + analytics)
- Voice Engine (speech generation + voice options)
"""

from flask import Blueprint, request, jsonify
from receptionist.elite_ai_receptionist import EliteAIReceptionist
from receptionist.brain import ReceptionistBrain
from voice_engine import TTSEngine, PresetVoices

# Create a Flask Blueprint so this can be registered in app.py
bridge_bp = Blueprint("receptionist_bridge", __name__)

# Initialize the core modules
receptionist = EliteAIReceptionist()
brain = ReceptionistBrain()
tts_engine = TTSEngine()

# --------------------------------------------------------------------
# 🧠 Analyze Text (Calls, Emails, SMS) via the Brain
# --------------------------------------------------------------------
@bridge_bp.route("/analyze", methods=["POST"])
def analyze_text():
    """
    Takes a text input (from voice transcription, SMS, or email),
    passes it through the Brain for analysis, and returns structured data.
    """
    data = request.get_json()
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "No message provided"}), 400

    try:
        analysis = brain.analyze_message(message)
        receptionist_entry = receptionist.analyze_conversation(message)

        response = {
            "analysis": analysis,
            "receptionist_entry": receptionist_entry,
            "status": "success"
        }
        return jsonify(response), 200

    except Exception as e:
        print(f"[Bridge Error - analyze_text] {e}")
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------
# 🗣️ Generate Voice from Text
# --------------------------------------------------------------------
@bridge_bp.route("/speak", methods=["POST"])
def speak_text():
    """
    Converts a text string into an AI-generated voice response.
    Accepts JSON: {"text": "...", "voice": "professional_male/professional_female/friendly_receptionist"}
    """
    data = request.get_json()
    text = data.get("text")
    voice_type = data.get("voice", "professional_female")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        # Select voice preset
        voice_presets = {
            "professional_male": PresetVoices.professional_male(),
            "professional_female": PresetVoices.professional_female(),
            "friendly_receptionist": PresetVoices.friendly_receptionist(),
            "luxury_concierge": PresetVoices.luxury_concierge(),
            "enthusiastic_sales": PresetVoices.enthusiastic_sales()
        }
        
        voice_config = voice_presets.get(voice_type, PresetVoices.professional_female())
        
        # Generate speech with new engine
        audio_path = f"output/speech_{hash(text)}.wav"
        tts_engine.synthesize(text, voice_config, audio_path)
        
        return jsonify({
            "status": "success",
            "text": text,
            "voice": voice_type,
            "audio_path": audio_path
        }), 200
    except Exception as e:
        print(f"[Bridge Error - speak_text] {e}")
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------
# 📊 Get Analytics for Dashboard
# --------------------------------------------------------------------
@bridge_bp.route("/analytics", methods=["GET"])
def get_analytics():
    """
    Fetch combined analytics from calls, SMS, emails, and leads.
    """
    try:
        analytics_data = receptionist.get_analytics()
        return jsonify({
            "status": "success",
            "analytics": analytics_data
        }), 200
    except Exception as e:
        print(f"[Bridge Error - get_analytics] {e}")
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------
# 📊 Full Pipeline Example
# --------------------------------------------------------------------
@bridge_bp.route("/process", methods=["POST"])
def process_full_pipeline():
    """
    Unified endpoint that:
    1. Takes in a message
    2. Runs AI analysis (brain)
    3. Logs it with the receptionist
    4. Speaks the response (if requested)
    """
    data = request.get_json()
    message = data.get("message", "")
    voice_type = data.get("voice", "professional_female")

    if not message:
        return jsonify({"error": "No message provided"}), 400

    try:
        analysis = brain.analyze_message(message)
        receptionist_entry = receptionist.analyze_conversation(message)
        
        # Select voice preset
        voice_presets = {
            "professional_male": PresetVoices.professional_male(),
            "professional_female": PresetVoices.professional_female(),
            "friendly_receptionist": PresetVoices.friendly_receptionist(),
            "luxury_concierge": PresetVoices.luxury_concierge(),
            "enthusiastic_sales": PresetVoices.enthusiastic_sales()
        }
        
        voice_config = voice_presets.get(voice_type, PresetVoices.professional_female())
        audio_path = f"output/speech_{hash(analysis)}.wav"
        tts_engine.synthesize(analysis, voice_config, audio_path)

        return jsonify({
            "status": "success",
            "analysis": analysis,
            "receptionist_entry": receptionist_entry,
            "audio_path": audio_path
        }), 200
    except Exception as e:
        print(f"[Bridge Error - process_full_pipeline] {e}")
        return jsonify({"error": str(e)}), 500

# --------------------------------------------------------------------
# 🎙️ Save Voice Settings
# --------------------------------------------------------------------
@bridge_bp.route("/voice/settings", methods=["POST"])
def save_voice_settings():
    """
    Saves user's preferred voice and accent settings.
    If a clone file is uploaded, stores it for training later.
    """
    try:
        voice_type = request.form.get("voice_type", "female")
        accent = request.form.get("accent", "us")
        clone_file = request.files.get("clone_file")

        # Optional: Save preferences to database or JSON
        settings = {
            "voice_type": voice_type,
            "accent": accent,
            "clone_file": clone_file.filename if clone_file else None
        }

        # If they uploaded a clone file, save it to /uploads
        if clone_file:
            import os
            upload_dir = os.path.join("uploads", "voice_clones")
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, clone_file.filename)
            clone_file.save(file_path)
            settings["clone_path"] = file_path

        print(f"[Voice Settings Saved] {settings}")
        return jsonify({"status": "success", "settings": settings}), 200

    except Exception as e:
        print(f"[Voice Settings Error] {e}")
        return jsonify({"error": str(e)}), 500