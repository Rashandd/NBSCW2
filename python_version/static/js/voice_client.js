/**
 * Voice Client - Client-side library for voice chat
 * 
 * This connects to the SharedWorker and provides an easy API
 * for managing voice state across pages.
 */

class VoiceClient {
    constructor() {
        this.worker = null;
        this.port = null;
        this.state = {
            connected: false,
            serverSlug: null,
            serverName: null,
            channelName: null,
            channelId: null,
            isMuted: false,
            isDeafened: false,
            participants: [],
        };

        // Event callbacks
        this.onStateChange = null;
        this.onConnected = null;
        this.onDisconnected = null;
        this.onParticipantJoined = null;
        this.onParticipantLeft = null;
        this.onWebRTCSignal = null;

        this.init();
    }

    init() {
        // Check SharedWorker support
        if (typeof SharedWorker === 'undefined') {
            console.warn('[VoiceClient] SharedWorker not supported, falling back to regular mode');
            this.fallbackMode = true;
            return;
        }

        try {
            this.worker = new SharedWorker('/static/js/voice_worker.js', { name: 'voice-worker' });
            this.port = this.worker.port;

            this.port.onmessage = (event) => this.handleMessage(event.data);
            this.port.start();

            // Request current state
            this.port.postMessage({ type: 'get_state' });

            console.log('[VoiceClient] Connected to SharedWorker');
        } catch (e) {
            console.error('[VoiceClient] Failed to connect to SharedWorker:', e);
            this.fallbackMode = true;
        }
    }

    handleMessage(message) {
        switch (message.type) {
            case 'state':
            case 'state_updated':
                this.state = message.state;
                if (this.onStateChange) this.onStateChange(this.state);
                break;

            case 'voice_connected':
                this.state = message.state;
                if (this.onConnected) this.onConnected(this.state);
                if (this.onStateChange) this.onStateChange(this.state);
                break;

            case 'voice_disconnected':
                this.state = message.state;
                if (this.onDisconnected) this.onDisconnected(this.state);
                if (this.onStateChange) this.onStateChange(this.state);
                break;

            case 'participant_joined':
                this.state = message.state;
                if (this.onParticipantJoined) this.onParticipantJoined(message.data);
                if (this.onStateChange) this.onStateChange(this.state);
                break;

            case 'participant_left':
                this.state = message.state;
                if (this.onParticipantLeft) this.onParticipantLeft(message.data);
                if (this.onStateChange) this.onStateChange(this.state);
                break;

            case 'webrtc_signal':
                if (this.onWebRTCSignal) this.onWebRTCSignal(message.data);
                break;

            default:
                console.log('[VoiceClient] Unknown message:', message);
        }
    }

    // Connect to a voice channel
    connect(wsUrl, serverSlug, serverName, channelId, channelName) {
        if (this.fallbackMode) {
            console.warn('[VoiceClient] Cannot connect in fallback mode');
            return false;
        }

        this.port.postMessage({
            type: 'connect',
            wsUrl,
            serverSlug,
            serverName,
            channelId,
            channelName
        });
        return true;
    }

    // Disconnect from voice
    disconnect() {
        if (this.fallbackMode) return;
        this.port.postMessage({ type: 'disconnect' });
    }

    // Toggle mute
    setMuted(isMuted) {
        if (this.fallbackMode) return;
        this.port.postMessage({ type: 'set_muted', isMuted });
    }

    toggleMute() {
        this.setMuted(!this.state.isMuted);
    }

    // Toggle deafen
    setDeafened(isDeafened) {
        if (this.fallbackMode) return;
        this.port.postMessage({ type: 'set_deafened', isDeafened });
    }

    toggleDeafen() {
        this.setDeafened(!this.state.isDeafened);
    }

    // Send WebRTC signaling data
    sendSignal(data) {
        if (this.fallbackMode) return;
        this.port.postMessage({ type: 'send_signal', data });
    }

    // Get current state
    getState() {
        return this.state;
    }

    // Check if connected to voice
    isConnected() {
        return this.state.connected;
    }

    // Check if SharedWorker is available
    isSharedWorkerAvailable() {
        return !this.fallbackMode;
    }
}

// Global instance
window.voiceClient = new VoiceClient();

// Helper function to update voice popup UI
function updateVoicePopupUI() {
    const popup = document.getElementById('voice-popup');
    if (!popup) return;

    const state = window.voiceClient.getState();

    if (state.connected) {
        popup.classList.add('active');

        // Update server/channel name
        const serverLabel = popup.querySelector('.voice-popup-server');
        if (serverLabel) {
            serverLabel.textContent = `${state.serverName || 'Server'} / ${state.channelName || 'Voice'}`;
        }

        // Update participants
        const usersContainer = popup.querySelector('#voice-popup-users');
        if (usersContainer) {
            usersContainer.innerHTML = state.participants.map(p => `
                <div class="voice-popup-user ${p.isSpeaking ? 'speaking' : ''}" title="${p.username}">
                    ${p.username.charAt(0).toUpperCase()}
                </div>
            `).join('');
        }

        // Update mute button
        const muteBtn = popup.querySelector('.voice-popup-btn.mute');
        if (muteBtn) {
            muteBtn.classList.toggle('active', state.isMuted);
        }
    } else {
        popup.classList.remove('active');
    }
}

// Set up voice client callbacks
if (window.voiceClient) {
    window.voiceClient.onStateChange = updateVoicePopupUI;
}

console.log('[VoiceClient] Client library loaded');
