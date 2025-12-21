# Shipwright Docker Setup

## Quick Start with Docker

1. **Clone and Setup Environment**
   ```bash
   cd Shipwright
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start All Services**
   ```bash
   docker-compose up -d
   ```

3. **Access Applications**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - ChromaDB: http://localhost:8001

## Benefits of Docker Implementation

### Development Benefits
- **No Python Version Issues**: Guaranteed Python 3.11 environment
- **No Virtual Environment Setup**: Docker handles isolation
- **Consistent Dependencies**: Same versions across all environments
- **One Command Startup**: `docker-compose up` starts everything

### Production Benefits
- **Scalability**: Easy horizontal scaling with Docker Swarm/Kubernetes
- **Isolation**: Services run in separate containers
- **Rollback**: Easy version management and rollbacks
- **Monitoring**: Better observability with container logs

### Data Persistence
- ChromaDB data persists in Docker volume
- SQLite database mounted as volume
- No data loss on container restart

## Development Workflow

### Start Development Environment
```bash
docker-compose up -d
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Rebuild After Code Changes
```bash
# Rebuild specific service
docker-compose build backend
docker-compose up -d backend

# Rebuild all
docker-compose build
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

## Production Deployment

### Using Docker Swarm
```bash
docker swarm init
docker stack deploy -c docker-compose.yml shipwright
```

### Using Kubernetes
Convert docker-compose.yml to Kubernetes manifests:
```bash
kompose convert
kubectl apply -f .
```

## Troubleshooting

### Check Service Status
```bash
docker-compose ps
```

### Access Container Shell
```bash
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Reset Everything
```bash
docker-compose down -v
docker-compose up -d
```