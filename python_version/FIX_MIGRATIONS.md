# Fix "No migrations to apply" Issue

## Problem
After creating fresh migrations, `python manage.py migrate` says "No migrations to apply" even though migrations were just created.

## Why This Happens
This occurs when:
1. The database tables already exist (from previous migrations)
2. The `django_migrations` table shows migrations as already applied
3. There's a mismatch between migration state and actual database

## Solutions

### Option 1: Check if Tables Already Exist (Recommended First Step)

```bash
# Connect to PostgreSQL and check if tables exist
psql -U postgres -d nbcsw2_db -c "\dt main_*"
```

If tables exist, you have two choices:

### Option 2A: Fake the Initial Migration (If Tables Match Models)

If your existing tables match your new models:

```bash
python manage.py migrate --fake-initial main
```

This marks the migration as applied without actually running it.

### Option 2B: Reset Database Completely (If Starting Fresh)

**⚠️ WARNING: This will DELETE ALL DATA!**

```bash
# Drop and recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS nbcsw2_db;"
psql -U postgres -c "CREATE DATABASE nbcsw2_db;"

# Then run migrations
python manage.py migrate
```

### Option 3: Check Migration State

```bash
# See which migrations Django thinks are applied
python manage.py showmigrations main

# Check the django_migrations table directly
psql -U postgres -d nbcsw2_db -c "SELECT * FROM django_migrations WHERE app = 'main';"
```

### Option 4: Manual Migration State Fix

If tables exist but migration state is wrong:

```bash
# 1. Check what's in django_migrations
psql -U postgres -d nbcsw2_db -c "SELECT * FROM django_migrations WHERE app = 'main';"

# 2. If empty or wrong, you can manually insert:
# (But this is risky - better to use --fake-initial)

# 3. Or delete all main migrations from django_migrations and re-run:
psql -U postgres -d nbcsw2_db -c "DELETE FROM django_migrations WHERE app = 'main';"
python manage.py migrate --fake-initial main
```

## Recommended Approach

1. **First, check if tables exist:**
   ```bash
   psql -U postgres -d nbcsw2_db -c "\dt main_*"
   ```

2. **If tables exist and match your models:**
   ```bash
   python manage.py migrate --fake-initial main
   ```

3. **If tables don't exist or you want fresh start:**
   ```bash
   # Backup first if needed!
   pg_dump -U postgres nbcsw2_db > backup.sql
   
   # Drop and recreate
   psql -U postgres -c "DROP DATABASE IF EXISTS nbcsw2_db;"
   psql -U postgres -c "CREATE DATABASE nbcsw2_db;"
   
   # Run migrations
   python manage.py migrate
   ```

4. **Verify migrations applied:**
   ```bash
   python manage.py showmigrations main
   ```

## Quick Diagnostic Commands

```bash
# Check migration status
python manage.py showmigrations

# Check what would be applied
python manage.py migrate --plan

# Check database tables
psql -U postgres -d nbcsw2_db -c "\dt"

# Check django_migrations table
psql -U postgres -d nbcsw2_db -c "SELECT app, name, applied FROM django_migrations WHERE app = 'main' ORDER BY applied;"
```

