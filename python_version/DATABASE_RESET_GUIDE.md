# Database Reset Guide - Following SERVER_STRUCTURE.md

## Overview
This guide will help you reset the database and create fresh migrations according to the SERVER_STRUCTURE.md specifications.

## Prerequisites
- PostgreSQL database is running
- Database credentials are configured in `.env` or `settings.py`
- All old migrations have been deleted (already done)

## Step-by-Step Instructions

### Step 1: Create Fresh Migrations

```bash
cd python_version
python3 manage.py makemigrations
```

This will create initial migrations for all models including:
- CustomUser (enhanced with flexible JSON fields)
- Server (enhanced with flexible JSON fields)
- ServerRole
- ServerMember
- TextChannel
- VoiceChannel
- ChatMessage
- PrivateConversation
- PrivateMessage
- MiniGame
- GameSession
- AIAgent
- Workflow
- WorkflowExecution
- MemoryBank

### Step 2: Reset Database

**Option A: Using PostgreSQL (Recommended)**

```bash
# Connect to PostgreSQL and drop/recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS nbcsw2_db;"
psql -U postgres -c "CREATE DATABASE nbcsw2_db;"

# Apply migrations
python3 manage.py migrate
```

**Option B: Using Django's migrate (if you want to keep the database)**

```bash
# This will apply all migrations from scratch
python3 manage.py migrate --run-syncdb
```

### Step 3: Create Superuser

```bash
python3 manage.py createsuperuser
```

### Step 4: Verify Models Match SERVER_STRUCTURE.md

The models have been enhanced beyond SERVER_STRUCTURE.md with:

#### Server Model Enhancements:
- ✅ All fields from SERVER_STRUCTURE.md
- ➕ `banner_url` - Server banner image
- ➕ `is_verified` - Verified server badge
- ➕ `settings` (JSONField) - Flexible server settings
- ➕ `features` (JSONField) - Enable/disable features dynamically
- ➕ `metadata` (JSONField) - Custom server data
- ➕ `max_members` - Configurable member limit
- ➕ `max_channels` - Configurable channel limit

#### CustomUser Model Enhancements:
- ✅ All standard Django user fields
- ➕ `avatar_url` - User avatar
- ➕ `bio` - User biography
- ➕ `user_settings` (JSONField) - User preferences
- ➕ `metadata` (JSONField) - Custom user data
- ➕ `per_game_stats` (JSONField) - Game statistics
- ➕ `status_message` - Custom status
- ➕ `is_online` - Online status
- ➕ `last_login_ip` - Last login IP address

### Step 5: Test the Setup

```bash
# Start the development server
python3 manage.py runserver

# In another terminal, test admin panel
# Visit: http://localhost:8000/admin/
```

## Model Structure Verification

### ✅ Server Model (matches SERVER_STRUCTURE.md)
- `name`, `slug`, `description` ✓
- `owner` (FK to User) ✓
- `icon`, `is_private` ✓
- `created_at`, `updated_at` ✓

### ✅ ServerRole Model (matches SERVER_STRUCTURE.md)
- `server` (FK to Server) ✓
- `name`, `color` ✓
- `permissions` (JSONField) ✓
- `position` ✓

### ✅ ServerMember Model (matches SERVER_STRUCTURE.md)
- `server` (FK to Server) ✓
- `user` (FK to User) ✓
- `roles` (ManyToMany to ServerRole) ✓
- `nickname`, `is_online` ✓
- `joined_at` ✓

### ✅ TextChannel Model (matches SERVER_STRUCTURE.md)
- `server` (FK to Server) ✓
- `name`, `slug`, `description` ✓
- `position`, `is_private` ✓
- `created_at` ✓

### ✅ VoiceChannel Model (matches SERVER_STRUCTURE.md)
- `server` (FK to Server) ✓
- `name`, `slug`, `description` ✓
- `position`, `user_limit` ✓
- `is_private`, `created_at` ✓

### ✅ ChatMessage Model (matches SERVER_STRUCTURE.md)
- `channel` (FK to TextChannel) ✓
- `user`, `content` ✓
- `created_at`, `edited_at` ✓

## Quick Reset Script

You can also use the provided script:

```bash
chmod +x reset_db.sh
./reset_db.sh
```

## Troubleshooting

### Migration Errors
If you encounter migration errors:
1. Check that all old migrations are deleted
2. Verify models.py has no syntax errors
3. Ensure database connection is working

### Database Connection Issues
Check your `.env` file or `settings.py` for:
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

## Next Steps After Reset

1. **Create initial data:**
   - Create a superuser
   - Create test servers via admin or views

2. **Test server creation:**
   - Visit `/create-server/`
   - Create a test server
   - Verify default roles are created

3. **Test channels:**
   - Create text and voice channels
   - Test permissions

4. **Test chat:**
   - Send messages in text channels
   - Verify WebSocket connections

## Notes

- All game algorithms remain unchanged
- GameSession model is preserved exactly as before
- The enhancements are backward-compatible
- JSON fields allow dynamic data without migrations

