#!/bin/bash
# Production Preparation Script
# This script helps prepare your code for production deployment

set -e  # Exit on error

echo "🚀 Rashigo Production Preparation"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
        return 0
    else
        echo -e "${RED}✗${NC} $1 missing"
        return 1
    fi
}

# Function to check if string is in file
check_in_file() {
    if grep -q "$2" "$1"; then
        echo -e "${RED}✗${NC} Found sensitive data in $1: $2"
        return 1
    else
        echo -e "${GREEN}✓${NC} No sensitive data found in $1"
        return 0
    fi
}

echo "📋 Checking files..."
echo ""

# Check .gitignore
check_file ".gitignore" || exit 1

# Check if .env is in .gitignore
if grep -q "^\.env$" .gitignore; then
    echo -e "${GREEN}✓${NC} .env is in .gitignore"
else
    echo -e "${RED}✗${NC} .env is NOT in .gitignore!"
    echo "  Add '.env' to .gitignore before proceeding"
    exit 1
fi

echo ""
echo "🔒 Checking for sensitive data in git..."
echo ""

# Check settings.py for hardcoded credentials
SETTINGS_FILE="python_version/python_version/settings.py"
if [ -f "$SETTINGS_FILE" ]; then
    # Check for hardcoded IPs (except localhost/127.0.0.1)
    if grep -E "['\"](stun|turn):[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" "$SETTINGS_FILE" | grep -v "127.0.0.1" | grep -v "localhost"; then
        echo -e "${YELLOW}⚠${NC}  Warning: Found hardcoded IP addresses in settings.py"
        echo "  Consider moving to environment variables"
    fi
    
    # Check for hardcoded passwords
    if grep -E "password|credential|secret" "$SETTINGS_FILE" | grep -E "=\s*['\"][^'\"]+['\"]" | grep -v "os.getenv" | grep -v "SECRET_KEY"; then
        echo -e "${YELLOW}⚠${NC}  Warning: Possible hardcoded credentials in settings.py"
    fi
fi

# Check if .env exists and is not tracked
if [ -f "python_version/.env" ]; then
    if git ls-files --error-unmatch "python_version/.env" 2>/dev/null; then
        echo -e "${RED}✗${NC} .env file is tracked by git!"
        echo "  Run: git rm --cached python_version/.env"
        exit 1
    else
        echo -e "${GREEN}✓${NC} .env exists and is not tracked by git"
    fi
else
    echo -e "${YELLOW}⚠${NC}  .env file doesn't exist yet"
    echo "  Create it from .env.example before deployment"
fi

echo ""
echo "📦 Checking dependencies..."
echo ""

# Check if requirements files exist
check_file "python_version/requirements.txt" || exit 1
check_file "python_version/requirements-prod.txt" || exit 1

echo ""
echo "🔍 Checking for common issues..."
echo ""

# Check DEBUG setting
if grep -q "DEBUG\s*=\s*True" "$SETTINGS_FILE"; then
    echo -e "${YELLOW}⚠${NC}  DEBUG is set to True in settings.py"
    echo "  Make sure to set DEBUG=False in your .env for production"
fi

# Check SECRET_KEY
if grep -q "SECRET_KEY\s*=\s*['\"]django-insecure" "$SETTINGS_FILE"; then
    echo -e "${YELLOW}⚠${NC}  Using default SECRET_KEY"
    echo "  Generate a new SECRET_KEY for production"
fi

# Check ALLOWED_HOSTS
if grep -q 'ALLOWED_HOSTS\s*=\s*\["\*"\]' "$SETTINGS_FILE"; then
    echo -e "${YELLOW}⚠${NC}  ALLOWED_HOSTS is set to ['*']"
    echo "  Restrict ALLOWED_HOSTS in production"
fi

echo ""
echo "📝 Git status check..."
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠${NC}  You have uncommitted changes"
    echo "  Commit your changes before deployment"
else
    echo -e "${GREEN}✓${NC} No uncommitted changes"
fi

# Check current branch
BRANCH=$(git branch --show-current)
echo -e "Current branch: ${GREEN}$BRANCH${NC}"

echo ""
echo "✅ Pre-deployment checks complete!"
echo ""
echo "📋 Next steps:"
echo "1. Create .env file from .env.example"
echo "2. Update .env with production values"
echo "3. Review DEPLOYMENT_CHECKLIST.md"
echo "4. Run: docker-compose up -d --build"
echo ""
echo "For detailed deployment instructions, see docs/DEPLOYMENT.md"
