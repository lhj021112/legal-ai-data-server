# Data Server Render Deployment

This folder contains the FastAPI Data Server for the legal case search project.

## Render Settings

Use these values when creating a Render Web Service.

- Root Directory: `data_server`
- Environment: `Python 3`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Environment Variables

Add this variable in Render.

```env
DATABASE_URL=postgresql://postgres.PROJECT_ID:DB_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres
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

## API Docs

```text
https://YOUR_RENDER_SERVICE.onrender.com/docs
```

## Search Example

```text
https://YOUR_RENDER_SERVICE.onrender.com/cases/search?q=명의신탁
```
