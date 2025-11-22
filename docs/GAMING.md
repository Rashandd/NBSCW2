# Gaming Platform

Documentation for the gaming features of Rashigo.

## Overview

Rashigo includes a comprehensive gaming platform with:
- Multiple mini-games (Dice Wars, extensible framework)
- Real-time multiplayer gameplay via WebSockets
- Leaderboards and player statistics
- Public and private game rooms
- Matchmaking system

## Games

### Dice Wars

A strategy game where players compete to control territories on a board.

**Features:**
- Dynamic board sizes (5x5, 7x7, 9x9 based on player count)
- Turn-based gameplay
- Chain reaction mechanics
- Player elimination
- Real-time updates

**Game Flow:**
1. Players join a game session
2. Game starts when minimum players join
3. Players take turns placing pieces
4. Chain reactions occur when cells reach critical mass
5. Eliminated players are tracked
6. Game ends when one player remains

### Adding New Games

Create a new game by:

1. **Define Game Model**
```python
# In main/models.py
game = MiniGame.objects.create(
    name="My New Game",
    description="Game description",
    min_players=2,
    max_players=4,
    is_active=True
)
```

2. **Create Game Consumer**
```python
# In main/consumers.py
class MyGameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        # Handle connection
        pass
    
    async def receive_json(self, content):
        # Handle game actions
        pass
```

3. **Add Routing**
```python
# In main/routing.py
websocket_urlpatterns = [
    path('ws/game/mygame/<uuid:game_id>/', MyGameConsumer.as_asgi()),
]
```

4. **Create Template**
```html
<!-- templates/mygame.html -->
<!-- Game UI and WebSocket client -->
```

## Game Sessions

### Creating a Session

```python
from main.models import GameSession, MiniGame

game_type = MiniGame.objects.get(slug='dice-wars')
session = GameSession.objects.create(
    game_type=game_type,
    host=request.user,
    status='waiting',
    is_private=False
)
```

### Joining a Session

```python
session.players.add(request.user)
if session.player_count >= session.game_type.min_players:
    session.status = 'in_progress'
    session.save()
```

### Game State Management

Game state is stored in `board_state` JSON field:

```python
{
    "0": {
        "0": {"owner": "player1", "count": 2},
        "1": {"owner": "player2", "count": 1}
    },
    "1": {
        "0": null,
        "1": {"owner": "player1", "count": 3}
    }
}
```

## Leaderboards

### Global Leaderboard

```python
from main.models import CustomUser

top_players = CustomUser.objects.order_by('-rank_point')[:10]
```

### Game-Specific Leaderboard

```python
# Get top players for Dice Wars
players = CustomUser.objects.all()
dice_wars_leaders = sorted(
    players,
    key=lambda p: p.per_game_stats.get('dice-wars', {}).get('rank_point', 0),
    reverse=True
)[:10]
```

## Statistics

### User Statistics

Each user has:
- `rank_point`: Overall ranking points
- `total_wins`: Total wins across all games
- `total_losses`: Total losses
- `total_games`: Total games played
- `per_game_stats`: Game-specific statistics

```python
user = CustomUser.objects.get(username='player1')
print(f"Win rate: {user.win_rate}%")
print(f"Dice Wars stats: {user.per_game_stats.get('dice-wars')}")
```

### Updating Statistics

Statistics are automatically updated when games end:

```python
from main.consumers import update_player_rankings

# Called automatically in game consumer
update_player_rankings(game_session, winner)
```

## WebSocket Protocol

### Client Connection

```javascript
const gameSocket = new WebSocket(
    `ws://${window.location.host}/ws/game/dice-wars/${gameId}/`
);

gameSocket.onopen = function(e) {
    console.log('Connected to game');
};

gameSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    handleGameUpdate(data);
};
```

### Message Types

**Make Move:**
```json
{
    "action": "make_move",
    "row": 2,
    "col": 3
}
```

**Game State Update:**
```json
{
    "type": "game_state",
    "board_state": {...},
    "current_turn": "player1",
    "players": ["player1", "player2"],
    "eliminated_players": []
}
```

**Player Joined:**
```json
{
    "type": "player_joined",
    "username": "player3",
    "player_count": 3
}
```

**Game Over:**
```json
{
    "type": "game_over",
    "winner": "player1",
    "final_stats": {...}
}
```

## Matchmaking

### Public Games

```python
# Find available public games
available_games = GameSession.objects.filter(
    game_type=game_type,
    status='waiting',
    is_private=False
).exclude(
    players__in=[request.user]
)

if available_games.exists():
    session = available_games.first()
    session.players.add(request.user)
else:
    # Create new session
    session = GameSession.objects.create(...)
```

### Private Games

```python
# Create private game
session = GameSession.objects.create(
    game_type=game_type,
    host=request.user,
    is_private=True,
    invited_players=['player2', 'player3']
)

# Join with invite
if request.user.username in session.invited_players:
    session.players.add(request.user)
```

## Cleanup

Stale games are automatically cleaned up:

```bash
# Run cleanup command
python manage.py cleanup_stale_games
```

Or schedule with cron:
```bash
# Every hour
0 * * * * cd /path/to/project && python manage.py cleanup_stale_games
```

## Best Practices

1. **State Management**: Always validate game state before moves
2. **Error Handling**: Handle disconnections gracefully
3. **Security**: Validate user permissions for moves
4. **Performance**: Use database indexes for queries
5. **Testing**: Test with multiple concurrent players

## Troubleshooting

**WebSocket not connecting:**
- Check Daphne is running (not Django runserver)
- Verify WebSocket URL is correct
- Check browser console for errors

**Game state not updating:**
- Verify Redis/channel layer is configured
- Check WebSocket connection is active
- Review game consumer logs

**Players can't join:**
- Check game status is 'waiting'
- Verify game isn't full
- Check private game invite list
