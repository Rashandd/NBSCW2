#!/bin/bash
# Script to check database state and fix migration issues

echo "🔍 Checking database state..."

# Check if tables exist
echo ""
echo "📊 Checking if main_* tables exist in database..."
psql -U postgres -d nbcsw2_db -c "\dt main_*" 2>/dev/null

if [ $? -eq 0 ]; then
    TABLE_COUNT=$(psql -U postgres -d nbcsw2_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'main_%';" 2>/dev/null | tr -d ' ')
    
    if [ "$TABLE_COUNT" -gt 0 ]; then
        echo ""
        echo "✅ Found $TABLE_COUNT main_* tables in database"
        echo ""
        echo "📋 Checking migration state..."
        python manage.py showmigrations main
        
        echo ""
        echo "💡 Solution: Use --fake-initial to mark migrations as applied"
        echo "   Command: python manage.py migrate --fake-initial main"
        echo ""
        read -p "Do you want to fake the initial migration? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            python manage.py migrate --fake-initial main
            echo "✅ Done! Verifying..."
            python manage.py showmigrations main
        fi
    else
        echo ""
        echo "❌ No main_* tables found. Running migrations normally..."
        python manage.py migrate
    fi
else
    echo ""
    echo "⚠️  Could not connect to database. Check your database settings."
    echo "   Database: nbcsw2_db"
    echo "   User: postgres"
fi

echo ""
echo "📋 Final migration status:"
python manage.py showmigrations main

