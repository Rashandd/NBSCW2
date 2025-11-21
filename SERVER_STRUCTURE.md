# Server-Based Structure

## ✅ Changes Made

### Models Created

1. **Server** - Main server/community container
   - `name`, `slug`, `description`
   - `owner` (user who created it)
   - `icon`, `is_private`
   - `created_at`, `updated_at`

2. **ServerRole** - Roles within servers
   - `server` (FK to Server)
   - `name`, `color` (hex color)
   - `permissions` (JSONField for permission flags)
   - `position` (for ordering)

3. **ServerMember** - Users in servers with roles
   - `server` (FK to Server)
   - `user` (FK to User)
   - `roles` (ManyToMany to ServerRole)
   - `nickname`, `is_online`
   - `joined_at`

4. **TextChannel** - Text channels for chat messages
   - `server` (FK to Server)
   - `name`, `slug`, `description`
   - `position`, `is_private`
   - `created_at`

5. **VoiceChannel** - Voice channels for voice communication
   - `server` (FK to Server)
   - `name`, `slug`, `description`
   - `position`, `user_limit`
   - `is_private`, `created_at`

6. **ChatMessage** - Messages in text channels (updated)
   - `channel` (FK to TextChannel, not VoiceChannel)
   - `user`, `content`
   - `created_at`, `edited_at`

### Templates Updated

1. **index.html** - Now extends `base.html` and shows servers
   - Uses Bootstrap (from base.html)
   - Displays server cards with member counts
   - Shows text and voice channel counts

2. **login.html** - Now extends `base.html`
   - Uses Bootstrap styling
   - Integrated with Django auth

### Views Created

1. **index()** - Shows user's servers (member or owner)
   - Returns servers user belongs to
   - Includes dummy servers if DB is empty

2. **server_view()** - View a server with channels
   - Shows text and voice channels
   - Displays members and roles
   - Checks permissions

3. **channel_view()** - View a text channel
   - Shows chat messages
   - Server-specific channel view

### URLs Added

- `/server/<slug>/` - View server
- `/server/<server_slug>/channel/<channel_slug>/` - View text channel

## Structure

```
Server (e.g., "Gaming Hub")
  ├── Text Channels
  │   ├── #general
  │   ├── #announcements
  │   └── #random
  ├── Voice Channels
  │   ├── 🔊 General
  │   ├── 🔊 Gaming
  │   └── 🔊 Music
  ├── Roles
  │   ├── Owner (Admin)
  │   ├── Moderator
  │   └── Member
  └── Members
      ├── User1 (roles: Owner)
      ├── User2 (roles: Moderator)
      └── User3 (roles: Member)
```

## Next Steps

1. **Create migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Create templates:**
   - `server_view.html` - Server page with channels sidebar
   - `channel_view.html` - Text channel with chat

3. **Update consumers:**
   - Update WebSocket consumer to work with TextChannel instead of VoiceChannel
   - Add server-based routing

4. **Admin panel:**
   - Register new models in admin.py
   - Set up admin interface for servers, roles, channels

