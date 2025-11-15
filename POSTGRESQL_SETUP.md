# PostgreSQL Database Setup Guide

## Prerequisites

1. **Install PostgreSQL** (if not already installed):

   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   ```

   **macOS (using Homebrew):**
   ```bash
   brew install postgresql
   brew services start postgresql
   ```

   **Windows:**
   Download and install from: https://www.postgresql.org/download/windows/

2. **Install Python dependencies:**
   ```bash
   cd python_version
   source .venv/bin/activate  # or activate your virtual environment
   pip install -r requirements.txt
   ```

## Database Setup Steps

### 1. Create PostgreSQL Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# Or if you have a different setup, connect to PostgreSQL:
psql -U postgres
```

Then run these SQL commands:

```sql
-- Create database
CREATE DATABASE nbcsw2_db;

-- Create user (optional, you can use postgres user)
CREATE USER nbcsw2_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE nbcsw2_db TO nbcsw2_user;

-- Exit psql
\q
```

### 2. Create .env File

Create a `.env` file in the `python_version/` directory:

```bash
cd python_version
nano .env  # or use your preferred editor
```

Add the following content (adjust values as needed):

```env
# PostgreSQL Database Configuration
DB_NAME=nbcsw2_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Django Secret Key (generate a new one for production!)
SECRET_KEY=django-insecure-t+%**n55*%jp9@)kzegmo9f2u$_4gf6hx4e3sbmd1$%hargrfx

# Debug Mode (set to False in production)
DEBUG=True
```

**Important:** 
- Change `DB_PASSWORD` to your actual PostgreSQL password
- Change `DB_USER` if you created a custom user
- Generate a new `SECRET_KEY` for production (you can use: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)

### 3. Run Migrations

```bash
cd python_version
source .venv/bin/activate
python manage.py migrate
```

### 4. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 5. Test the Connection

```bash
python manage.py dbshell
```

If you can connect, you should see the PostgreSQL prompt. Type `\q` to exit.

## Troubleshooting

### Connection Error: "could not connect to server"

1. **Check if PostgreSQL is running:**
   ```bash
   sudo systemctl status postgresql  # Linux
   # or
   brew services list  # macOS
   ```

2. **Start PostgreSQL if not running:**
   ```bash
   sudo systemctl start postgresql  # Linux
   # or
   brew services start postgresql  # macOS
   ```

### Authentication Error: "password authentication failed"

1. Check your `.env` file has the correct password
2. Verify the user exists and has correct permissions:
   ```sql
   psql -U postgres
   \du  -- List all users
   ```

### Database Does Not Exist Error

Make sure you created the database:
```sql
psql -U postgres
CREATE DATABASE nbcsw2_db;
```

### Permission Denied Error

Grant proper permissions:
```sql
GRANT ALL PRIVILEGES ON DATABASE nbcsw2_db TO your_user;
```

## Production Considerations

1. **Use a strong password** for the database user
2. **Set DEBUG=False** in production
3. **Use environment variables** or a secrets manager (not .env file) in production
4. **Use SSL connections** for remote databases
5. **Regular backups** of your PostgreSQL database

## Useful PostgreSQL Commands

```bash
# Connect to database
psql -U postgres -d nbcsw2_db

# List all databases
psql -U postgres -c "\l"

# List all tables in current database
\dt

# Exit psql
\q
```

## Migration from SQLite to PostgreSQL

If you had data in SQLite that you want to migrate:

1. **Export data from SQLite:**
   ```bash
   python manage.py dumpdata > data.json
   ```

2. **After setting up PostgreSQL, import data:**
   ```bash
   python manage.py loaddata data.json
   ```

**Note:** This migration was already done - the database was recreated with PostgreSQL schema.

