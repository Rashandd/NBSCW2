# Communication System

Documentation for the Discord-like communication features.

## Overview

Rashigo includes a comprehensive communication system with:
- Discord-like servers and channels
- Text and voice channels
- Real-time messaging via WebSockets
- WebRTC voice communication
- Role-based permissions
- User presence tracking

## Servers

### Creating a Server

```python
from main.models import Server, ServerRole, ServerMember

# Create server
server = Server.objects.create(
    name="My Community",
    description="A great community server",
    owner=request.user,
    icon="🎮",
    is_private=False
)

# Create default roles
admin_role = ServerRole.objects.create(
    server=server,
    name="Admin",
    color="#FF0000",
    permissions={"manage_channels": True, "manage_roles": True},
    position=100
)

member_role = ServerRole.objects.create(
    server=server,
    name="Member",
    color="#99AAB5",
    permissions={"send_messages": True, "join_voice": True},
    position=1
)

# Add owner as member with admin role
membership = ServerMember.objects.create(
    server=server,
    user=request.user
)
membership.roles.add(admin_role)
```

### Joining a Server

```python
# Join server
membership = ServerMember.objects.create(
    server=server,
    user=request.user
)
membership.roles.add(member_role)  # Assign default role
```

## Channels

### Text Channels

```python
from main.models import TextChannel

text_channel = TextChannel.objects.create(
    server=server,
    name="general",
    description="General discussion",
    position=0,
    is_private=False
)
```

### Voice Channels

```python
from main.models import VoiceChannel

voice_channel = VoiceChannel.objects.create(
    server=server,
    name="Voice Chat",
    description="General voice chat",
    position=0,
    user_limit=10,  # 0 = unlimited
    is_private=False
)
```

## Messaging

### Sending Messages

Messages are sent via WebSocket:

```javascript
const chatSocket = new WebSocket(
    `ws://${window.location.host}/ws/text/${channelSlug}/`
);

// Send message
chatSocket.send(JSON.stringify({
    'action': 'chat_message',
    'message': 'Hello everyone!'
}));
```

### Storing Messages

```python
from main.models import ChatMessage

message = ChatMessage.objects.create(
    channel=text_channel,
    user=request.user,
    content="Hello everyone!"
)
```

### Loading Message History

```python
# Get recent messages
messages = ChatMessage.objects.filter(
    channel=text_channel
).select_related('user').order_by('-created_at')[:50]
```

## Voice Communication

### WebRTC Setup

Voice communication uses WebRTC with COTURN server.

**Configuration** (`settings.py`):
```python
COTURN_CONFIG = {
    'ice_servers': [
        {
            'urls': ['stun:your-server:3478', 'turn:your-server:3478'],
            'username': 'username',
            'credential': 'password',
        },
        {'urls': ['stun:stun.l.google.com:19302']},
    ]
}
```

### Connecting to Voice

```javascript
const voiceSocket = new WebSocket(
    `ws://${window.location.host}/ws/voice/${channelSlug}/`
);

// Initialize WebRTC
const peerConnection = new RTCPeerConnection({
    iceServers: iceServers
});

// Get local audio stream
navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    .then(stream => {
        localStream = stream;
        stream.getTracks().forEach(track => {
            peerConnection.addTrack(track, stream);
        });
    });

// Handle WebRTC signaling
voiceSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    
    if (data.type === 'webrtc_signal') {
        if (data.signal_type === 'offer') {
            handleOffer(data.data);
        } else if (data.signal_type === 'answer') {
            handleAnswer(data.data);
        } else if (data.signal_type === 'ice-candidate') {
            handleIceCandidate(data.data);
        }
    }
};
```

## Roles & Permissions

### Permission System

```python
# Check permission
def has_permission(member, permission):
    for role in member.roles.all():
        if role.permissions.get(permission, False):
            return True
    return False

# Usage
if has_permission(member, 'manage_channels'):
    # Allow action
    pass
```

### Common Permissions

- `send_messages`: Send text messages
- `manage_messages`: Delete/edit others' messages
- `manage_channels`: Create/edit/delete channels
- `manage_roles`: Create/edit roles
- `kick_members`: Kick members from server
- `ban_members`: Ban members from server
- `join_voice`: Join voice channels
- `speak`: Speak in voice channels
- `mute_members`: Mute other members

## Presence System

### Online Status

```python
from main.middleware import OnlineStatusMiddleware

# Middleware automatically tracks user activity
# Users are marked online when making requests
```

### Manual Status Update

```python
from main.models import ServerMember

# Mark user online
ServerMember.objects.filter(user=user).update(is_online=True)

# Mark user offline
ServerMember.objects.filter(user=user).update(is_online=False)
```

## WebSocket Consumers

### Text Channel Consumer

```python
# main/consumers.py
class VoiceChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        # Join channel group
        await self.channel_layer.group_add(
            self.channel_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def receive_json(self, content):
        if content['action'] == 'chat_message':
            # Broadcast message
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    'type': 'chat.message',
                    'message': content['message'],
                    'username': self.scope['user'].username
                }
            )
```

## API Endpoints

### Get Server Channels

```python
# views.py
def server_channels(request, server_slug):
    server = get_object_or_404(Server, slug=server_slug)
    
    # Check membership
    if not server.members.filter(user=request.user).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)
    
    text_channels = server.text_channels.all()
    voice_channels = server.voice_channels.all()
    
    return JsonResponse({
        'text_channels': [
            {'id': c.id, 'name': c.name, 'slug': c.slug}
            for c in text_channels
        ],
        'voice_channels': [
            {'id': c.id, 'name': c.name, 'slug': c.slug}
            for c in voice_channels
        ]
    })
```

## Best Practices

1. **Security**: Always verify user permissions before actions
2. **Performance**: Use select_related/prefetch_related for queries
3. **Scalability**: Use Redis for channel layers in production
4. **Error Handling**: Handle WebSocket disconnections gracefully
5. **Rate Limiting**: Implement rate limiting for messages

## Troubleshooting

**Voice not working:**
- Verify COTURN server is running and accessible
- Check ICE server configuration
- Test with STUN servers first
- Review browser console for WebRTC errors

**Messages not appearing:**
- Check WebSocket connection is active
- Verify channel layer (Redis) is running
- Check user has permission to view channel

**Can't join server:**
- Verify server exists and is not private
- Check user isn't already a member
- Review server permissions
