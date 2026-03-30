# Railway Deployment Quick Start

Deploy the NotebookLM API server to Railway in under 5 minutes.

## Prerequisites

1. **Railway account**: Sign up at [railway.app](https://railway.app)
2. **Railway CLI**: `npm install -g @railway/cli`
3. **NotebookLM auth**: Run `notebooklm login` locally first

## Step-by-Step Deployment

### 1. Prepare Authentication

```bash
# Authenticate with NotebookLM locally
notebooklm login

# Save auth JSON (you'll need this for Railway)
cat ~/.notebooklm/storage_state.json
```

Copy the output - you'll paste it into Railway in step 4.

### 2. Install and Login to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login (opens browser)
railway login
```

### 3. Create Railway Project

```bash
# Navigate to your project directory
cd /path/to/notebooklm-py

# Initialize Railway project
railway init

# Give it a name (e.g., "notebooklm-api")
```

### 4. Set Environment Variables

**Option A: Via CLI (Recommended)**

```bash
# Generate and set API key
railway variables set API_SECRET_KEY="$(openssl rand -hex 32)"

# Set NotebookLM auth (paste the JSON from step 1)
railway variables set NOTEBOOKLM_AUTH_JSON="$(cat ~/.notebooklm/storage_state.json)"
```

**Option B: Via Dashboard**

1. Go to [railway.app/dashboard](https://railway.app/dashboard)
2. Select your project
3. Go to "Variables" tab
4. Add:
   - `API_SECRET_KEY`: Generate with `openssl rand -hex 32`
   - `NOTEBOOKLM_AUTH_JSON`: Paste JSON from step 1

### 5. Deploy

```bash
# Deploy to Railway
railway up

# Watch deployment logs
railway logs
```

Railway will:
- Detect the `Dockerfile`
- Build the image
- Deploy to a public URL
- Provide automatic HTTPS

### 6. Get Your API URL

```bash
# Get deployment URL
railway status

# Or open in browser
railway open
```

Your API will be at: `https://[your-project].up.railway.app`

### 7. Test Your Deployment

```bash
# Get your API key
API_KEY=$(railway variables get API_SECRET_KEY)

# Get your Railway URL (replace with your actual URL)
RAILWAY_URL="https://[your-project].up.railway.app"

# Test health endpoint
curl "$RAILWAY_URL/health"

# Test creating a notebook
curl -X POST "$RAILWAY_URL/api/notebooks/create" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test from Railway"}'
```

Or use the test script:

```bash
./test_server.sh "$RAILWAY_URL" "$API_KEY"
```

## Enable Auto-Deploy from GitHub

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Add NotebookLM API server"
   git push origin main
   ```

2. **Connect in Railway Dashboard**:
   - Go to your project settings
   - Click "Connect GitHub Repo"
   - Select your repository
   - Enable auto-deploy

3. **Deploy on push**:
   ```bash
   git push origin main
   ```
   Railway will automatically build and deploy!

## View Logs and Monitor

```bash
# View real-time logs
railway logs

# Or use the dashboard
railway open
```

In the dashboard you can:
- View deployment logs
- Monitor resource usage
- See request metrics
- Manage environment variables

## Update Credentials

If your NotebookLM session expires:

```bash
# Re-authenticate locally
notebooklm login

# Update Railway variable
railway variables set NOTEBOOKLM_AUTH_JSON="$(cat ~/.notebooklm/storage_state.json)"

# Restart deployment
railway up
```

## Troubleshooting

### Build Fails

**Problem**: `Forced include not found: /app/AGENTS.md`

**Solution**: Ensure `SKILL.md` and `AGENTS.md` are not in `.dockerignore` exceptions:
```bash
git add SKILL.md AGENTS.md
git commit -m "Add required build files"
railway up
```

### Health Check Returns `authenticated: false`

**Problem**: NotebookLM auth failed

**Solutions**:
1. Verify `NOTEBOOKLM_AUTH_JSON` is set correctly in Railway variables
2. Check if credentials expired - re-run `notebooklm login`
3. View logs: `railway logs`

### API Returns 401 Unauthorized

**Problem**: API key mismatch

**Solutions**:
1. Get your API key: `railway variables get API_SECRET_KEY`
2. Verify you're using `X-API-Key` header
3. Check for whitespace in the key

### Deployment Stuck

**Problem**: Build or deployment hangs

**Solutions**:
1. Check Railway status: [status.railway.app](https://status.railway.app)
2. View build logs: `railway logs`
3. Restart deployment: `railway up --detach`

## Costs

Railway offers:
- **Free tier**: $5 credit/month (enough for small projects)
- **Usage-based pricing**: ~$0.000463/GB-hour for RAM

A typical NotebookLM API deployment uses:
- ~100MB RAM idle
- ~0.5GB RAM under load
- Estimate: $1-3/month for light use

Monitor usage in the Railway dashboard.

## Security Best Practices

1. **Rotate API keys regularly**:
   ```bash
   railway variables set API_SECRET_KEY="$(openssl rand -hex 32)"
   ```

2. **Use strong API keys** (min 32 characters)

3. **Monitor access logs** via Railway dashboard

4. **Enable CORS** if accessed from web frontend:
   ```python
   # Add to server.py
   from fastapi.middleware.cors import CORSMiddleware
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourapp.com"],
       allow_methods=["POST", "GET"],
       allow_headers=["X-API-Key", "Content-Type"],
   )
   ```

5. **Add rate limiting** for production use

## Next Steps

- **API Documentation**: Visit `https://[your-url]/docs` for Swagger UI
- **Add endpoints**: Extend `src/notebooklm/server.py` with more features
- **Monitor usage**: Set up alerts in Railway for errors/usage spikes
- **Scale up**: Upgrade Railway plan for higher limits

## Support

- **Full Documentation**: [docs/api-server.md](docs/api-server.md)
- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Issues**: [github.com/teng-lin/notebooklm-py/issues](https://github.com/teng-lin/notebooklm-py/issues)
