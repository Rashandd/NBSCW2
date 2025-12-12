/**
 * Voice SharedWorker - Persistent Voice Connection Manager
 * 
 * This SharedWorker maintains WebSocket connections across page navigations.
 * It handles voice state synchronization between all open tabs/pages.
 */

// Store for all connected ports (browser tabs/pages)
const ports = new Set();

// Voice connection state
let voiceState = {
    connected: false,
    serverSlug: null,
    serverName: null,
    channelName: null,
    channelId: null,
    isMuted: false,
    isDeafened: false,
    participants: [], // [{userId, username, isMuted, isSpeaking}]
};

// WebSocket connection to Django Channels
let ws = null;
let wsUrl = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Broadcast message to all connected ports
function broadcast(message) {
    ports.forEach(port => {
        try {
            port.postMessage(message);
        } catch (e) {
            // Port might be closed, remove it
            ports.delete(port);
        }
    });
}

// Connect to voice WebSocket
function connectWebSocket(url, serverSlug, channelId) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        // Already connected, just return state
        return;
    }

    wsUrl = url;

    try {
        ws = new WebSocket(url);

        ws.onopen = () => {
            console.log('[VoiceWorker] WebSocket connected');
            reconnectAttempts = 0;

            // Update state
            voiceState.connected = true;
            voiceState.serverSlug = serverSlug;
            voiceState.channelId = channelId;

            // Broadcast to all pages
            broadcast({
                type: 'voice_connected',
                state: voiceState
            });
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('[VoiceWorker] Error parsing message:', e);
            }
        };

        ws.onclose = (event) => {
            console.log('[VoiceWorker] WebSocket closed:', event.code, event.reason);
            ws = null;

            // Update state
            voiceState.connected = false;

            // Broadcast disconnection
            broadcast({
                type: 'voice_disconnected',
                state: voiceState
            });

            // Try to reconnect if unexpected close
            if (event.code !== 1000 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                console.log(`[VoiceWorker] Attempting reconnect ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);
                setTimeout(() => connectWebSocket(wsUrl, serverSlug, channelId), 2000 * reconnectAttempts);
            }
        };

        ws.onerror = (error) => {
            console.error('[VoiceWorker] WebSocket error:', error);
        };

    } catch (e) {
        console.error('[VoiceWorker] Failed to create WebSocket:', e);
    }
}

// Disconnect from voice
function disconnectVoice() {
    if (ws) {
        ws.close(1000, 'User disconnected');
        ws = null;
    }

    // Reset state
    voiceState = {
        connected: false,
        serverSlug: null,
        serverName: null,
        channelName: null,
        channelId: null,
        isMuted: false,
        isDeafened: false,
        participants: [],
    };

    // Broadcast to all pages
    broadcast({
        type: 'voice_disconnected',
        state: voiceState
    });
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'user_joined':
            voiceState.participants.push({
                userId: data.user_id,
                username: data.username,
                isMuted: false,
                isSpeaking: false
            });
            broadcast({ type: 'participant_joined', data, state: voiceState });
            break;

        case 'user_left':
            voiceState.participants = voiceState.participants.filter(p => p.userId !== data.user_id);
            broadcast({ type: 'participant_left', data, state: voiceState });
            break;

        case 'user_muted':
            const mutedUser = voiceState.participants.find(p => p.userId === data.user_id);
            if (mutedUser) mutedUser.isMuted = data.is_muted;
            broadcast({ type: 'participant_updated', data, state: voiceState });
            break;

        case 'user_speaking':
            const speakingUser = voiceState.participants.find(p => p.userId === data.user_id);
            if (speakingUser) speakingUser.isSpeaking = data.is_speaking;
            broadcast({ type: 'participant_speaking', data, state: voiceState });
            break;

        case 'offer':
        case 'answer':
        case 'ice_candidate':
            // Forward WebRTC signaling to the main page (server_view)
            broadcast({ type: 'webrtc_signal', data });
            break;

        default:
            // Forward unknown messages
            broadcast({ type: 'ws_message', data });
    }
}

// Send message through WebSocket
function sendWebSocketMessage(message) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    }
}

// Update local voice state
function updateLocalState(updates) {
    Object.assign(voiceState, updates);
    broadcast({ type: 'state_updated', state: voiceState });
}

// Handle messages from pages
function handlePortMessage(port, message) {
    switch (message.type) {
        case 'connect':
            connectWebSocket(message.wsUrl, message.serverSlug, message.channelId);
            voiceState.serverName = message.serverName;
            voiceState.channelName = message.channelName;
            break;

        case 'disconnect':
            disconnectVoice();
            break;

        case 'get_state':
            port.postMessage({ type: 'state', state: voiceState });
            break;

        case 'set_muted':
            voiceState.isMuted = message.isMuted;
            sendWebSocketMessage({ type: 'mute', is_muted: message.isMuted });
            broadcast({ type: 'state_updated', state: voiceState });
            break;

        case 'set_deafened':
            voiceState.isDeafened = message.isDeafened;
            sendWebSocketMessage({ type: 'deafen', is_deafened: message.isDeafened });
            broadcast({ type: 'state_updated', state: voiceState });
            break;

        case 'send_signal':
            // Forward WebRTC signaling to server
            sendWebSocketMessage(message.data);
            break;

        default:
            console.log('[VoiceWorker] Unknown message type:', message.type);
    }
}

// SharedWorker connection handler
self.onconnect = function (e) {
    const port = e.ports[0];
    ports.add(port);

    console.log('[VoiceWorker] New connection, total ports:', ports.size);

    port.onmessage = function (event) {
        handlePortMessage(port, event.data);
    };

    // Send current state to new connection
    port.postMessage({ type: 'state', state: voiceState });

    port.start();
};

console.log('[VoiceWorker] SharedWorker initialized');
