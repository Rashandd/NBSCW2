# Deployment Guide

Production deployment guide for Rashigo platform.

## Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Docker and Docker Compose (recommended)
- PostgreSQL 12+
- Redis 6+
- Python 3.10+
- Nginx (for production)

## Environment Setup

### 1. Environment Variables

Create `.env` file:

```bash
# Django
SECRET_KEY=your-secret-key-here-generate-new-one
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=nbcsw2_db
DB_USER=postgres
DB_PASSWORD=strong-password-here
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# COTURN
COTURN_HOST=turn.yourdomain.com
COTURN_PORT=3478
COTURN_USERNAME=username
COTURN_PASSWORD=password
```

### 2. Generate Secret Key

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

## Docker Deployment (Recommended)

### 1. Build and Start Services

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Initialize Database

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### 3. Configure Nginx

Create `/etc/nginx/sites-available/rashigo`:

```nginx
upstream rashigo {
    server web:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    client_max_body_size 100M;

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://rashigo;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://rashigo;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
ln -s /etc/nginx/sites-available/rashigo /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 4. SSL Certificate (Let's Encrypt)

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is configured automatically
```

## Manual Deployment

### 1. Install Dependencies

```bash
# System packages
apt-get update
apt-get install -y python3.10 python3-pip python3-venv postgresql redis-server nginx

# Create virtual environment
python3 -m venv /opt/rashigo/venv
source /opt/rashigo/venv/bin/activate

# Install Python packages
pip install -r requirements-prod.txt
```

### 2. Configure PostgreSQL

```bash
sudo -u postgres psql

CREATE DATABASE nbcsw2_db;
CREATE USER rashigo WITH PASSWORD 'your-password';
ALTER ROLE rashigo SET client_encoding TO 'utf8';
ALTER ROLE rashigo SET default_transaction_isolation TO 'read committed';
ALTER ROLE rashigo SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE nbcsw2_db TO rashigo;
\q
```

### 3. Configure Systemd Services

**Django (Daphne) Service** - `/etc/systemd/system/rashigo.service`:

```ini
[Unit]
Description=Rashigo Django Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=rashigo
Group=rashigo
WorkingDirectory=/opt/rashigo/python_version
Environment="PATH=/opt/rashigo/venv/bin"
ExecStart=/opt/rashigo/venv/bin/daphne -b 0.0.0.0 -p 8000 python_version.asgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Celery Worker** - `/etc/systemd/system/rashigo-celery.service`:

```ini
[Unit]
Description=Rashigo Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=rashigo
Group=rashigo
WorkingDirectory=/opt/rashigo/python_version
Environment="PATH=/opt/rashigo/venv/bin"
ExecStart=/opt/rashigo/venv/bin/celery -A python_version worker -l info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
systemctl daemon-reload
systemctl enable rashigo rashigo-celery
systemctl start rashigo rashigo-celery
systemctl status rashigo rashigo-celery
```

## Monitoring

### 1. Application Logs

```bash
# Docker
docker-compose logs -f web

# Systemd
journalctl -u rashigo -f
```

### 2. Health Checks

Add health check endpoint in `main/views.py`:

```python
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'healthy'})
```

### 3. Monitoring Tools

- **Sentry**: Error tracking (configure in settings.py)
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization

## Backup Strategy

### Database Backup

```bash
# Backup
docker-compose exec db pg_dump -U postgres nbcsw2_db > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T db psql -U postgres nbcsw2_db < backup_20250101.sql
```

### Media Files Backup

```bash
# Backup
tar -czf media_backup_$(date +%Y%m%d).tar.gz python_version/media/

# Restore
tar -xzf media_backup_20250101.tar.gz
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_memory_agent_type ON main_memorybank(agent_id, memory_type);
CREATE INDEX idx_workflow_active ON main_workflow(is_active, is_public);

-- Vacuum database
VACUUM ANALYZE;
```

### 2. Redis Configuration

Edit `/etc/redis/redis.conf`:
```
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 3. Gunicorn Workers

For production with Gunicorn instead of Daphne:
```bash
gunicorn python_version.wsgi:application \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

## Security Checklist

- [ ] Change SECRET_KEY to a strong random value
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS properly
- [ ] Enable SSL/TLS
- [ ] Set secure cookie flags
- [ ] Configure CORS properly
- [ ] Set up firewall (ufw/iptables)
- [ ] Regular security updates
- [ ] Database password is strong
- [ ] Redis is password protected
- [ ] Regular backups configured

## Scaling

### Horizontal Scaling

1. **Load Balancer**: Use Nginx or HAProxy
2. **Multiple Web Servers**: Run multiple web containers
3. **Separate Database**: Use managed PostgreSQL (AWS RDS, etc.)
4. **Redis Cluster**: For high availability

### Vertical Scaling

- Increase worker processes
- Allocate more memory to Redis
- Optimize database queries
- Use connection pooling

## Troubleshooting

**502 Bad Gateway**
- Check if web service is running
- Verify port configuration
- Check logs for errors

**Database Connection Failed**
- Verify PostgreSQL is running
- Check database credentials
- Ensure database exists

**WebSocket Not Working**
- Verify Nginx WebSocket configuration
- Check Redis connection
- Review channel layer settings

**Static Files Not Loading**
- Run `collectstatic` command
- Check Nginx static file configuration
- Verify file permissions
