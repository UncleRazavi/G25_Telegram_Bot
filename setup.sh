#!/bin/bash
# Quick setup script for Linux and macOS users
# This script sets up the G25 Telegram Bot for local development

set -e

echo ""
echo "=========================================="
echo "G25 Telegram Bot - Linux/macOS Setup"
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9+ from https://www.python.org/"
    exit 1
fi

echo "[OK] Python found"
python3 --version

# Create virtual environment
if [ ! -d venv ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "[OK] Virtual environment created"
else
    echo "[OK] Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
echo "[OK] Virtual environment activated"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt -q
echo "[OK] Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cp .env.example .env
    echo "[OK] .env file created"
    echo ""
    echo "!!! IMPORTANT !!!"
    echo "Please edit .env and add your BOT_TOKEN"
    echo "Get your token from @BotFather on Telegram"
    echo ""
else
    echo "[OK] .env file already exists"
fi

# Create necessary directories
mkdir -p logs
echo "[OK] Created logs directory"

mkdir -p temp
echo "[OK] Created temp directory"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your BOT_TOKEN"
echo "  2. Run: python bot.py"
echo ""
echo "For Docker:"
echo "  docker-compose up -d"
echo ""
echo "For more info, see:"
echo "  - DOCKER_README.md"
echo "  - DEPLOYMENT_GUIDE.md"
echo ""
