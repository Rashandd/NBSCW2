# Documentation

Complete documentation for the Rashigo platform.

## Table of Contents

### Getting Started
- [Main README](../README.md) - Project overview and quick start
- [Development Guide](../DEVELOPMENT_GUIDE.md) - Development setup and workflow
- [Contributing](../CONTRIBUTING.md) - Contribution guidelines
- [Code of Conduct](../CODE_OF_CONDUCT.md) - Community standards

### Core Features
- [AI Agents & Memory Bank](AI_AGENTS.md) - AI agent system, memory bank, and workflows
- [Gaming Platform](GAMING.md) - Game development and multiplayer features
- [Communication System](COMMUNICATION.md) - Discord-like chat and voice features

### Technical Documentation
- [API Reference](API.md) - REST API endpoints and usage
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [PostgreSQL Setup](../POSTGRESQL_SETUP.md) - Database configuration
- [Server Structure](../SERVER_STRUCTURE.md) - Server and channel architecture

### Examples
- [Example Workflows](../examples/workflows/) - Workflow configuration examples
- [Example Agents](../examples/agents/) - AI agent configuration examples
- [Examples README](../examples/README.md) - How to use examples

## Quick Links

### For Developers
- [Setting up development environment](../DEVELOPMENT_GUIDE.md#setup)
- [Running tests](../CONTRIBUTING.md#testing)
- [Code style guide](../CONTRIBUTING.md#style-guides)
- [Creating custom agents](AI_AGENTS.md#custom-agent-implementation)

### For Deployers
- [Docker deployment](DEPLOYMENT.md#docker-deployment-recommended)
- [Manual deployment](DEPLOYMENT.md#manual-deployment)
- [Environment configuration](DEPLOYMENT.md#environment-setup)
- [Security checklist](DEPLOYMENT.md#security-checklist)

### For API Users
- [Authentication](API.md#authentication)
- [Agent endpoints](API.md#agents)
- [Memory bank endpoints](API.md#memory-bank)
- [Workflow endpoints](API.md#workflows)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Rashigo Platform                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Gaming     │  │ Communication│  │  AI Agents   │ │
│  │   Platform   │  │    System    │  │  & Memory    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                         │                                │
│              ┌──────────▼──────────┐                    │
│              │   Django Backend    │                    │
│              │  - REST API         │                    │
│              │  - WebSockets       │                    │
│              │  - Business Logic   │                    │
│              └──────────┬──────────┘                    │
│                         │                                │
│         ┌───────────────┼───────────────┐               │
│         │               │               │               │
│  ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐       │
│  │ PostgreSQL  │ │   Redis   │ │   COTURN    │       │
│  │  Database   │ │  Cache &  │ │  WebRTC     │       │
│  │             │ │  Channels │ │   Server    │       │
│  └─────────────┘ └───────────┘ └─────────────┘       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Technology Stack

- **Backend**: Django 5.2+, Django Channels
- **Database**: PostgreSQL 12+
- **Cache/Channels**: Redis 6+
- **WebSockets**: Daphne/Channels
- **Voice**: WebRTC with COTURN
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx (production)

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/NBSCW2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/NBSCW2/discussions)
- **Documentation**: This directory

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to the project.

## License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) for details.
