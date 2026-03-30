# API Server

The NotebookLM API server provides a REST API for programmatic access to NotebookLM functionality. It's built with FastAPI and can be deployed to Railway or any container platform.

## Quick Start

### Local Development

1. **Install dependencies**:
   ```bash
   uv pip install -e ".[web]"
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and set:
   # - API_SECRET_KEY (generate with: openssl rand -hex 32)
   # - NOTEBOOKLM_AUTH_JSON (from: cat ~/.notebooklm/storage_state.json)
   ```

3. **Run the server**:
   ```bash
   uvicorn notebooklm.server:app --reload
   ```

4. **Test the server**:
   ```bash
   # Health check
   curl http://localhost:8000/health

   # Create notebook
   curl -X POST http://localhost:8000/api/notebooks/create \
     -H "X-API-Key: your-secret-key" \
     -H "Content-Type: application/json" \
     -d '{"title": "My Research"}'
   ```

5. **View API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Health Check

**GET /health**

Check server health and authentication status.

**Response**:
```json
{
  "status": "ok",
  "authenticated": true
}
```

### Create Notebook

**POST /api/notebooks/create**

Create a new notebook.

**Headers**:
- `X-API-Key`: Your API secret key
- `Content-Type`: application/json

**Request Body**:
```json
{
  "title": "My Research"
}
```

**Response** (201 Created):
```json
{
  "notebook_id": "abc123...",
  "title": "My Research"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/notebooks/create \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"title": "AI Research"}'
```

### Add Source

**POST /api/sources/add**

Add a URL source to an existing notebook.

**Headers**:
- `X-API-Key`: Your API secret key
- `Content-Type`: application/json

**Request Body**:
```json
{
  "notebook_id": "abc123...",
  "url": "https://example.com"
}
```

**Response** (201 Created):
```json
{
  "source_id": "def456...",
  "title": "Example Domain",
  "status": "processing"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/sources/add \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"notebook_id": "abc123", "url": "https://en.wikipedia.org/wiki/Artificial_intelligence"}'
```

## Authentication

The API uses two levels of authentication:

### 1. API-Level Authentication (Client → Server)

Protect API endpoints with an API key passed in the `X-API-Key` header.

**Setup**:
```bash
# Generate a secure API key
openssl rand -hex 32

# Set in environment
export API_SECRET_KEY="your-generated-key"
```

**Usage**:
```bash
curl -H "X-API-Key: your-generated-key" http://localhost:8000/api/notebooks/create
```

### 2. Server-Level Authentication (Server → NotebookLM)

The server authenticates to NotebookLM using Google session credentials.

**Setup**:
1. Run `notebooklm login` locally to authenticate
2. Copy the credentials:
   ```bash
   cat ~/.notebooklm/storage_state.json
   ```
3. Set as environment variable (single-line JSON):
   ```bash
   export NOTEBOOKLM_AUTH_JSON='{"cookies":[...]}'
   ```

**Security Note**: `NOTEBOOKLM_AUTH_JSON` contains your Google session cookies. Treat it as highly sensitive - never commit to version control, and use secret management in production.

## Railway Deployment

Railway provides free hosting with automatic HTTPS and easy environment variable management.

### Prerequisites

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Authenticate**:
   ```bash
   railway login
   ```

### Deployment Steps

1. **Create a new project**:
   ```bash
   railway init
   ```

2. **Set environment variables**:
   ```bash
   # Generate and set API key
   railway variables set API_SECRET_KEY="$(openssl rand -hex 32)"

   # Set NotebookLM credentials
   railway variables set NOTEBOOKLM_AUTH_JSON="$(cat ~/.notebooklm/storage_state.json)"
   ```

3. **Deploy**:
   ```bash
   railway up
   ```

4. **Get your deployment URL**:
   ```bash
   railway status
   ```
   Your API will be available at `https://[project-name].up.railway.app`

5. **Test the deployment**:
   ```bash
   # Get your API key from Railway
   API_KEY=$(railway variables get API_SECRET_KEY)
   RAILWAY_URL="https://[project-name].up.railway.app"

   # Test health
   curl "$RAILWAY_URL/health"

   # Test create notebook
   curl -X POST "$RAILWAY_URL/api/notebooks/create" \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"title": "Test from Railway"}'
   ```

### GitHub Integration (Auto-Deploy)

1. **Connect repository in Railway dashboard**:
   - Go to your project settings
   - Connect your GitHub repository
   - Enable auto-deploy on push

2. **Push to deploy**:
   ```bash
   git push origin main
   ```

Railway will automatically build and deploy on every push.

### Monitoring

**View logs**:
```bash
railway logs
```

**Monitor deployment**:
- Railway Dashboard: https://railway.app/dashboard
- Metrics, logs, and environment variables available in UI

## Docker Deployment

### Build and Run Locally

1. **Build the image**:
   ```bash
   docker build -t notebooklm-api .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 \
     -e API_SECRET_KEY="your-key" \
     -e NOTEBOOKLM_AUTH_JSON="$(cat ~/.notebooklm/storage_state.json)" \
     notebooklm-api
   ```

3. **Test**:
   ```bash
   curl http://localhost:8000/health
   ```

### Deploy to Any Container Platform

The Docker image can be deployed to:
- **Railway**: Uses Dockerfile automatically
- **Google Cloud Run**: `gcloud run deploy`
- **AWS ECS/Fargate**: Push to ECR and deploy
- **Azure Container Instances**: Push to ACR and deploy
- **DigitalOcean App Platform**: Connect repository
- **Fly.io**: `fly deploy`

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `API_SECRET_KEY` | Yes | API key for endpoint authentication | `abc123...` (min 32 chars) |
| `NOTEBOOKLM_AUTH_JSON` | Yes | Google auth credentials (JSON) | `{"cookies":[...]}` |
| `PORT` | No | Server port (Railway sets automatically) | `8000` |
| `HOST` | No | Server host | `0.0.0.0` |

## Security Considerations

### API Key Security

- **Generate strong keys**: Use `openssl rand -hex 32` or similar
- **Rotate regularly**: Change keys periodically
- **Never commit**: Use environment variables, not hardcoded values
- **Use HTTPS**: Always access API over HTTPS in production (Railway provides this automatically)

### NotebookLM Credentials

`NOTEBOOKLM_AUTH_JSON` contains Google session cookies:

- **Highly sensitive**: Treat like a password
- **Session-based**: Will expire (typically 30-90 days)
- **Refresh when expired**: Re-run `notebooklm login` and update env var
- **Use secret management**: Railway/Docker secrets, not plaintext files
- **Never log**: Ensure credentials aren't written to logs

### Production Recommendations

1. **Add rate limiting**:
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   ```

2. **Add CORS for browser access**:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   app.add_middleware(CORSMiddleware, allow_origins=["https://yourapp.com"])
   ```

3. **Enable request logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

4. **Monitor authentication expiry**:
   - Set up alerts when `/health` returns `authenticated: false`
   - Automatically refresh credentials or notify admins

## Troubleshooting

### Health Check Fails

**Problem**: `/health` returns `authenticated: false`

**Solutions**:
1. Check `NOTEBOOKLM_AUTH_JSON` is set correctly
2. Verify credentials haven't expired (re-run `notebooklm login`)
3. Check Railway logs for authentication errors: `railway logs`

### API Key Rejected

**Problem**: 401 Unauthorized error

**Solutions**:
1. Verify `X-API-Key` header is included in request
2. Check API key matches `API_SECRET_KEY` environment variable
3. Ensure no extra whitespace in key

### Railway Deployment Fails

**Problem**: Build or deployment errors

**Solutions**:
1. Check Railway build logs: `railway logs`
2. Verify `Dockerfile` is in repository root
3. Ensure environment variables are set in Railway dashboard
4. Test Docker build locally: `docker build -t notebooklm-api .`

### Port Conflicts

**Problem**: "Address already in use" error

**Solutions**:
1. Change port: `PORT=8001 uvicorn notebooklm.server:app`
2. Kill existing process: `lsof -ti:8000 | xargs kill -9`

## Next Steps

- **Add more endpoints**: List notebooks, delete sources, generate artifacts
- **Add authentication middleware**: OAuth2, JWT tokens
- **Add async background tasks**: Long-running artifact generation
- **Add metrics**: Prometheus endpoint for monitoring
- **Add request validation**: Enhanced Pydantic models
- **Add OpenAPI customization**: Better API documentation

## Example Client Code

### Python (httpx)

```python
import httpx

API_URL = "https://your-app.up.railway.app"
API_KEY = "your-api-key"

async def create_notebook(title: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/api/notebooks/create",
            json={"title": title},
            headers={"X-API-Key": API_KEY},
        )
        response.raise_for_status()
        return response.json()

async def add_source(notebook_id: str, url: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/api/sources/add",
            json={"notebook_id": notebook_id, "url": url},
            headers={"X-API-Key": API_KEY},
        )
        response.raise_for_status()
        return response.json()

# Usage
result = await create_notebook("My Research")
notebook_id = result["notebook_id"]
await add_source(notebook_id, "https://example.com")
```

### JavaScript (fetch)

```javascript
const API_URL = "https://your-app.up.railway.app";
const API_KEY = "your-api-key";

async function createNotebook(title) {
  const response = await fetch(`${API_URL}/api/notebooks/create`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });
  return response.json();
}

async function addSource(notebookId, url) {
  const response = await fetch(`${API_URL}/api/sources/add`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ notebook_id: notebookId, url }),
  });
  return response.json();
}

// Usage
const result = await createNotebook("My Research");
const notebookId = result.notebook_id;
await addSource(notebookId, "https://example.com");
```

### cURL

```bash
# Set variables
API_URL="https://your-app.up.railway.app"
API_KEY="your-api-key"

# Create notebook
NOTEBOOK=$(curl -s -X POST "$API_URL/api/notebooks/create" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Research"}')

NOTEBOOK_ID=$(echo $NOTEBOOK | jq -r '.notebook_id')

# Add source
curl -X POST "$API_URL/api/sources/add" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"notebook_id\": \"$NOTEBOOK_ID\", \"url\": \"https://example.com\"}"
```
