-- Fix PostgreSQL 15+ Permission Issue
-- Run this script to fix the "permission denied for schema public" error

-- Connect to your database as postgres superuser first:
-- sudo -u postgres psql

-- Then connect to your database
\c nbcsw2_db

-- Grant schema privileges (REQUIRED for PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO nbcsw2_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nbcsw2_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO nbcsw2_user;

-- If you're using the postgres user directly, run these instead:
-- GRANT ALL ON SCHEMA public TO postgres;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;

-- Verify permissions (optional check)
\dn+

