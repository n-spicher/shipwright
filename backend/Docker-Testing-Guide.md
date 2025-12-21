# Docker Implementation Testing Guide

## Prerequisites
1. **Docker Desktop** installed and running
2. **Environment variables** configured in `.env` file
3. **API keys** for Google Gemini and Firebase

## Step-by-Step Testing

### 1. Environment Setup
```bash
# Navigate to project root
cd Shipwright

# Copy environment template
cp .env.example .env

# Edit .env with your actual API keys
# Required: GOOGLE_API_KEY, Firebase config variables
```

### 2. Build and Start Services
```bash
# Build all containers (first time)
docker-compose build

# Start all services in background
docker-compose up -d

# View startup logs
docker-compose logs -f
```

### 3. Verify Service Status
```bash
# Check all services are running
docker-compose ps

# Expected output:
# backend    Up    0.0.0.0:8000->8000/tcp
# frontend   Up    0.0.0.0:3000->3000/tcp  
# chroma     Up    0.0.0.0:8001->8000/tcp
```

### 4. Test Individual Services

#### Backend API Tests
```bash
# Health check
curl http://localhost:8000/ping
# Expected: {"message":"pong"}

# API documentation
open http://localhost:8000/docs

# Test user creation
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"testpass123"}'
```

#### Frontend Tests
```bash
# Open React app
open http://localhost:3000

# Should see login page
# Test Firebase authentication (if configured)
```

#### ChromaDB Tests
```bash
# ChromaDB health check
curl http://localhost:8001/api/v1/heartbeat
# Expected: {"nanosecond heartbeat": timestamp}

# List collections
curl http://localhost:8001/api/v1/collections
```

### 5. Network Communication Tests
```bash
# Test backend can reach ChromaDB
docker-compose exec backend curl http://chroma:8000/api/v1/heartbeat

# Test service discovery
docker-compose exec backend ping chroma
docker-compose exec frontend ping backend
```

### 6. Volume Persistence Tests
```bash
# Create test data
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"email":"persist@test.com","username":"persistuser","password":"test123"}'

# Stop services
docker-compose down

# Restart services
docker-compose up -d

# Verify data persisted
curl "http://localhost:8000/users/1"
```

### 7. Log Analysis
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs chroma

# Follow logs in real-time
docker-compose logs -f backend
```

### 8. Performance Tests
```bash
# Check resource usage
docker stats

# Test concurrent requests
for i in {1..10}; do
  curl http://localhost:8000/ping &
done
wait
```

## Functional Testing Scenarios

### Scenario 1: Complete User Workflow
1. **Access frontend** at http://localhost:3000
2. **Create account** (if Firebase configured)
3. **Upload PDF** document
4. **View document** in PDF viewer
5. **Ask questions** in chat interface
6. **Verify responses** from AI

### Scenario 2: API Integration Test
```bash
# 1. Create user
USER_RESPONSE=$(curl -s -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"email":"api@test.com","username":"apiuser","password":"test123"}')

USER_ID=$(echo $USER_RESPONSE | jq -r '.id')

# 2. Test chat endpoint
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Hello\",\"user_id\":$USER_ID,\"mode\":\"NONE\"}"
```

### Scenario 3: Error Handling
```bash
# Test invalid requests
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"email":"invalid-email","username":"","password":""}'

# Test non-existent endpoints
curl http://localhost:8000/nonexistent
```

## Troubleshooting Common Issues

### Services Won't Start
```bash
# Check Docker daemon
docker --version
docker-compose --version

# Check port conflicts
netstat -an | findstr :8000
netstat -an | findstr :3000

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Environment Variable Issues
```bash
# Verify .env file exists
ls -la .env

# Check environment variables in container
docker-compose exec backend env | grep GOOGLE_API_KEY
docker-compose exec frontend env | grep REACT_APP_
```

### Network Issues
```bash
# Inspect network
docker network ls
docker network inspect shipwright_shipwright-network

# Test connectivity
docker-compose exec backend nslookup chroma
docker-compose exec frontend nslookup backend
```

### Volume Issues
```bash
# Check volume mounts
docker-compose exec backend ls -la /app/data
docker-compose exec backend ls -la /app/sql_app.db

# Inspect volumes
docker volume ls
docker volume inspect shipwright_chroma_data
```

## Performance Benchmarks

### Expected Response Times
- **Health checks**: < 100ms
- **User creation**: < 500ms
- **Document upload**: Varies by size
- **Chat queries**: 1-5 seconds (depends on AI processing)

### Resource Usage
- **Backend**: ~200MB RAM, minimal CPU
- **Frontend**: ~100MB RAM, minimal CPU  
- **ChromaDB**: ~300MB RAM, moderate CPU during indexing

## Success Criteria

✅ **All services start successfully**
✅ **Health checks pass for all endpoints**
✅ **Network communication works between services**
✅ **Data persists across container restarts**
✅ **Frontend loads and displays correctly**
✅ **API endpoints respond with expected data**
✅ **Logs show no critical errors**

## Cleanup
```bash
# Stop services
docker-compose down

# Remove volumes (destroys data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Complete cleanup
docker system prune -a
```