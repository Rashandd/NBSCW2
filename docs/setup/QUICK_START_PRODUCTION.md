# Quick Start - Production Deployment

## 🚨 IMPORTANT: Security Fixed!

Your COTURN credentials have been moved to environment variables. **You can now safely push to production.**

## What Was Fixed

✅ **Before** (INSECURE - hardcoded in settings.py):
```python
COTURN_CONFIG = {
    'ice_servers': [{
        'urls': ['stun:31.58.244.167:3478', 'turn:31.58.244.167:3478'],
        'username': 'adem',
        'credential': 'fb1907',  # ❌ EXPOSED IN GIT!
    }]
}
```

✅ **After** (SECURE - from environment variables):
```python
COTURN_HOST = os.getenv('COTURN_HOST', 'localhost')
COTURN_USERNAME = os.getenv('COTURN_USERNAME', '')
COTURN_PASSWORD = os.getenv('COTURN_PASSWORD', '')  # ✅ SAFE!
```

## 🚀 Deploy to Production (5 Steps)

### Step 1: Create .env File

```bash
cd python_version
cat > .env << 'EOF'
# Django
SECRET_KEY=GENERATE-A-NEW-SECRET-KEY-HERE
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=nbcsw2_db
DB_USER=postgres
DB_PASSWORD=your-strong-password
DB_HOST=db
DB_PORT=5432

# COTURN
COTURN_HOST=31.58.244.167
COTURN_PORT=3478
COTURN_USERNAME=adem
COTURN_PASSWORD=fb1907

# Redis
REDIS_URL=redis://redis:6379/0
EOF
```

**Generate a new SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 2: Run Pre-deployment Check

```bash
cd /home/adem/PycharmProjects/NBSCW2
./scripts/prepare_production.sh
```

This will check for:
- Sensitive data in git
- Missing files
- Common security issues

### Step 3: Deploy with Docker

```bash
# Build and start all services
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### Step 4: Verify Deployment

```bash
# Check if services are running
docker-compose ps

# Check logs
docker-compose logs -f web

# Test the application
curl http://localhost:8000
```

### Step 5: Push to Git

Now it's safe to push:

```bash
# Make sure .env is not tracked
git status

# Commit your changes
git add .
git commit -m "feat: move COTURN credentials to environment variables"

# Push to production
git push origin Production
```

## 📋 Production Checklist

Use this before every deployment:

```bash
# 1. Check for secrets
./scripts/check_secrets.sh

# 2. Run pre-deployment checks
./scripts/prepare_production.sh

# 3. Review checklist
cat DEPLOYMENT_CHECKLIST.md
```

## 🔒 Security Notes

### What's Protected Now

✅ COTURN credentials are in `.env` (not in git)
✅ `.env` is in `.gitignore`
✅ Settings.py uses `os.getenv()` for all secrets
✅ Public STUN servers as fallback

### Important Files

- **`.env`** - Contains secrets (NEVER commit!)
- **`.env.example`** - Template (safe to commit)
- **`.gitignore`** - Protects `.env` from git

### Verify .env is Not Tracked

```bash
# This should show nothing
git ls-files | grep "\.env$"

# If it shows .env, remove it:
git rm --cached python_version/.env
git commit -m "fix: remove .env from git"
```

## 🆘 Troubleshooting

### Voice Chat Not Working

1. **Check COTURN credentials in .env**
   ```bash
   cat python_version/.env | grep COTURN
   ```

2. **Test COTURN server**
   ```bash
   # From your server
   telnet 31.58.244.167 3478
   ```

3. **Check firewall**
   ```bash
   sudo ufw status
   # Port 3478 should be open
   ```

### Can't Push to Git

If you see "sensitive data" errors:

1. **Check what's being committed**
   ```bash
   git diff --cached
   ```

2. **Remove sensitive files**
   ```bash
   git reset HEAD python_version/.env
   ```

3. **Verify .gitignore**
   ```bash
   grep "\.env" .gitignore
   ```

## 📚 Additional Resources

- **Full Deployment Guide**: `docs/DEPLOYMENT.md`
- **Security Policy**: `SECURITY.md`
- **Deployment Checklist**: `DEPLOYMENT_CHECKLIST.md`
- **API Documentation**: `docs/API.md`

## 🎯 Quick Commands

```bash
# Start production
docker-compose up -d

# Stop production
docker-compose down

# View logs
docker-compose logs -f web

# Restart service
docker-compose restart web

# Run migrations
docker-compose exec web python manage.py migrate

# Create backup
docker-compose exec db pg_dump -U postgres nbcsw2_db > backup.sql
```

## ✅ You're Ready!

Your code is now secure and ready for production deployment. The COTURN credentials are safely stored in environment variables and will not be exposed in git.

**Next Steps:**
1. ✅ Review `DEPLOYMENT_CHECKLIST.md`
2. ✅ Create `.env` file with your production values
3. ✅ Run `./scripts/prepare_production.sh`
4. ✅ Deploy with `docker-compose up -d`
5. ✅ Push to git safely

Good luck with your deployment! 🚀
