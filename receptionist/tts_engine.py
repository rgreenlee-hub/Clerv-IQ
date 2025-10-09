# receptionist/tts_engine.py
"""
TTS Engine for ClervIQ Receptionist
Generates speech dynamically during calls using the voice engine.
"""

from voice_engine import TTSEngine, PresetVoices
import os

# Initialize the TTS model once (loads into memory)
tts_engine = TTSEngine()

def generate_speech(text, voice_type="professional_female", filename="response.wav"):
    """
    Generate speech audio from text and save it to a file.
    
    Args:
        text: The text to convert to speech
        voice_type: Type of voice preset to use
        filename: Output filename (default: response.wav)
    
    Returns:
        output_path: Path to the generated audio file
    """
    # Select voice preset
    voice_presets = {
        "professional_male": PresetVoices.professional_male(),
        "professional_female": PresetVoices.professional_female(),
        "friendly_receptionist": PresetVoices.friendly_receptionist(),
        "luxury_concierge": PresetVoices.luxury_concierge(),
        "enthusiastic_sales": PresetVoices.enthusiastic_sales()
    }
    
    voice_config = voice_presets.get(voice_type, PresetVoices.professional_female())
    
    # Create output path
    output_path = os.path.join("static", filename)
    
    # Generate speech
    tts_engine.synthesize(text=text, voice_config=voice_config, output_path=output_path)
    
    return output_path


# Example usage
if __name__ == "__main__":
    # Test the TTS engine
    test_text = "Hello! Welcome to ClervIQ. How may I assist you today?"
    audio_path = generate_speech(test_text, voice_type="friendly_receptionist")
    print(f"✓ Audio generated: {audio_path}")