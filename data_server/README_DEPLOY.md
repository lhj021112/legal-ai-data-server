# Data Server Render Deployment

This folder contains the FastAPI Data Server for the legal case search project.

## Render Settings

Use these values when creating a Render Web Service.

- Root Directory: `data_server`
- Environment: `Python 3`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Environment Variables

Add these variables in Render.

```env
DATABASE_URL=postgresql://postgres.PROJECT_ID:DB_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres
ADMIN_API_KEY=change-this-to-a-private-random-value
CORS_ALLOW_ORIGINS=*
PYTHON_VERSION=3.11.9
```

Do not commit the local `.env` file to GitHub.

## Health Check

After deployment, check:

```text
https://YOUR_RENDER_SERVICE.onrender.com/health
```

Expected response:

```json
{"status":"ok"}
```

## Initialize Tables

The deployed app does not create tables during startup. If the database is empty,
run this once from a trusted local machine or Render Shell:

```bash
python scripts/init_db.py
```

## API Docs

```text
https://YOUR_RENDER_SERVICE.onrender.com/docs
```

## Search Example

```text
https://YOUR_RENDER_SERVICE.onrender.com/cases/search?q=명의신탁
```

## Protected Write APIs

Write/import APIs require the `X-Admin-API-Key` header.

```bash
curl -X POST "https://YOUR_RENDER_SERVICE.onrender.com/cases/import-file" \
  -H "X-Admin-API-Key: YOUR_ADMIN_API_KEY" \
  -F "file=@case.txt"
```

## Upload Files From Terminal

```bash
python scripts/upload_files.py ./data/raw_cases \
  --server-url https://YOUR_RENDER_SERVICE.onrender.com \
  --admin-api-key YOUR_ADMIN_API_KEY
```
