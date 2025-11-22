# Database Reset Instructions

## What Was Done

1. **Deleted all existing migrations** - All migration files except `__init__.py` have been removed
2. **Enhanced CustomUser model** - Made it more flexible with:
   - JSON fields for extensible settings, metadata, and per-game stats
   - Additional fields: avatar_url, bio, status_message, is_online
   - Helper methods for updating/getting settings and metadata
   - Better indexing for performance

3. **Enhanced Server model** - Made it more flexible with:
   - JSON fields for extensible settings, features, and metadata
   - Additional fields: banner_url, is_verified, max_members, max_channels
   - Helper methods for managing settings, features, and metadata
   - Better indexing for performance

4. **Fixed timestamp fields** - Changed all `created_at` fields to use `auto_now_add=True` for consistency

## Next Steps

To create fresh migrations and reset the database:

```bash
cd python_version

# Create fresh migrations
python3 manage.py makemigrations

# Reset database (WARNING: This will delete all data!)
python3 manage.py migrate --run-syncdb

# Or if you want to start completely fresh:
# Delete the database file (if using SQLite)
# Then run:
python3 manage.py migrate
```

## Game Algorithms

All game algorithms remain unchanged. The GameSession model and game logic are preserved exactly as they were.

## New Features

### CustomUser Enhancements:
- `user_settings` - Store user preferences (theme, notifications, etc.)
- `metadata` - Store custom user data without schema changes
- `per_game_stats` - Track statistics per game type
- `avatar_url` - Custom avatar support
- `bio` - User biography
- `status_message` - Custom status message
- `is_online` - Online status tracking

### Server Enhancements:
- `settings` - Server configuration (notifications, moderation, etc.)
- `features` - Enable/disable features dynamically
- `metadata` - Store custom server data without schema changes
- `banner_url` - Server banner image
- `is_verified` - Verified server badge
- `max_members` - Configurable member limit
- `max_channels` - Configurable channel limit

All JSON fields support dynamic data without requiring database migrations!

