#!/bin/bash
# Check for accidentally committed secrets
# Run this before pushing to production

echo "🔍 Checking for secrets in git history..."
echo ""

# Check for common secret patterns
echo "Checking for passwords..."
git log -p | grep -i "password\s*=" | grep -v "DB_PASSWORD" | grep -v "os.getenv" | head -5

echo ""
echo "Checking for API keys..."
git log -p | grep -i "api[_-]key" | grep -v "os.getenv" | head -5

echo ""
echo "Checking for secret keys..."
git log -p | grep "SECRET_KEY\s*=" | grep -v "os.getenv" | head -5

echo ""
echo "Checking for COTURN credentials..."
git log -p | grep -E "(COTURN|coturn)" | grep -E "(username|password|credential)" | head -10

echo ""
echo "✅ Check complete!"
echo ""
echo "If you found any secrets above:"
echo "1. Remove them from git history"
echo "2. Rotate the compromised credentials"
echo "3. Use environment variables instead"
echo ""
echo "To remove secrets from git history:"
echo "  git filter-branch --force --index-filter \\"
echo "    'git rm --cached --ignore-unmatch path/to/file' \\"
echo "    --prune-empty --tag-name-filter cat -- --all"
