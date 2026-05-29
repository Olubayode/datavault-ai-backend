# Datavault AI Backend Deployment

## Local Run

From the project root:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Open:

```text
http://localhost:8010/docs
```

## Render Deployment

1. Push this folder to GitHub.
2. In Render, create a new Blueprint from the GitHub repo.
3. Render will read `render.yaml`.
4. Add the secret environment variable:

```text
GROQ_API_KEY=your_groq_key
GROQ_FAST_MODEL=llama-3.1-8b-instant
GROQ_COMPLEX_MODEL=llama-3.3-70b-versatile
```

5. Deploy.

Backend start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## API Test

```bash
curl -X POST https://YOUR-RENDER-URL/analytics/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Give me a full real estate analysis with price trends, outliers, missing values, clusters, and useful charts"}'
```

## Production Notes

- Replace the demo CSV path with the uploaded project dataset path from your database.
- Store user uploads in S3, Cloudflare R2, Supabase Storage, or another durable object store.
- Keep `GROQ_API_KEY` in deployment secrets only.
- Use the returned `charts[].figure_json` in React with `react-plotly.js`.
