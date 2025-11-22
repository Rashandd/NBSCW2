# Project Structure

This document describes the organization and structure of the Rashigo project.

## Directory Layout

```
NBSCW2/
├── docs/                          # Project documentation
│   ├── setup/                     # Setup and installation guides
│   │   ├── POSTGRESQL_SETUP.md
│   │   └── QUICK_START_PRODUCTION.md
│   ├── features/                  # Feature-specific documentation
│   │   ├── SERVER_STRUCTURE.md
│   │   └── DISCORD_INTEGRATION.md
│   ├── AI_AGENTS.md              # AI agent system documentation
│   ├── API.md                    # REST API reference
│   ├── COMMUNICATION.md          # Communication features
│   ├── DEPLOYMENT.md             # Deployment guide
│   ├── GAMING.md                 # Gaming platform documentation
│   ├── PROJECT_STRUCTURE.md      # This file
│   └── README.md                 # Documentation index
│
├── examples/                      # Example configurations
│   ├── agents/                   # AI agent examples
│   │   ├── community_helper.json
│   │   ├── cursor_assistant.json
│   │   └── game_moderator.json
│   └── workflows/                # Workflow examples
│       ├── code_review_assistant.json
│       ├── greet_user.json
│       └── task_tracker.json
│
├── python_version/               # Main Django application
│   ├── main/                     # Main Django app
│   │   ├── agents/               # AI agent implementations
│   │   │   ├── base_agent.py
│   │   │   └── __init__.py
│   │   ├── api/                  # REST API endpoints
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── __init__.py
│   │   ├── integrations/         # External integrations
│   │   │   ├── cursor_memory.py
│   │   │   └── __init__.py
│   │   ├── management/           # Django management commands
│   │   │   └── commands/
│   │   │       └── cleanup_stale_games.py
│   │   ├── migrations/           # Database migrations
│   │   ├── services/             # Business logic services
│   │   │   ├── ai_agent_service.py
│   │   │   ├── memory_bank_service.py
│   │   │   ├── workflow_service.py
│   │   │   └── __init__.py
│   │   ├── templatetags/         # Custom template tags
│   │   ├── admin.py              # Django admin configuration
│   │   ├── consumers.py           # WebSocket consumers
│   │   ├── middleware.py         # Custom middleware
│   │   ├── models.py             # Database models
│   │   ├── routing.py            # WebSocket routing
│   │   ├── urls.py               # URL routing
│   │   └── views.py              # View functions
│   │
│   ├── python_version/           # Django project settings
│   │   ├── asgi.py               # ASGI configuration
│   │   ├── settings.py           # Django settings
│   │   ├── urls.py               # Root URL configuration
│   │   └── wsgi.py               # WSGI configuration
│   │
│   ├── locale/                   # Internationalization files
│   │   ├── en/                   # English translations
│   │   ├── tr/                   # Turkish translations
│   │   ├── es/                   # Spanish translations
│   │   ├── fr/                   # French translations
│   │   └── de/                   # German translations
│   │
│   ├── static/                   # Static files (CSS, JS, images)
│   │   └── js/
│   │
│   ├── templates/                # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── game_room.html
│   │   ├── lobby.html
│   │   └── ...
│   │
│   ├── requirements.txt          # Base dependencies
│   ├── requirements-dev.txt      # Development dependencies
│   ├── requirements-prod.txt     # Production dependencies
│   ├── requirements-test.txt     # Testing dependencies
│   └── manage.py                # Django management script
│
├── scripts/                      # Utility scripts
│   ├── check_secrets.sh
│   └── prepare_production.sh
│
├── .gitignore                    # Git ignore rules
├── CHANGELOG.md                  # Project changelog
├── CODE_OF_CONDUCT.md            # Code of conduct
├── CONTRIBUTING.md               # Contribution guidelines
├── DEPLOYMENT_CHECKLIST.md       # Deployment checklist
├── DEVELOPMENT_GUIDE.md         # Development guide
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Docker image definition
├── LICENSE                       # License file
├── README.md                     # Main project README
└── SECURITY.md                   # Security guidelines
```

## Key Directories

### `python_version/`
The main Django application directory. Contains all application code, settings, templates, and static files.

### `python_version/main/`
The main Django app containing:
- **Models**: Database models for users, servers, channels, games, AI agents, etc.
- **Views**: HTTP request handlers
- **API**: REST API endpoints
- **Consumers**: WebSocket handlers for real-time features
- **Services**: Business logic layer
- **Agents**: AI agent implementations
- **Integrations**: External service integrations

### `docs/`
Documentation organized by category:
- **setup/**: Installation and setup guides
- **features/**: Feature-specific documentation
- Core documentation files for API, deployment, etc.

### `examples/`
Example configuration files for:
- AI agents
- Workflows
- Useful for understanding how to configure the system

## File Naming Conventions

- **Python files**: `snake_case.py`
- **Django apps**: `lowercase`
- **Models**: `PascalCase` classes
- **Templates**: `snake_case.html`
- **Static files**: `kebab-case` for CSS/JS, `snake_case` for images

## Generated Files (Not in Version Control)

The following directories/files are generated and should not be committed:
- `python_version/staticfiles/` - Generated by `collectstatic`
- `python_version/media/` - User-uploaded media files
- `python_version/__pycache__/` - Python bytecode cache
- `python_version/locale/*/LC_MESSAGES/*.mo` - Compiled translation files
- `*.pyc`, `*.pyo` - Compiled Python files

## Database Migrations

Migrations are stored in `python_version/main/migrations/`. Always commit migration files, but never edit them manually. Create new migrations using:

```bash
python manage.py makemigrations
```

## Static Files

Static files are collected to `python_version/staticfiles/` in production using:

```bash
python manage.py collectstatic
```

This directory is generated and should not be committed to version control.

## Environment Configuration

Environment-specific settings should be stored in `.env` files (not committed). See `.env.example` for required variables.

## Testing

Tests should be placed in:
- `python_version/main/tests.py` (basic tests)
- `python_version/main/tests/` (for more complex test suites)

Run tests with:
```bash
pytest
# or
python manage.py test
```

