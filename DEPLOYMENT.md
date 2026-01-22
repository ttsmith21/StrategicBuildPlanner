# Deployment Guide

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed
- OpenAI API key
- Confluence API credentials (for integration)

### 1. Clone and Configure

```bash
git clone https://github.com/ttsmith21/StrategicBuildPlanner.git
cd StrategicBuildPlanner

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your API keys
```

### 2. Build and Run

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Access the Application

- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Deployment Options

### Option 1: Local Docker (Development/Demo)
Best for: Testing, demos, single-user access

```bash
docker-compose up -d --build
```

### Option 2: Internal Server
Best for: Team access within company network

1. Deploy to a server with Docker installed
2. Update `VITE_API_URL` in docker-compose.yml to server IP/hostname
3. Configure firewall to allow ports 80 and 8000
4. Run `docker-compose up -d --build`

### Option 3: Cloud Deployment

#### Railway (Recommended for simplicity)
1. Connect GitHub repo to Railway
2. Add environment variables in Railway dashboard
3. Deploy backend and frontend as separate services

#### AWS / Azure / GCP
1. Use container services (ECS, Azure Container Apps, Cloud Run)
2. Set up load balancer for frontend
3. Configure environment variables via secrets manager

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for AI features |
| `OPENAI_MODEL_PLAN` | No | Model for plan generation (default: gpt-4o) |
| `CONFLUENCE_BASE_URL` | Yes* | Confluence instance URL |
| `CONFLUENCE_API_TOKEN` | Yes* | Confluence API token |
| `CONFLUENCE_USER_EMAIL` | Yes* | Email for Confluence auth |
| `ASANA_TOKEN` | No | Asana API token for task creation |

*Required for Confluence integration features

---

## Production Considerations

### Security
- [ ] Use HTTPS (add reverse proxy like Traefik or nginx)
- [ ] Set strong API keys
- [ ] Restrict CORS origins to your domain
- [ ] Consider adding authentication (OAuth, SSO)

### Performance
- [ ] Use production Docker images (already optimized)
- [ ] Configure resource limits in docker-compose.yml
- [ ] Set up monitoring (health checks included)

### Backup
- [ ] Application is stateless - no database to backup
- [ ] All data stored in Confluence/Asana

---

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend
```

### API connection issues
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in docker-compose.yml
3. Verify `VITE_API_URL` matches backend URL

### Confluence integration not working
1. Verify API token is valid
2. Check Confluence URL format (should end with `/wiki`)
3. Ensure user email matches Confluence account
