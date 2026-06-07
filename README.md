# G25 Ancestry Telegram Bot

A powerful Telegram bot for ancestry analysis using G25 genetic datasets. Performs NNLS decomposition, population matching, and PCA visualization directly in Telegram with Docker support.

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/UncleRazavi/G25_Telegram_bot)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker Ready](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

### 📊 Analysis Tools

- **NNLS Ancestry Decomposition** - Decompose sample ancestry using ancient populations
- **Closest Population Finder** - Identify most similar populations from combined datasets
- **PCA Visualization** - Project samples onto modern population PCA space
- **Population Search** - Search and suggest ancient populations by name

### 🚀 Deployment

- **Docker Support** - Multi-stage builds, health checks, and optimized images
- **Docker Compose** - One-command deployment with proper volume management
- **GitHub Actions** - Automated CI/CD pipeline for builds and tests
- **Systemd Service** - Linux service integration for production

### 📈 Developer Features

- **Comprehensive Logging** - File and console logging with configurable levels
- **Error Handling** - Robust error handling with user-friendly messages
- **Type Hints** - Full type annotations for better code quality
- **Environment Config** - Flexible configuration via .env files

## Quick Start

### With Docker (Recommended)

```bash
# Clone and setup
git clone https://github.com/UncleRazavi/G25_Telegram_bot.git
cd G25_Telegram_bot

# Configure
cp .env.example .env
# Edit .env with your BOT_TOKEN

# Run
docker-compose up -d

# Monitor
docker-compose logs -f
```

### Local Development

```bash
# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your BOT_TOKEN

# Run
python bot.py
```

## Bot Commands

### Start & Help
- `/start` - Welcome message and command overview
- `/help` - Detailed help information

### Analysis
- `/nnls` - NNLS ancestry decomposition
- `/closest` - Find closest populations
- `/pca` - PCA visualization
- `/nnls_suggest` - Search ancient populations

### Other
- `/cancel` - Cancel current operation

## Input Format

Provide CSV data with populations as rows and PCA components as columns:

```csv
Sample,PC1,PC2,PC3,...
Sample1,0.1,0.2,0.3,...
Sample2,-0.1,0.3,0.1,...
```

## Output

- **Text Results** - Ancestry composition, distances, statistics
- **Visualizations** - PNG charts (pie charts, bar plots, scatter plots)

## Project Structure

```
G25_Telegram_bot/
├── bot.py                    # Main bot with logging & error handling
├── nnls_script.py           # NNLS analysis
├── closest_script.py        # Population matching
├── pca_script.py            # PCA visualization
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # Container orchestration
├── .env.example             # Configuration template
├── requirements.txt         # Python dependencies
├── Makefile                 # Common tasks
├── DOCKER_README.md         # Docker guide
├── DEPLOYMENT_GUIDE.md      # Deployment instructions
├── Data/                    # Reference datasets
├── logs/                    # Application logs
└── temp/                    # Temporary files
```

## Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Available settings:
- `BOT_TOKEN` - Your Telegram bot token (required)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `DATA_PATH` - Path to data directory
- `TEMP_DIR` - Temporary file directory
- `MAX_FILE_SIZE_MB` - Maximum file size limit
- `TIMEOUT_SECONDS` - Operation timeout

## Enhancements

### Version 2.0 (This Release)

✨ **New Features**
- Comprehensive logging system with file rotation
- Detailed error messages with emoji indicators
- Help command with feature descriptions
- Health checks for containers
- Environment-based configuration

🐳 **Docker Support**
- Multi-stage builds for smaller images
- Docker Compose for easy deployment
- Health checks and restart policies
- Volume management for data persistence

📋 **Developer Tools**
- GitHub Actions CI/CD workflow
- Makefile for common tasks
- Comprehensive deployment guide
- Type hints and docstrings

🔒 **Quality & Security**
- Comprehensive error handling
- Input validation
- Secure configuration management
- Code linting and formatting setup

## Documentation

- [Docker Guide](DOCKER_README.md) - Docker setup and deployment
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment instructions
- [GitHub Actions Workflow](.github/workflows/docker-build.yml) - CI/CD setup

## Usage Examples

### Running with Docker Compose

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Make Commands

```bash
make help      # Show all available commands
make build     # Build Docker image
make run       # Run bot
make logs      # View logs
make dev       # Run locally for development
make clean     # Clean up
```

### Manual Docker Commands

```bash
# Build
docker build -t g25-bot:latest .

# Run
docker run -d \
  --name g25-bot \
  -e BOT_TOKEN=your_token \
  -v $(pwd)/Data:/app/Data:ro \
  -v $(pwd)/logs:/app/logs \
  g25-bot:latest

# Monitor
docker logs -f g25-bot
```

## System Requirements

- **Docker**: 20.10+ (recommended)
- **Docker Compose**: 1.29+ (recommended)
- **Python**: 3.9+ (for local development)
- **RAM**: 512MB minimum, 1GB recommended
- **Disk**: 500MB+ for image and logs

## Performance

- Typical NNLS analysis: 1-5 seconds
- Closest finder: 2-10 seconds
- PCA visualization: 3-8 seconds
- Memory usage: 200-400MB under normal load

## Troubleshooting

### Bot Won't Start
```bash
# Check logs
docker-compose logs

# Verify BOT_TOKEN
echo $BOT_TOKEN

# Check data files
docker-compose exec g25-telegram-bot ls /app/Data/
```

### Out of Memory
- Increase Docker memory limit
- Reduce MAX_FILE_SIZE_MB
- Check temp directory cleanup

### Slow Performance
- Monitor resource usage: `docker stats`
- Check disk space: `df -h`
- Review logs for errors: `docker-compose logs | grep ERROR`

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for more troubleshooting.

## Development

### Adding New Features

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test locally
3. Run linting: `make lint`
4. Commit with clear messages
5. Push and create pull request

### Testing Locally

```bash
# Setup development environment
make setup

# Run with debug logging
LOG_LEVEL=DEBUG make dev

# Monitor logs
docker-compose logs -f
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Dependencies

### Core
- `python-telegram-bot` - Telegram bot framework
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `scipy` - Scientific computing
- `matplotlib` - Plotting
- `scikit-learn` - Machine learning
- `seaborn` - Statistical visualization

### Development
- `python-dotenv` - Environment variable management
- `pylint` - Code linting
- `black` - Code formatting
- `pytest` - Testing framework

## License

MIT License - see [LICENSE](LICENSE) file for details

## Author

**Hossein Razavi**

## Support & Contact

- 📧 Report issues on [GitHub Issues](https://github.com/UncleRazavi/G25_Telegram_bot/issues)
- 💬 Discussions on [GitHub Discussions](https://github.com/UncleRazavi/G25_Telegram_bot/discussions)
- 📝 Check the [Wiki](https://github.com/UncleRazavi/G25_Telegram_bot/wiki) for detailed guides

## Citation

If you use this bot in your research, please cite:

```bibtex
@software{razavi2025g25bot,
  title={G25 Ancestry Telegram Bot},
  author={Razavi, Hossein},
  year={2025},
  url={https://github.com/UncleRazavi/G25_Telegram_bot}
}
```

## Changelog

### v2.0
- Docker support with multi-stage builds
- Enhanced logging and error handling
- Comprehensive documentation
- GitHub Actions CI/CD workflow
- Environment-based configuration
- Type hints and docstrings

### v1.0
- Initial release
- Core NNLS, Closest, and PCA functionality

## Roadmap

- [ ] Multi-language support
- [ ] Result caching
- [ ] Advanced visualization options
- [ ] Batch processing
- [ ] Web UI dashboard
- [ ] Results export (JSON, PDF)
- [ ] User statistics
- [ ] Rate limiting and quotas

## FAQ

**Q: Can I deploy on my own server?**
A: Yes! See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for instructions.

**Q: What data format do you support?**
A: CSV files with samples as rows and PCA components as columns.

**Q: How long do analyses take?**
A: Typically 1-10 seconds depending on data size.

**Q: Is there a rate limit?**
A: Currently no, but large files (>10MB) are rejected by default.

**Q: How do I get a Telegram bot token?**
A: Message @BotFather on Telegram and follow the instructions.

---

Made with ❤️ for ancestry analysis enthusiasts

