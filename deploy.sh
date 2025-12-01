#!/bin/bash
# Quick deployment script for Rashigo production

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] && [ ! -f "python_version/manage.py" ]; then
    echo "❌ Error: Not in project root directory"
    exit 1
fi

# Pull latest changes
echo "📥 Pulling latest changes from git..."
git pull origin development

# Check deployment method
if [ -f "docker-compose.yml" ]; then
    echo "🐳 Using Docker deployment..."
    
    # Rebuild and restart
    docker-compose down
    docker-compose up -d --build
    
    # Run migrations
    echo "🔄 Running migrations..."
    docker-compose exec -T web python manage.py migrate --noinput
    
    # Collect static files
    echo "📦 Collecting static files..."
    docker-compose exec -T web python manage.py collectstatic --noinput
    
    echo "✅ Docker deployment complete!"
    echo "📊 Checking service status..."
    docker-compose ps
    
else
    echo "⚙️  Using systemd deployment..."
    
    # Activate venv if exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Install dependencies
    echo "📦 Installing dependencies..."
    pip install -r requirements-prod.txt --quiet
    
    # Run migrations
    echo "🔄 Running migrations..."
    cd python_version
    python manage.py migrate --noinput
    
    # Collect static files
    echo "📦 Collecting static files..."
    python manage.py collectstatic --noinput
    
    # Restart services
    echo "🔄 Restarting services..."
    sudo systemctl restart rashigo
    sudo systemctl restart nginx
    
    echo "✅ Systemd deployment complete!"
    echo "📊 Checking service status..."
    sudo systemctl status rashigo --no-pager
fi

echo ""
echo "✨ Deployment finished successfully!"
echo "🌐 Check your site: https://rashigo.com/server/ilk-server/"

