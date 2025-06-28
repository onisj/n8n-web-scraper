# 🚀 Web Modernization Quick Start

This guide helps you modernize the n8n AI Knowledge System from Streamlit to a modern web stack with monitoring, Discord integration, and Chrome extension.

## 🎯 What You'll Get

- **Modern Frontend**: Next.js + React + TypeScript + Tailwind CSS
- **Enhanced Backend**: FastAPI with WebSocket support and Prometheus metrics
- **Monitoring Stack**: Prometheus + Grafana dashboards
- **Discord Bot**: AI assistant for Discord servers
- **Chrome Extension**: Browser-based AI assistant
- **Production Ready**: Docker containers, Redis caching, PostgreSQL

## 🚀 Quick Start

### 1. Run the Setup Script

```bash
# Make sure you're in the project root
cd /path/to/n8n-web-scrapper

# Run the automated setup
python3 scripts/modernize_setup.py
```

The script will:
- ✅ Check prerequisites (Node.js, npm, Python, Docker)
- 🏗️ Create Next.js frontend with TypeScript and Tailwind
- 🤖 Setup Discord bot structure
- 🌐 Create Chrome extension template
- 📊 Configure Prometheus + Grafana monitoring
- 🐳 Generate Docker Compose configurations
- 📝 Create development Makefile

### 2. Configure Environment Variables

```bash
# Main project environment
cp .env.example .env
# Edit .env with your settings

# Discord bot environment
cp discord-bot/.env.example discord-bot/.env
# Add your Discord bot token

# Frontend environment (already created)
# Edit frontend/.env.local if needed
```

### 3. Start Development

```bash
# Start all services with monitoring and Discord
make all-full

# Or start individual services:
make frontend    # Next.js dev server
make backend     # FastAPI dev server
make monitoring  # Prometheus + Grafana
make discord     # Discord bot
```

### 4. Access Your Applications

- 🌐 **Frontend**: http://localhost:3000
- 🔧 **Backend API**: http://localhost:8000
- 📊 **Prometheus**: http://localhost:9090
- 📈 **Grafana**: http://localhost:3001 (admin/admin)
- 📚 **API Docs**: http://localhost:8000/docs

## 🛠️ Development Commands

```bash
# Setup commands
make setup           # Run initial setup
make setup-frontend  # Install frontend dependencies
make setup-discord   # Install Discord bot dependencies

# Development
make frontend        # Start Next.js dev server
make backend         # Start FastAPI dev server
make discord         # Start Discord bot
make monitoring      # Start Prometheus + Grafana

# Docker commands
make all             # Start core services
make all-with-monitoring  # Include monitoring
make all-with-discord     # Include Discord bot
make all-full        # Everything (recommended)

# Testing
make test           # Run all tests

# Cleanup
make clean          # Stop and remove containers
```

## 📁 New Project Structure

```
n8n-web-scrapper/
├── frontend/                 # Next.js React app
│   ├── src/app/             # App router pages
│   ├── src/components/      # React components
│   ├── src/lib/            # Utilities and API clients
│   └── package.json
├── discord-bot/             # Discord bot
│   ├── src/
│   │   ├── commands/       # Slash commands
│   │   ├── index.js        # Main bot file
│   │   └── deploy-commands.js
│   └── package.json
├── chrome-extension/        # Browser extension
│   ├── popup/              # Extension popup
│   ├── content/            # Content scripts
│   ├── background/         # Service worker
│   └── manifest.json
├── monitoring/              # Monitoring stack
│   ├── prometheus/         # Prometheus config
│   ├── grafana/           # Grafana dashboards
│   └── docker-compose.monitoring.yml
├── src/                    # Existing Python backend
└── docker-compose.modernized.yml  # New Docker setup
```

## 🤖 Discord Bot Setup

1. **Create Discord Application**:
   - Go to https://discord.com/developers/applications
   - Create new application
   - Go to "Bot" section and create bot
   - Copy bot token

2. **Configure Bot**:
   ```bash
   cd discord-bot
   cp .env.example .env
   # Add your DISCORD_TOKEN, CLIENT_ID, and GUILD_ID
   ```

3. **Deploy Commands**:
   ```bash
   cd discord-bot
   npm run deploy
   ```

4. **Invite Bot to Server**:
   - Use OAuth2 URL generator in Discord Developer Portal
   - Select "bot" and "applications.commands" scopes
   - Add required permissions

## 🌐 Chrome Extension Setup

1. **Load Extension**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chrome-extension/` directory

2. **Test Extension**:
   - Visit n8n documentation pages
   - Click extension icon in toolbar
   - Use the AI assistant popup

## 📊 Monitoring Setup

The monitoring stack includes:

- **Prometheus**: Metrics collection from backend API
- **Grafana**: Dashboards for visualizing metrics
- **Custom Metrics**: API response times, request counts, error rates

### Default Dashboards

- API Performance
- System Resources
- User Activity
- Error Tracking

## 🔧 Troubleshooting

### Common Issues

1. **Port Conflicts**:
   ```bash
   # Check what's using ports
   lsof -i :3000  # Frontend
   lsof -i :8000  # Backend
   lsof -i :9090  # Prometheus
   lsof -i :3001  # Grafana
   ```

2. **Docker Issues**:
   ```bash
   # Reset Docker state
   make clean
   docker system prune -f
   ```

3. **Node.js Issues**:
   ```bash
   # Clear npm cache
   npm cache clean --force
   
   # Reinstall dependencies
   cd frontend && rm -rf node_modules package-lock.json && npm install
   ```

4. **Python Issues**:
   ```bash
   # Reinstall Python dependencies
   pip install -r requirements.txt --force-reinstall
   ```

### Getting Help

- 📚 **Implementation Guide**: `docs/IMPLEMENTATION_GUIDE.md`
- 🗺️ **Modernization Plan**: `docs/WEB_MODERNIZATION_PLAN.md`
- 🛠️ **Development Guide**: `docs/DEVELOPMENT_TESTING.md`

## 🎯 Next Steps

1. **Customize Frontend**: Modify React components in `frontend/src/components/`
2. **Add Discord Commands**: Create new commands in `discord-bot/src/commands/`
3. **Enhance Extension**: Add features to `chrome-extension/`
4. **Configure Monitoring**: Add custom Grafana dashboards
5. **Deploy to Production**: Use the deployment guides in `docs/`

## 📝 Notes

- **setup.py**: Not needed! This project uses `pyproject.toml` for modern Python packaging
- **Streamlit**: Will be completely replaced by the Next.js frontend
- **Backward Compatibility**: The FastAPI backend remains compatible with existing features
- **Gradual Migration**: You can run both old and new systems during transition

---

🎉 **Happy coding!** Your modernized n8n AI Knowledge System is ready for the future!