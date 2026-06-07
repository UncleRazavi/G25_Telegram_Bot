# G25 Ancestry Telegram Bot - Docker Guide

## Overview

This is an enhanced version of the G25 Ancestry Telegram Bot with Docker support and improved project structure. The bot performs ancestry analysis using G25 datasets via Telegram.

## Features

- **NNLS Analysis**: Decompose ancestry using ancient populations
- **Closest Finder**: Find most similar populations to your sample
- **PCA Visualization**: Project samples onto modern population PCA space
- **Population Search**: Search and suggest ancient populations by name
- **Comprehensive Logging**: Track all operations with detailed logs
- **Environment Configuration**: Flexible configuration via .env file
- **Error Handling**: Robust error handling and user-friendly messages

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- Telegram Bot Token (get from @BotFather on Telegram)
- Data files in `Data/` directory

### 1. Setup Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your BOT_TOKEN
nano .env  # or use your preferred editor
```

### 2. Run with Docker Compose

```bash
# Build and start the bot
docker-compose up -d

# View logs
docker-compose logs -f g25-telegram-bot

# Stop the bot
docker-compose down
```

### 3. Manual Docker Build & Run

```bash
# Build the image
docker build -t g25-bot:latest .

# Run the container
docker run -d \
  --name g25-bot \
  -e BOT_TOKEN=your_token_here \
  -e LOG_LEVEL=INFO \
  -v $(pwd)/Data:/app/Data:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/temp:/app/temp \
  g25-bot:latest
```

## Environment Variables

Create a `.env` file or pass these variables:

```env
# Required
BOT_TOKEN=your_telegram_bot_token_here

# Optional - Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Optional - Data Paths (in container)
ANCIENT_REF_PATH=/Data/Global25_PCA_scaled (Ancient Individuals).csv
MODERN_REF_PATH=/Data/Global25_PCA_modern_scaled.csv

# Optional - Application Settings
TEMP_DIR=/app/temp
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=10
TIMEOUT_SECONDS=300
```

## Project Structure

```
.
├── Dockerfile                 # Multi-stage Docker build
├── docker-compose.yml        # Docker Compose configuration
├── .dockerignore             # Files to exclude from Docker image
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── bot.py                    # Enhanced main bot with logging & error handling
├── nnls_script.py           # NNLS analysis implementation
├── closest_script.py        # Closest finder implementation
├── pca_script.py            # PCA visualization implementation
├── Data/                    # Reference datasets (mounted as read-only)
├── logs/                    # Bot logs (created automatically)
├── temp/                    # Temporary files during processing
└── README.md               # Documentation
```

## Bot Commands

### Start & Help
- `/start` - Welcome message and available commands
- `/help` - Detailed help information about all features

### Analysis Commands
- `/nnls` - NNLS ancestry decomposition (ancient populations)
- `/closest` - Find closest populations (ancient + modern)
- `/pca` - PCA visualization (modern populations)
- `/nnls_suggest` - Search ancient populations by name

### Other
- `/cancel` - Cancel current operation

## Input Data Format

CSV files should have populations/samples as rows and PCA components as columns:

```csv
Sample,PC1,PC2,PC3,...
Sample1,0.1,0.2,0.3,...
Sample2,-0.1,0.3,0.1,...
```

## Output

- **Text Results**: Ancestry composition, population distances, etc.
- **Visualizations**: PNG charts (pie charts, bar plots, scatter plots)

## Enhancements in This Version

1. **Logging System**
   - File-based logging to `logs/bot.log`
   - Configurable log levels
   - Comprehensive operation tracking

2. **Error Handling**
   - Try-catch blocks for all operations
   - User-friendly error messages
   - Validation of input data

3. **Configuration Management**
   - Environment-based configuration
   - Support for .env files
   - Configurable data paths and settings

4. **Docker Optimization**
   - Multi-stage builds for smaller images
   - Proper health checks
   - Volume mounting for data and logs

5. **Code Quality**
   - Type hints for functions
   - Comprehensive docstrings
   - Better code organization with sections

6. **User Experience**
   - Welcome message with command list
   - Detailed help command
   - Progress indicators (⏳ emoji)
   - Better error messages with emojis (❌)

## Troubleshooting

### Bot Won't Start
- Check `BOT_TOKEN` is set correctly: `echo $BOT_TOKEN`
- View logs: `docker-compose logs g25-telegram-bot`

### Data Files Not Found
- Ensure Data files are in the `Data/` directory
- Check volume mounts in docker-compose.yml
- Verify file paths in .env

### Out of Memory
- Check resource limits in docker-compose.yml
- Adjust TEMP_DIR cleanup if needed

### Slow Performance
- Monitor logs: `docker-compose logs -f`
- Check disk space for temp files
- Adjust MAX_FILE_SIZE_MB if needed

## Development

### Running Locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your BOT_TOKEN
cp .env.example .env
# Edit .env with your token

# Run the bot
python bot.py
```

### Building Logs

```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View specific container logs
docker-compose logs -f g25-telegram-bot
```

## Performance Tips

1. **Use file uploads** instead of pasting for large datasets
2. **Monitor temp directory**: Check `temp/` for leftover files
3. **Log rotation**: Implement log rotation for long-running deployments
4. **Resource allocation**: Adjust docker-compose.yml resource limits based on load

## License

MIT License - See LICENSE file for details

## Author

Hossein Razavi

## Support

For issues or questions, please open an issue on GitHub or contact the project maintainer.
