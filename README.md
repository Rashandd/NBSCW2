# Rashigo - AI-Powered Gaming & Communication Platform

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.2+-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A comprehensive Django-based platform combining real-time gaming, Discord-like communication, and AI agent capabilities with workflow automation and memory bank features.

## 🌟 Features

### Gaming Platform
- 🎮 **Multi-Game Support**: Dice Wars and extensible mini-game framework
- 🏆 **Leaderboards & Rankings**: Track player statistics and achievements
- 🎯 **Real-time Gameplay**: WebSocket-powered live game sessions
- 👥 **Matchmaking**: Public and private game rooms

### Communication
- 💬 **Discord-like Interface**: Text and voice channels
- 🔊 **Voice Chat**: WebRTC-powered voice communication with COTURN support
- 📱 **Server System**: Create and manage community servers
- 👤 **User Profiles**: Customizable profiles with roles and permissions

### AI Agent System
- 🤖 **AI Agents**: Configurable AI agents with multiple types (assistant, workflow automation, conversational)
- 🧠 **Memory Bank**: Persistent memory storage with semantic search capabilities
- ⚙️ **Workflow Repository**: Define and execute automated workflows
- 🔗 **Cursor Integration**: Specialized memory bank for Cursor AI interactions
- 📊 **Context Management**: Build comprehensive context for AI queries

### Technical Features
- 🌐 **Multi-language Support**: English, Turkish, Spanish, French, German
- 🔐 **Authentication System**: Secure user management
- 📡 **WebSocket Support**: Real-time communication via Django Channels
- 🗄️ **PostgreSQL Database**: Robust data storage
- 🎨 **Modern UI**: Responsive design with Discord-inspired interface

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Redis (for production channel layers)
- Node.js (optional, for frontend development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/NBSCW2.git
   cd NBSCW2
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   cd python_version
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Setup database**
   ```bash
   # Create PostgreSQL database
   createdb nbcsw2_db
   
   # Run migrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   # For WebSocket support
   daphne -b 0.0.0.0 -p 8000 python_version.asgi:application
   
   # Or standard Django server (no WebSocket)
   python manage.py runserver
   ```

8. **Access the application**
   - Main site: http://localhost:8000
   - Admin panel: http://localhost:8000/admin
   - API: http://localhost:8000/api/

## 📖 Documentation

### Core Documentation
- [Development Guide](DEVELOPMENT_GUIDE.md) - Setup and development workflow
- [AI Agents & Memory Bank](docs/AI_AGENTS.md) - AI agent system guide
- [API Documentation](docs/API.md) - REST API reference
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment
- [Gaming Platform](docs/GAMING.md) - Game development guide
- [Communication System](docs/COMMUNICATION.md) - Chat and voice features
- [PostgreSQL Setup](POSTGRESQL_SETUP.md) - Database configuration
- [Server Structure](SERVER_STRUCTURE.md) - Server and channel system

### API Documentation

#### AI Agent API

**List Agents**
```bash
GET /api/agents/
```

**Get Agent Details**
```bash
GET /api/agents/{agent_slug}/
```

**Store Memory**
```bash
POST /api/agents/{agent_slug}/memory/
Content-Type: application/json

{
  "type": "conversation",
  "user_message": "How do I implement a feature?",
  "agent_response": "Here's how...",
  "tags": ["development", "help"]
}
```

**Search Memories**
```bash
GET /api/agents/{agent_slug}/memory/search/?type=conversation&q=feature&limit=10
```

**Get Context**
```bash
GET /api/agents/{agent_slug}/context/?q=current+task
```

**Execute Workflow**
```bash
POST /api/agents/{agent_slug}/workflows/{workflow_slug}/execute/
Content-Type: application/json

{
  "input": {
    "param1": "value1"
  }
}
```

## 🏗️ Project Structure

```
NBSCW2/
├── python_version/
│   ├── main/                      # Main Django app
│   │   ├── agents/                # AI agent implementations
│   │   │   ├── base_agent.py      # Base AI agent class
│   │   │   └── __init__.py
│   │   ├── api/                   # REST API endpoints
│   │   │   ├── views.py           # API views
│   │   │   ├── urls.py            # API URL routing
│   │   │   └── __init__.py
│   │   ├── integrations/          # External integrations
│   │   │   ├── cursor_memory.py   # Cursor AI memory bank
│   │   │   └── __init__.py
│   │   ├── management/            # Django management commands
│   │   │   └── commands/
│   │   │       └── cleanup_stale_games.py
│   │   ├── migrations/            # Database migrations
│   │   ├── services/              # Business logic services
│   │   │   ├── ai_agent_service.py
│   │   │   ├── memory_bank_service.py
│   │   │   ├── workflow_service.py
│   │   │   └── __init__.py
│   │   ├── templatetags/          # Custom template tags
│   │   ├── admin.py               # Admin interface
│   │   ├── consumers.py           # WebSocket consumers
│   │   ├── middleware.py          # Custom middleware
│   │   ├── models.py              # Database models
│   │   ├── routing.py             # WebSocket routing
│   │   ├── urls.py                # URL routing
│   │   └── views.py               # View functions
│   ├── python_version/            # Project settings
│   │   ├── asgi.py                # ASGI configuration
│   │   ├── settings.py            # Django settings
│   │   ├── urls.py                # Root URL configuration
│   │   └── wsgi.py                # WSGI configuration
│   ├── static/                    # Static files
│   ├── templates/                 # HTML templates
│   ├── locale/                    # Translations
│   ├── manage.py                  # Django management script
│   └── requirements.txt           # Python dependencies
├── .gitignore                     # Git ignore rules
├── README.md                      # This file
└── LICENSE                        # License file
```

## 🗃️ Database Models

### Core Models
- **CustomUser**: Extended user model with gaming statistics
- **Server**: Discord-like servers
- **ServerRole**: Role-based permissions
- **ServerMember**: Server membership
- **TextChannel**: Text communication channels
- **VoiceChannel**: Voice communication channels
- **ChatMessage**: Stored chat messages

### Gaming Models
- **MiniGame**: Game definitions
- **GameSession**: Active game sessions

### AI Models
- **AIAgent**: AI agent configurations
- **Workflow**: Workflow definitions
- **WorkflowExecution**: Workflow execution tracking
- **MemoryBank**: AI memory storage

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `python_version` directory:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=nbcsw2_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# COTURN (WebRTC)
COTURN_HOST=your-coturn-server
COTURN_PORT=3478
COTURN_USERNAME=username
COTURN_PASSWORD=password
```

### WebSocket Configuration

For production, use Redis as the channel layer:

```python
# settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test main

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 🚢 Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure proper `SECRET_KEY`
- [ ] Set up PostgreSQL database
- [ ] Configure Redis for channel layers
- [ ] Set up COTURN server for WebRTC
- [ ] Configure static files serving
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS and CSRF settings
- [ ] Set up logging and monitoring
- [ ] Configure backup strategy

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where applicable
- Write docstrings for all public methods
- Add tests for new features

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Adem** - *Initial work*

## 🙏 Acknowledgments

- Django and Django Channels teams
- WebRTC and COTURN communities
- All contributors and users

## 📞 Support

- **Documentation**: See the `/docs` directory
- **Issues**: [GitHub Issues](https://github.com/yourusername/NBSCW2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/NBSCW2/discussions)

## 🗺️ Roadmap

- [ ] Enhanced AI agent capabilities
- [ ] More mini-games
- [ ] Mobile app support
- [ ] Advanced analytics dashboard
- [ ] Plugin system for extensions
- [ ] Improved voice quality and features
- [ ] AI-powered game recommendations
- [ ] Tournament system

---

Made with ❤️ by the Rashigo team
