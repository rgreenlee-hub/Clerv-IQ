/**
 * ClervIQ Voice Engine Integration
 * Drop this into your existing settings/integrations HTML
 * 
 * Requirements:
 * - API server running at http://localhost:8000
 * - HTML elements with matching IDs (see usage below)
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const VOICE_API_URL = 'http://localhost:8000/api';
const CLIENT_ID = 'your_client_id'; // Set this to your actual client ID

// ============================================================================
// VOICE SETTINGS STATE
// ============================================================================

const voiceSettings = {
    voiceType: 'preset', // 'preset' or 'custom'
    presetVoice: 'professional_female',
    customVoice: null,
    accent: 'en',
    emotion: 'professional',
    pitch: 0,
    speed: 1.0,
    energy: 1.0
};

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Fetch all available preset voices
 */
async function fetchPresetVoices() {
    try {
        const response = await fetch(`${VOICE_API_URL}/voices/presets`);
        const data = await response.json();
        return data.presets;
    } catch (error) {
        console.error('Failed to fetch preset voices:', error);
        return [];
    }
}

/**
 * Fetch custom voices for client
 */
async function fetchCustomVoices(clientId) {
    try {
        const response = await fetch(`${VOICE_API_URL}/clients/${clientId}/voices`);
        const data = await response.json();
        return data.voices;
    } catch (error) {
        console.error('Failed to fetch custom voices:', error);
        return [];
    }
}

/**
 * Fetch all available accents
 */
async function fetchAccents() {
    try {
        const response = await fetch(`${VOICE_API_URL}/accents`);
        const data = await response.json();
        return data.accents;
    } catch (error) {
        console.error('Failed to fetch accents:', error);
        return [];
    }
}

/**
 * Fetch all available emotions
 */
async function fetchEmotions() {
    try {
        const response = await fetch(`${VOICE_API_URL}/emotions`);
        const data = await response.json();
        return data.emotions;
    } catch (error) {
        console.error('Failed to fetch emotions:', error);
        return [];
    }
}

/**
 * Test/preview voice with current settings
 */
async function testVoice(text = "Hello! Welcome to ClervIQ. How may I assist you today?") {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('pitch_shift', voiceSettings.pitch);
    formData.append('speed', voiceSettings.speed);
    formData.append('energy', voiceSettings.energy);
    formData.append('emotion', voiceSettings.emotion);
    
    if (voiceSettings.voiceType === 'preset') {
        formData.append('voice_preset', voiceSettings.presetVoice);
    } else {
        formData.append('client_id', CLIENT_ID);
        formData.append('voice_name', voiceSettings.customVoice);
    }
    
    try {
        showLoading('Testing voice...');
        
        const response = await fetch(`${VOICE_API_URL}/synthesize`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Voice synthesis failed');
        }
        
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Play audio
        playAudio(audioUrl);
        
        hideLoading();
        showSuccess('Voice preview ready!');
        
        return audioUrl;
        
    } catch (error) {
        hideLoading();
        showError('Failed to generate voice preview: ' + error.message);
        console.error('Test voice error:', error);
        return null;
    }
}

/**
 * Clone a voice from uploaded audio file
 */
async function cloneVoice(audioFile, voiceName, gender, accent) {
    const formData = new FormData();
    formData.append('client_id', CLIENT_ID);
    formData.append('voice_name', voiceName);
    formData.append('gender', gender);
    formData.append('accent', accent);
    formData.append('audio_file', audioFile);
    
    try {
        showLoading('Cloning voice... This may take a minute.');
        
        const response = await fetch(`${VOICE_API_URL}/clone-voice`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (response.ok) {
            showSuccess(`Voice "${voiceName}" cloned successfully!`);
            // Refresh custom voices list
            await loadCustomVoices();
            return data;
        } else {
            throw new Error(data.message || 'Voice cloning failed');
        }
        
    } catch (error) {
        hideLoading();
        showError('Failed to clone voice: ' + error.message);
        console.error('Clone voice error:', error);
        return null;
    }
}

/**
 * Save voice settings (to your backend or localStorage)
 */
async function saveVoiceSettings() {
    try {
        showLoading('Saving settings...');
        
        // Option 1: Save to localStorage
        localStorage.setItem('clerviq_voice_settings', JSON.stringify(voiceSettings));
        
        // Option 2: Save to your backend
        // await fetch('/your-backend/save-voice-settings', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify(voiceSettings)
        // });
        
        hideLoading();
        showSuccess('Voice settings saved successfully!');
        
        return true;
        
    } catch (error) {
        hideLoading();
        showError('Failed to save settings: ' + error.message);
        console.error('Save settings error:', error);
        return false;
    }
}

/**
 * Load saved voice settings
 */
function loadVoiceSettings() {
    try {
        // Option 1: Load from localStorage
        const saved = localStorage.getItem('clerviq_voice_settings');
        if (saved) {
            const settings = JSON.parse(saved);
            Object.assign(voiceSettings, settings);
            updateUIFromSettings();
        }
        
        // Option 2: Load from your backend
        // const response = await fetch('/your-backend/get-voice-settings');
        // const settings = await response.json();
        // Object.assign(voiceSettings, settings);
        // updateUIFromSettings();
        
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

// ============================================================================
// UI UPDATE FUNCTIONS
// ============================================================================

/**
 * Populate voice dropdowns
 */
async function loadVoiceOptions() {
    // Load preset voices
    const presets = await fetchPresetVoices();
    const presetSelect = document.getElementById('voicePresetSelect');
    if (presetSelect) {
        presetSelect.innerHTML = presets.map(preset => 
            `<option value="${preset}">${formatVoiceName(preset)}</option>`
        ).join('');
    }
    
    // Load custom voices
    await loadCustomVoices();
    
    // Load accents
    const accents = await fetchAccents();
    const accentSelect = document.getElementById('voiceAccentSelect');
    if (accentSelect) {
        accentSelect.innerHTML = accents.map(accent => 
            `<option value="${accent}">${formatAccentName(accent)}</option>`
        ).join('');
    }
    
    // Load emotions
    const emotions = await fetchEmotions();
    const emotionSelect = document.getElementById('voiceEmotionSelect');
    if (emotionSelect) {
        emotionSelect.innerHTML = emotions.map(emotion => 
            `<option value="${emotion}">${formatEmotionName(emotion)}</option>`
        ).join('');
    }
}

/**
 * Load custom voices for client
 */
async function loadCustomVoices() {
    const customVoices = await fetchCustomVoices(CLIENT_ID);
    const customSelect = document.getElementById('voiceCustomSelect');
    if (customSelect) {
        if (customVoices.length === 0) {
            customSelect.innerHTML = '<option value="">No custom voices yet</option>';
        } else {
            customSelect.innerHTML = customVoices.map(voice => 
                `<option value="${voice.name}">${voice.name} (${voice.gender}, ${voice.accent})</option>`
            ).join('');
        }
    }
}

/**
 * Update UI elements from settings object
 */
function updateUIFromSettings() {
    // Voice type
    const voiceTypeSelect = document.getElementById('voiceTypeSelect');
    if (voiceTypeSelect) voiceTypeSelect.value = voiceSettings.voiceType;
    
    // Preset voice
    const presetSelect = document.getElementById('voicePresetSelect');
    if (presetSelect) presetSelect.value = voiceSettings.presetVoice;
    
    // Accent
    const accentSelect = document.getElementById('voiceAccentSelect');
    if (accentSelect) accentSelect.value = voiceSettings.accent;
    
    // Emotion
    const emotionSelect = document.getElementById('voiceEmotionSelect');
    if (emotionSelect) emotionSelect.value = voiceSettings.emotion;
    
    // Pitch slider
    const pitchSlider = document.getElementById('voicePitchSlider');
    if (pitchSlider) pitchSlider.value = voiceSettings.pitch;
    const pitchValue = document.getElementById('voicePitchValue');
    if (pitchValue) pitchValue.textContent = voiceSettings.pitch;
    
    // Speed slider
    const speedSlider = document.getElementById('voiceSpeedSlider');
    if (speedSlider) speedSlider.value = voiceSettings.speed;
    const speedValue = document.getElementById('voiceSpeedValue');
    if (speedValue) speedValue.textContent = voiceSettings.speed + 'x';
    
    // Energy slider
    const energySlider = document.getElementById('voiceEnergySlider');
    if (energySlider) energySlider.value = voiceSettings.energy;
    const energyValue = document.getElementById('voiceEnergyValue');
    if (energyValue) energyValue.textContent = voiceSettings.energy;
}

// ============================================================================
// EVENT HANDLERS
// ============================================================================

/**
 * Handle voice type change (preset vs custom)
 */
function handleVoiceTypeChange(value) {
    voiceSettings.voiceType = value;
    
    // Show/hide appropriate dropdowns
    const presetGroup = document.getElementById('voicePresetGroup');
    const customGroup = document.getElementById('voiceCustomGroup');
    
    if (value === 'preset') {
        if (presetGroup) presetGroup.style.display = 'block';
        if (customGroup) customGroup.style.display = 'none';
    } else {
        if (presetGroup) presetGroup.style.display = 'none';
        if (customGroup) customGroup.style.display = 'block';
    }
}

/**
 * Handle preset voice selection
 */
function handlePresetVoiceChange(value) {
    voiceSettings.presetVoice = value;
}

/**
 * Handle custom voice selection
 */
function handleCustomVoiceChange(value) {
    voiceSettings.customVoice = value;
}

/**
 * Handle accent change
 */
function handleAccentChange(value) {
    voiceSettings.accent = value;
}

/**
 * Handle emotion change
 */
function handleEmotionChange(value) {
    voiceSettings.emotion = value;
}

/**
 * Handle pitch slider change
 */
function handlePitchChange(value) {
    voiceSettings.pitch = parseFloat(value);
    const pitchValue = document.getElementById('voicePitchValue');
    if (pitchValue) pitchValue.textContent = value;
}

/**
 * Handle speed slider change
 */
function handleSpeedChange(value) {
    voiceSettings.speed = parseFloat(value);
    const speedValue = document.getElementById('voiceSpeedValue');
    if (speedValue) speedValue.textContent = value + 'x';
}

/**
 * Handle energy slider change
 */
function handleEnergyChange(value) {
    voiceSettings.energy = parseFloat(value);
    const energyValue = document.getElementById('voiceEnergyValue');
    if (energyValue) energyValue.textContent = value;
}

/**
 * Handle test voice button click
 */
async function handleTestVoice() {
    const testText = document.getElementById('voiceTestText')?.value || 
                     "Hello! Welcome to ClervIQ. How may I assist you today?";
    await testVoice(testText);
}

/**
 * Handle save settings button click
 */
async function handleSaveSettings() {
    await saveVoiceSettings();
}

/**
 * Handle file upload for voice cloning
 */
async function handleVoiceUpload(file) {
    const voiceName = document.getElementById('cloneVoiceName')?.value || 'Custom Voice';
    const gender = document.getElementById('cloneVoiceGender')?.value || 'neutral';
    const accent = document.getElementById('cloneVoiceAccent')?.value || 'en';
    
    if (!file) {
        showError('Please select an audio file');
        return;
    }
    
    await cloneVoice(file, voiceName, gender, accent);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Play audio from URL
 */
function playAudio(audioUrl) {
    const audioPlayer = document.getElementById('voicePreviewPlayer');
    if (audioPlayer) {
        audioPlayer.src = audioUrl;
        audioPlayer.style.display = 'block';
        audioPlayer.play();
    } else {
        // Create temporary audio element
        const audio = new Audio(audioUrl);
        audio.play();
    }
}

/**
 * Format voice name for display
 */
function formatVoiceName(name) {
    return name.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

/**
 * Format accent name for display
 */
function formatAccentName(accent) {
    const accentNames = {
        'en': 'American English',
        'en-gb': 'British English',
        'en-au': 'Australian English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese'
    };
    return accentNames[accent] || accent;
}

/**
 * Format emotion name for display
 */
function formatEmotionName(emotion) {
    return emotion.charAt(0).toUpperCase() + emotion.slice(1);
}

/**
 * Show loading message
 */
function showLoading(message) {
    const statusEl = document.getElementById('voiceStatusMessage');
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = 'status-message status-info';
        statusEl.style.display = 'block';
    }
}

/**
 * Hide loading message
 */
function hideLoading() {
    const statusEl = document.getElementById('voiceStatusMessage');
    if (statusEl) {
        statusEl.style.display = 'none';
    }
}

/**
 * Show success message
 */
function showSuccess(message) {
    const statusEl = document.getElementById('voiceStatusMessage');
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = 'status-message status-success';
        statusEl.style.display = 'block';
        setTimeout(() => statusEl.style.display = 'none', 5000);
    }
}

/**
 * Show error message
 */
function showError(message) {
    const statusEl = document.getElementById('voiceStatusMessage');
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = 'status-message status-error';
        statusEl.style.display = 'block';
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize voice integration
 * Call this when your settings page loads
 */
async function initVoiceIntegration() {
    console.log('Initializing ClervIQ Voice Integration...');
    
    // Load saved settings
    loadVoiceSettings();
    
    // Load voice options
    await loadVoiceOptions();
    
    // Update UI
    updateUIFromSettings();
    
    console.log('Voice integration ready!');
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVoiceIntegration);
} else {
    initVoiceIntegration();
}

// ============================================================================
// EXPORT FOR USE IN YOUR HTML
// ============================================================================

// Expose functions globally for onclick handlers
window.voiceIntegration = {
    testVoice: handleTestVoice,
    saveSettings: handleSaveSettings,
    uploadVoice: handleVoiceUpload,
    handleVoiceTypeChange,
    handlePresetVoiceChange,
    handleCustomVoiceChange,
    handleAccentChange,
    handleEmotionChange,
    handlePitchChange,
    handleSpeedChange,
    handleEnergyChange
};
