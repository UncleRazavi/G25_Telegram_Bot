# G25 Bot - Deployment & Setup Guide

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Setup](#docker-setup)
3. [Production Deployment](#production-deployment)
4. [Troubleshooting](#troubleshooting)

## Local Development Setup

### Prerequisites

- Python 3.9+ installed
- pip (Python package manager)
- Git
- Telegram Bot Token (from @BotFather)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/UncleRazavi/G25_Telegram_bot.git
   cd G25_Telegram_bot
   ```

2. **Create virtual environment**
   ```bash
   # On Linux/Mac
   python3 -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your BOT_TOKEN
   ```

5. **Run the bot**
   ```bash
   python bot.py
   ```

### Development Tips

- Check logs: `tail -f logs/bot.log`
- Enable debug logging: Set `LOG_LEVEL=DEBUG` in .env
- Test commands in Telegram: `/start`, `/help`, `/nnls`, etc.

## Docker Setup

### Quick Start

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your BOT_TOKEN

# 2. Start with Docker Compose
docker-compose up -d

# 3. Check logs
docker-compose logs -f

# 4. Stop
docker-compose down
```

### Docker Commands Reference

```bash
# Build image
docker build -t g25-bot:latest .

# Run container
docker run -d \
  --name g25-bot \
  -e BOT_TOKEN=your_token \
  -v $(pwd)/Data:/app/Data:ro \
  -v $(pwd)/logs:/app/logs \
  g25-bot:latest

# View logs
docker logs -f g25-bot

# Stop container
docker stop g25-bot

# Remove container
docker rm g25-bot

# Check container status
docker ps -a

# Execute command in container
docker exec g25-bot python -c "import pandas; print(pandas.__version__)"
```

### Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs

# Follow logs
docker-compose logs -f g25-telegram-bot

# Restart service
docker-compose restart g25-telegram-bot

# View running services
docker-compose ps

# Remove volumes
docker-compose down -v
```

## Production Deployment

### Using Docker on Linux Server

1. **Copy files to server**
   ```bash
   scp -r G25_Telegram_bot user@server:/path/to/app
   cd /path/to/app
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your BOT_TOKEN
   ```

3. **Set up systemd service** (optional)
   
   Create `/etc/systemd/system/g25-bot.service`:
   ```ini
   [Unit]
   Description=G25 Ancestry Telegram Bot
   After=docker.service
   Requires=docker.service

   [Service]
   Type=simple
   WorkingDirectory=/path/to/app
   ExecStart=/usr/bin/docker-compose up
   ExecStop=/usr/bin/docker-compose down
   Restart=unless-stopped

   [Install]
   WantedBy=multi-user.target
   ```

   Then:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable g25-bot
   sudo systemctl start g25-bot
   sudo systemctl status g25-bot
   ```

4. **Monitor the service**
   ```bash
   sudo journalctl -u g25-bot -f
   docker-compose logs -f
   ```

### Using Kubernetes

Example deployment YAML:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: g25-telegram-bot
  labels:
    app: g25-telegram-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: g25-telegram-bot
  template:
    metadata:
      labels:
        app: g25-telegram-bot
    spec:
      containers:
      - name: g25-bot
        image: g25-bot:latest
        env:
        - name: BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: bot-secret
              key: token
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: data
          mountPath: /app/Data
          readOnly: true
        - name: logs
          mountPath: /app/logs
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: data
        hostPath:
          path: /data/g25
      - name: logs
        emptyDir: {}
```

### Monitoring

1. **Health Check**
   ```bash
   curl http://localhost:8000/health 2>/dev/null
   ```

2. **Log Analysis**
   ```bash
   # Count errors
   grep ERROR logs/bot.log | wc -l

   # Find slow operations
   grep "completed" logs/bot.log | grep -oP '\d+\.\d+ seconds'
   ```

3. **Resource Usage**
   ```bash
   docker stats g25-bot
   ```

## Troubleshooting

### Bot Won't Start

**Problem**: Container exits immediately

**Solution**:
```bash
# Check logs
docker-compose logs

# Check environment
docker-compose exec g25-telegram-bot env | grep BOT_TOKEN

# Verify files exist
docker-compose exec g25-telegram-bot ls -la /Data/
```

### Data Files Missing

**Problem**: "FileNotFoundError: Global25_PCA_*.csv"

**Solution**:
```bash
# Check Data directory
ls -la Data/

# Verify mounted in container
docker-compose exec g25-telegram-bot ls /app/Data/

# Fix: Ensure csv files are in Data/ directory
```

### Out of Memory

**Problem**: Container gets killed

**Solution**:
1. Check current usage: `docker stats`
2. Increase memory in docker-compose.yml
3. Or reduce MAX_FILE_SIZE_MB in .env

### Permission Denied

**Problem**: "Permission denied" errors in logs

**Solution**:
```bash
# Fix permissions
chmod 755 docker-entrypoint.sh
chmod 644 .env

# Or run with appropriate user
docker run --user 1000:1000 ...
```

### Bot Not Responding

**Problem**: Bot doesn't reply to commands

**Solution**:
```bash
# Check if bot is running
docker-compose ps

# Restart bot
docker-compose restart g25-telegram-bot

# Check logs for errors
docker-compose logs | tail -100

# Verify BOT_TOKEN is correct
echo $BOT_TOKEN
```

## Maintenance

### Cleaning Up

```bash
# Remove old containers
docker container prune

# Remove unused images
docker image prune

# Clean logs
truncate -s 0 logs/bot.log

# Clean temp files
rm -rf temp/*
```

### Updating

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose build --no-cache

# Restart service
docker-compose up -d
```

### Backing Up Logs

```bash
# Archive logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Keep only recent logs
find logs -name "*.log" -mtime +30 -delete
```

## Performance Optimization

1. **Use read-only Data volume** ✓ (Already configured)
2. **Enable caching** - Consider caching processed results
3. **Use deployment-specific configs** - Adjust resource limits
4. **Monitor and alert** - Set up Prometheus/Grafana for monitoring

## Security Best Practices

1. **Environment variables** - Never commit .env file
2. **Secret management** - Use Docker secrets or external vault
3. **Network isolation** - Use internal Docker networks
4. **Volume permissions** - Run as non-root user
5. **Regular updates** - Keep Python and dependencies updated

```bash
# Keep dependencies updated
pip list --outdated
pip install --upgrade -r requirements.txt
```

## Support

For issues or questions:
- Check logs: `docker-compose logs`
- Enable debug: Set `LOG_LEVEL=DEBUG`
- Review code: Check bot.py for error handling
- Submit issues on GitHub
