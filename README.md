# Weefin API

FastAPI backend for Weefin Terminal.

## Local Development

```bash
cp .env.example .env
# Edit .env: set ESG_DATA_PATH, POLYGON_API_KEY
docker-compose up -d
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

## Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

## Environment Variables (Railway)

| Variable | Description |
|---|---|
| `DATABASE_URL` | Auto-set by Railway PostgreSQL plugin |
| `REDIS_URL` | Auto-set by Railway Redis plugin |
| `POLYGON_API_KEY` | Get free key at polygon.io |
| `ESG_DATA_PATH` | Path to companies.json (set after mounting data) |
| `CORS_ORIGINS` | Comma-separated allowed origins, e.g. `https://terminal.weefin.co` |

## Deployment (Railway)

1. Connect GitHub repo to Railway
2. Add PostgreSQL plugin → DATABASE_URL auto-configured
3. Add Redis plugin → REDIS_URL auto-configured
4. Set remaining env vars in Railway dashboard
5. Railway auto-deploys on push to main
