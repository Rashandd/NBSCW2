# Technical Context - Rashigo

## Project Structure
```
NBSCW2/
├── docs/                    # Documentation
├── python_version/          # Main Django app
│   ├── main/               # Core application
│   │   ├── models.py       # Database models
│   │   ├── views.py        # View functions
│   │   ├── consumers.py    # WebSocket consumers
│   │   ├── urls.py         # URL routing
│   │   └── api/            # REST API endpoints
│   ├── templates/          # HTML templates
│   └── python_version/     # Django settings
```

## Database Models

### User System
- `CustomUser`: Extended AbstractUser with rank_point, game stats, JSONField settings
- `RegistrationAttempt`: Security tracking for registrations

### Server System
- `Server`: Community servers with owner, settings, features (JSONField)
- `ServerRole`: Role-based permissions
- `ServerMember`: User-server relationships with roles
- `TextChannel` / `VoiceChannel`: Communication channels

### Gaming
- `MiniGame`: Game definitions (name, min/max players)
- `GameSession`: Active game instances with board_state (JSONField)

### AI (Optional)
- `AIAgent`, `Workflow`, `MemoryBank`: AI agent capabilities

## Template Inheritance
```
base.html                    # Root template (navbar, CSS, voice mini-box)
├── index.html              # Home/server list
├── server_view.html        # Main server interface (3-column layout)
├── minigames.html          # Game center
├── leaderboard.html        # Rankings
└── game_room.html          # Active game view
```

## Key Technologies
- **Django 5.2+**: Web framework
- **Django Channels**: WebSocket support
- **PostgreSQL**: Database
- **WebRTC + COTURN**: Voice communication
- **Bootstrap 5**: CSS framework

## View Structure
- `index`: Landing page, server list
- `server_view`: Main chat/voice interface
- `all_games_lobby`: Game center
- `game_room`: Active game session
- `leaderboard`: Rankings
