# Technical Context - Rashigo

## Architecture: App Shell Pattern

### Overview
Single-page application shell with dynamic content loading via HTMX.
No page reloads for core navigation - content swaps in `#main-viewport`.

### Layout Structure
```
┌─────────────────────────────────────────────────────┐
│                   Topbar (52px)                     │
│  [Context Title]                    [User Avatar]   │
├─────────┬───────────────────────────────────────────┤
│         │                                           │
│ Sidebar │           #main-viewport                  │
│ (72px)  │                                           │
│         │  Dynamic content loaded via HTMX:         │
│  Home   │  - _home.html (default)                   │
│ Servers │  - _settings.html                         │
│  Games  │  - _minigames.html                        │
│  Ranks  │  - _leaderboard.html                      │
│         │  - _servers.html                          │
│ ─────── │                                           │
│Settings │                                           │
│         │                                           │
└─────────┴───────────────────────────────────────────┘
```

### Key Rules
1. **Single Sidebar**: Only ONE persistent sidebar on the left
2. **No Nested Sidebars**: All content loads in `#main-viewport`
3. **HTMX Loading**: Use `hx-get`, `hx-target`, `hx-swap` for navigation

---

## Template Structure
```
templates/
├── base_app.html              # Master App Shell
├── landing.html               # Unauthenticated landing
├── partials/
│   ├── _home.html            # Welcome + server grid
│   ├── _settings.html        # User settings
│   ├── _servers.html         # Server list grid
│   ├── _minigames.html       # Game center
│   ├── _leaderboard.html     # Rankings
│   └── _game_lobby.html      # Dice Wars lobby
├── server_view.html           # Server chat interface
└── game_room.html            # Active game session
```

---

## URL Routing
| Path | View | Description |
|------|------|-------------|
| `/` | `app_shell` | Main App Shell (authenticated) or landing |
| `/?view=home` | partial | Home greeting + servers |
| `/?view=settings` | partial | Settings panel |
| `/game-lobby/` | partial | All games list |
| `/leaderboard/` | partial | Rankings |
| `/server/<slug>/` | full page | Server chat interface |

---

## Key Technologies
- **Django 5.2+**: Web framework
- **HTMX 1.9+**: Dynamic content loading
- **Django Channels**: WebSocket for real-time
- **PostgreSQL**: Database
- **WebRTC + COTURN**: Voice communication
- **Lucide Icons**: SVG icon set

---

## Database Models
### User: `CustomUser`
- Extended AbstractUser with rank_point, game stats, JSONField

### Server System
- `Server`, `ServerRole`, `ServerMember`
- `TextChannel`, `VoiceChannel`

### Gaming
- `MiniGame`: Game definitions
- `GameSession`: Active instances with board_state
