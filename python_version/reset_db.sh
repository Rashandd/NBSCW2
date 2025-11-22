#!/bin/bash
# Database Reset Script
# This script resets the database and creates fresh migrations

cd "$(dirname "$0")"

echo "🔄 Resetting database and creating fresh migrations..."

# Step 1: Create fresh migrations
echo "📝 Creating fresh migrations..."
python3 manage.py makemigrations

if [ $? -ne 0 ]; then
    echo "❌ Error creating migrations!"
    exit 1
fi

# Step 2: Show migration plan
echo ""
echo "📋 Migration plan:"
python3 manage.py showmigrations

# Step 3: Reset database (WARNING: This will delete all data!)
echo ""
read -p "⚠️  This will DELETE ALL DATA. Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled."
    exit 0
fi

# Step 4: Drop all tables and recreate
echo "🗑️  Dropping all tables..."
python3 manage.py migrate --run-syncdb

# Step 5: Apply all migrations
echo "✅ Applying migrations..."
python3 manage.py migrate

echo ""
echo "✨ Database reset complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Create a superuser: python3 manage.py createsuperuser"
echo "   2. Run the server: python3 manage.py runserver"

