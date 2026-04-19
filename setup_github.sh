#!/bin/bash
# OxQuant GitHub Setup Script

echo "=========================================="
echo "OxQuant GitHub Setup"
echo "=========================================="

# Check if repository exists
echo "Checking if GitHub repository exists..."
if curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/candy-frankie/OxQuant | grep -q "200"; then
    echo "✓ Repository exists on GitHub"
    REPO_EXISTS=true
else
    echo "⚠ Repository does not exist on GitHub"
    echo "You need to create it first:"
    echo "1. Go to https://github.com/new"
    echo "2. Repository name: OxQuant"
    echo "3. Description: Next-generation AI quantitative trading platform"
    echo "4. Choose Public or Private"
    echo "5. Do NOT initialize with README (we already have one)"
    echo "6. Click 'Create repository'"
    REPO_EXISTS=false
fi

echo ""
echo "=========================================="
echo "SSH Key Setup"
echo "=========================================="

# Check SSH key
if [ -f ~/.ssh/id_ed25519.pub ]; then
    echo "Your SSH public key:"
    cat ~/.ssh/id_ed25519.pub
    echo ""
    echo "To add this key to GitHub:"
    echo "1. Go to https://github.com/settings/keys"
    echo "2. Click 'New SSH key'"
    echo "3. Title: WSL or your computer name"
    echo "4. Paste the key above"
    echo "5. Click 'Add SSH key'"
else
    echo "No SSH key found. Generating one..."
    ssh-keygen -t ed25519 -C "644743502@qq.com" -f ~/.ssh/id_ed25519 -N ""
    echo "SSH key generated. Please add it to GitHub as above."
fi

echo ""
echo "=========================================="
echo "Git Configuration"
echo "=========================================="

# Set git config
git config --global user.name "candy-frankie"
git config --global user.email "644743502@qq.com"

echo "Git configured with:"
echo "  Name: candy-frankie"
echo "  Email: 644743502@qq.com"

echo ""
echo "=========================================="
echo "Push to GitHub"
echo "=========================================="

if [ "$REPO_EXISTS" = true ]; then
    echo "Attempting to push to GitHub..."
    git push -u origin main
    if [ $? -eq 0 ]; then
        echo "✓ Successfully pushed to GitHub!"
        echo "Repository URL: https://github.com/candy-frankie/OxQuant"
    else
        echo "✗ Failed to push. Make sure:"
        echo "  1. SSH key is added to GitHub"
        echo "  2. Repository exists"
        echo "  3. You have write permissions"
    fi
else
    echo "After creating the repository on GitHub, run:"
    echo ""
    echo "git remote add origin git@github.com:candy-frankie/OxQuant.git"
    echo "git push -u origin main"
fi

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo "1. Install dependencies:"
echo "   pip install -r requirements.txt"
echo "   or use Poetry: poetry install"
echo ""
echo "2. Start the development environment:"
echo "   docker-compose up -d postgres redis"
echo "   docker-compose up api"
echo ""
echo "3. Access API documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "4. Run Jupyter notebooks:"
echo "   docker-compose up jupyter"
echo "   http://localhost:8888 (password: oxquant)"