#!/bin/bash
# Docker entrypoint script for G25 Telegram Bot
# Validates configuration before starting the bot

set -e

echo "=========================================="
echo "G25 Ancestry Telegram Bot - Startup"
echo "=========================================="

# Check for BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: BOT_TOKEN environment variable is not set!"
    echo "Please set BOT_TOKEN before starting the container."
    exit 1
fi

echo "✓ BOT_TOKEN is configured"

# Check for data files
ANCIENT_REF_PATH="${ANCIENT_REF_PATH:-/Data/Global25_PCA_scaled (Ancient Individuals).csv}"
MODERN_REF_PATH="${MODERN_REF_PATH:-/Data/Global25_PCA_modern_scaled.csv}"

if [ ! -f "$ANCIENT_REF_PATH" ]; then
    echo "ERROR: Ancient reference file not found: $ANCIENT_REF_PATH"
    exit 1
fi
echo "✓ Ancient reference file found: $ANCIENT_REF_PATH"

if [ ! -f "$MODERN_REF_PATH" ]; then
    echo "ERROR: Modern reference file not found: $MODERN_REF_PATH"
    exit 1
fi
echo "✓ Modern reference file found: $MODERN_REF_PATH"

# Create necessary directories
TEMP_DIR="${TEMP_DIR:-/app/temp}"
mkdir -p "$TEMP_DIR" /app/logs

echo "✓ Temporary directory: $TEMP_DIR"
echo "✓ Logs directory: /app/logs"

# Display configuration
echo ""
echo "Configuration:"
echo "  LOG_LEVEL: ${LOG_LEVEL:-INFO}"
echo "  Ancient ref: $ANCIENT_REF_PATH"
echo "  Modern ref: $MODERN_REF_PATH"
echo "  Temp dir: $TEMP_DIR"
echo ""

echo "Starting G25 Ancestry Telegram Bot..."
echo "=========================================="
echo ""

# Run the bot
exec python bot.py
