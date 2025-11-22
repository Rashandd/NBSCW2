# Production Deployment Checklist

Before pushing to production, ensure all these items are completed.

## ✅ Security

- [ ] **SECRET_KEY** is set to a strong random value (not the default)
- [ ] **DEBUG** is set to `False`
- [ ] **ALLOWED_HOSTS** is properly configured with your domain
- [ ] **COTURN credentials** are in `.env` file (NOT in settings.py)
- [ ] **Database password** is strong and secure
- [ ] `.env` file is in `.gitignore` and NOT committed to git
- [ ] SSL/TLS certificates are configured
- [ ] Security headers are enabled (HSTS, CSP, etc.)

## ✅ Environment Variables

Create a `.env` file with these variables:

```bash
# Required
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=nbcsw2_db
DB_USER=postgres
DB_PASSWORD=strong-password
DB_HOST=db
DB_PORT=5432

# COTURN (for voice chat)
COTURN_HOST=31.58.244.167
COTURN_PORT=3478
COTURN_USERNAME=adem
COTURN_PASSWORD=fb1907

# Redis
REDIS_URL=redis://redis:6379/0
```

## ✅ Database

- [ ] PostgreSQL is installed and running
- [ ] Database is created
- [ ] Migrations are applied: `python manage.py migrate`
- [ ] Superuser is created: `python manage.py createsuperuser`
- [ ] Database backups are configured

## ✅ Static Files

- [ ] Static files collected: `python manage.py collectstatic`
- [ ] Nginx is configured to serve static files
- [ ] Media files directory is configured

## ✅ Services

- [ ] Daphne/Gunicorn is running
- [ ] Redis is running
- [ ] Celery worker is running (if using background tasks)
- [ ] Nginx is running and configured
- [ ] All services are set to start on boot

## ✅ WebSocket & Voice

- [ ] COTURN server is running and accessible
- [ ] WebSocket routing is configured in Nginx
- [ ] Firewall allows ports: 80, 443, 3478 (COTURN)
- [ ] Test voice chat functionality

## ✅ Monitoring & Logging

- [ ] Application logs are configured
- [ ] Error tracking (Sentry) is set up (optional)
- [ ] Server monitoring is configured
- [ ] Backup strategy is in place

## ✅ Testing

- [ ] All tests pass: `python manage.py test`
- [ ] Manual testing of key features
- [ ] Voice chat tested
- [ ] Game sessions tested
- [ ] API endpoints tested

## ✅ Git & Deployment

- [ ] All changes are committed
- [ ] `.env` is NOT in git (check with `git status`)
- [ ] Sensitive data is removed from git history
- [ ] Production branch is up to date

## 🚀 Deployment Commands

### Using Docker (Recommended)

```bash
# 1. Copy environment file
cp .env.production.example .env
# Edit .env with your actual values

# 2. Build and start services
docker-compose up -d --build

# 3. Run migrations
docker-compose exec web python manage.py migrate

# 4. Create superuser
docker-compose exec web python manage.py createsuperuser

# 5. Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# 6. Check logs
docker-compose logs -f web
```

### Manual Deployment

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements-prod.txt

# 3. Set environment variables
export $(cat .env | xargs)

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Start services
systemctl start rashigo
systemctl start rashigo-celery
systemctl start nginx
```

## 🔒 Security Best Practices

1. **Never commit sensitive data**
   - Use `.env` for all secrets
   - Add `.env` to `.gitignore`
   - Use `.env.example` for documentation

2. **Rotate credentials regularly**
   - Change SECRET_KEY periodically
   - Update database passwords
   - Rotate API keys

3. **Monitor for security issues**
   - Keep dependencies updated
   - Monitor security advisories
   - Run security scans

4. **Backup regularly**
   - Database backups daily
   - Media files backups weekly
   - Test restore procedures

## 📝 Post-Deployment

- [ ] Test all major features
- [ ] Monitor error logs for 24 hours
- [ ] Check performance metrics
- [ ] Verify SSL certificate is working
- [ ] Test from different devices/networks
- [ ] Document any issues encountered

## 🆘 Rollback Plan

If something goes wrong:

```bash
# Docker
docker-compose down
git checkout previous-working-commit
docker-compose up -d

# Manual
systemctl stop rashigo
git checkout previous-working-commit
systemctl start rashigo
```

## 📞 Support

If you encounter issues:
1. Check logs: `docker-compose logs web` or `journalctl -u rashigo`
2. Review this checklist
3. Check documentation in `docs/DEPLOYMENT.md`
4. Open an issue on GitHub
