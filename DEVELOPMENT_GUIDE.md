# Django Project Development Guide

## Project Overview
This is a Django 5.2.8 project with:
- **Django Channels** for WebSocket/real-time functionality
- **Custom User Model** (CustomUser with rank points)
- **Voice Channels** for voice chat rooms
- **Mini-Games System** with multiplayer game sessions
- **Real-time game sessions** with WebSocket support

## Recent Improvements Made

### 1. ✅ Created `requirements.txt`
   - Proper dependency management file created from the `req` file
   - Location: `python_version/requirements.txt`

### 2. ✅ Fixed AUTH_USER_MODEL Configuration
   - Added `AUTH_USER_MODEL = 'main.CustomUser'` to settings.py
   - Updated all model references to use `settings.AUTH_USER_MODEL` instead of direct `User` import
   - This ensures consistency across the project

### 3. ✅ Code Quality Improvements
   - Removed duplicate imports in models.py
   - Standardized user model references

## IDE Scale/UI Scaling in Cursor

### How to Adjust UI Scale in Cursor:

1. **Via Settings UI:**
   - Press `Ctrl+,` (or `Cmd+,` on Mac) to open Settings
   - Search for "zoom" or "scale"
   - Adjust "Window: Zoom Level" (default is 0, can be -5 to 5)

2. **Via Keyboard Shortcuts:**
   - `Ctrl++` or `Ctrl+=` to zoom in
   - `Ctrl+-` to zoom out
   - `Ctrl+0` to reset zoom

3. **Via Command Palette:**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "View: Zoom In" or "View: Zoom Out"

4. **Font Size Adjustment:**
   - Settings → Search "font size"
   - Adjust "Editor: Font Size" (default is usually 14)
   - You can also adjust "Terminal: Font Size" separately

5. **UI Scale (for High DPI Displays):**
   - Settings → Search "window zoom"
   - Adjust "Window: Zoom Level" for overall UI scaling

## Setup Instructions

### 1. Install Dependencies
```bash
cd python_version
pip install -r requirements.txt
```

### 2. Database Migrations
**Important:** Since we just added `AUTH_USER_MODEL`, you may need to handle migrations carefully:

If you have existing data:
```bash
# Backup your database first!
cp db.sqlite3 db.sqlite3.backup

# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

If starting fresh:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 3. Run Development Server
```bash
# For Django Channels, use daphne instead of runserver
daphne -b 0.0.0.0 -p 8000 python_version.asgi:application

# Or use the standard runserver (for HTTP only, no WebSocket)
python manage.py runserver
```

## Project Structure
```
python_version/
├── manage.py
├── requirements.txt          # ✅ Newly created
├── python_version/
│   ├── settings.py          # ✅ AUTH_USER_MODEL configured
│   ├── urls.py
│   └── asgi.py              # WebSocket configuration
├── main/
│   ├── models.py            # ✅ Updated to use AUTH_USER_MODEL
│   ├── views.py
│   ├── urls.py
│   ├── consumers.py         # WebSocket consumers
│   └── routing.py           # WebSocket routing
└── templates/
    └── [your templates]
```

## Key Features

### Custom User Model
- Extends `AbstractUser`
- Includes `rank_point` field for game ranking
- Configured as the default user model

### Game System
- `MiniGame`: Defines game types (name, min/max players)
- `GameSession`: Active game instances with board state
- Real-time updates via WebSockets

### Voice Channels
- `VoiceChannel`: Voice chat rooms
- `ChannelMember`: Tracks members in channels

## Next Steps for Development

1. **Test the Custom User Model:**
   - Create a superuser: `python manage.py createsuperuser`
   - Verify it uses CustomUser in admin panel

2. **Check WebSocket Functionality:**
   - Ensure consumers.py and routing.py are properly configured
   - Test real-time game updates

3. **Production Considerations:**
   - Move SECRET_KEY to environment variables
   - Set DEBUG = False for production
   - Configure proper CHANNEL_LAYERS (Redis recommended)
   - Set up proper ALLOWED_HOSTS

## Troubleshooting

### Issue: Migration errors after AUTH_USER_MODEL change
**Solution:** If you have existing data, you may need to:
1. Backup your database
2. Delete old migrations (if safe to do so)
3. Create fresh migrations
4. Or manually migrate the user model

### Issue: WebSocket not working
**Solution:** 
- Ensure you're using `daphne` to run the server
- Check that `CHANNEL_LAYERS` is configured in settings
- Verify `ASGI_APPLICATION` points to your asgi.py

## Useful Commands

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server (HTTP only)
python manage.py runserver

# Run with WebSocket support
daphne -b 0.0.0.0 -p 8000 python_version.asgi:application
```


