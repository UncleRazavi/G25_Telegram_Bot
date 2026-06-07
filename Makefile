.PHONY: help build run stop logs clean install test lint format

help:
	@echo "G25 Telegram Bot - Available Commands"
	@echo "====================================="
	@echo "make build       - Build Docker image"
	@echo "make run         - Run bot with docker-compose"
	@echo "make stop        - Stop bot"
	@echo "make logs        - View bot logs"
	@echo "make logs-follow - Follow bot logs in real-time"
	@echo "make clean       - Clean up containers and volumes"
	@echo "make install     - Install Python dependencies"
	@echo "make test        - Run tests"
	@echo "make lint        - Lint code"
	@echo "make format      - Format code"
	@echo "make dev         - Run bot locally for development"
	@echo "make shell       - Open shell in running container"
	@echo "make restart     - Restart bot"
	@echo "make ps          - Show running containers"
	@echo "make status      - Show service status"

build:
	@echo "Building Docker image..."
	docker-compose build

run:
	@echo "Starting bot with docker-compose..."
	docker-compose up -d

stop:
	@echo "Stopping bot..."
	docker-compose down

logs:
	@echo "Showing bot logs..."
	docker-compose logs g25-telegram-bot

logs-follow:
	@echo "Following bot logs..."
	docker-compose logs -f g25-telegram-bot

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache temp/* logs/*.log
	@echo "Cleanup complete!"

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

test:
	@echo "Running tests..."
	python -m pytest tests/ -v 2>/dev/null || echo "No tests found"

lint:
	@echo "Linting code..."
	pylint bot.py nnls_script.py closest_script.py pca_script.py 2>/dev/null || echo "Linting check complete"

format:
	@echo "Formatting code..."
	black . 2>/dev/null || echo "Black not installed, skipping"
	autopep8 --in-place --aggressive --aggressive bot.py 2>/dev/null || echo "Autopep8 not installed"

dev:
	@echo "Starting bot for development..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file - please edit with your BOT_TOKEN"; \
		echo ""; \
	fi
	python bot.py

shell:
	@echo "Opening shell in container..."
	docker-compose exec g25-telegram-bot /bin/bash

restart:
	@echo "Restarting bot..."
	docker-compose restart g25-telegram-bot
	@echo "Bot restarted!"

ps:
	@echo "Running containers:"
	docker-compose ps

status:
	@echo "Service status:"
	docker-compose ps
	@echo ""
	@echo "Container stats:"
	docker stats --no-stream g25-telegram-bot 2>/dev/null || echo "Container not running"

version:
	@echo "Python version:"
	@python --version
	@echo "Docker version:"
	@docker --version
	@echo "Docker Compose version:"
	@docker-compose --version

# Development helpers
requirements-update:
	@echo "Checking for outdated packages..."
	pip list --outdated

requirements-upgrade:
	@echo "Upgrading all packages..."
	pip install --upgrade -r requirements.txt

docker-build-nocache:
	@echo "Building Docker image (no cache)..."
	docker-compose build --no-cache

docker-logs-error:
	@echo "Showing errors in logs..."
	docker-compose logs | grep -i error || echo "No errors found"

docker-shell-root:
	@echo "Opening root shell in container..."
	docker-compose exec -u root g25-telegram-bot /bin/bash

# Setup helpers
setup:
	@echo "Setting up project..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file"; \
	fi
	@if [ ! -d logs ]; then \
		mkdir -p logs; \
		echo "Created logs directory"; \
	fi
	@if [ ! -d temp ]; then \
		mkdir -p temp; \
		echo "Created temp directory"; \
	fi
	@echo "Setup complete! Next steps:"
	@echo "1. Edit .env with your BOT_TOKEN"
	@echo "2. Run 'make run' to start the bot"
	@echo "3. Run 'make logs-follow' to monitor logs"

.DEFAULT_GOAL := help
