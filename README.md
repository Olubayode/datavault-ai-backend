# Datavault AI Backend

AI analytics backend for Datavault. This FastAPI service lets users ask natural-language questions about CSV datasets and returns:

- answer
- insights
- tables with descriptions and interpretations
- Plotly chart JSON for frontend rendering

Live API:

```text
https://datavault-ai-backend.onrender.com
```

Swagger docs:

```text
https://datavault-ai-backend.onrender.com/docs
```

---

## Running Locally in Ubuntu/WSL

### 1. Open the project

```bash
cd ~/datavault
```

### 2. Activate the virtual environment

```bash
source venv/bin/activate
```

### 3. Set Groq environment variables

```bash
export GROQ_API_KEY="your_groq_api_key_here"
export GROQ_FAST_MODEL="llama-3.1-8b-instant"
export GROQ_COMPLEX_MODEL="llama-3.3-70b-versatile"
export AI_ANALYSIS_TIMEOUT_SECONDS=60
```

### 4. Run the FastAPI backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Local API:

```text
http://localhost:8010
```

Local Swagger docs:

```text
http://localhost:8010/docs
```

Local health check:

```text
http://localhost:8010/health
```

---

## Testing Analytics Locally

Open:

```text
http://localhost:8010/docs
```

Go to:

```text
POST /analytics/ask
```

Click **Try it out** and use:

```json
{
  "question": "What is the average ticket price?",
  "dataset_path": "sample-data/49ers_ticket_prices.csv"
}
```

Then click **Execute**.

---

## Test Script

You can also test from Ubuntu with:

```bash
cd ~/datavault
source venv/bin/activate
python test_ai.py
```

The script writes the full result to:

```text
ai_result.json
```

To export Plotly charts from `ai_result.json` into standalone HTML files:

```bash
python view_charts.py
explorer.exe ai_charts
```

---

## Push Updates to GitHub

From Ubuntu/WSL:

```bash
cd ~/datavault
git status
git add .
git commit -m "Describe your update"
git push origin main
```

If GitHub asks for login:

```text
Username: Olubayode
Password: paste your GitHub personal access token
```

GitHub repository:

```text
https://github.com/Olubayode/datavault-ai-backend
```

---

## Render Deployment

This backend is deployed on Render from GitHub:

```text
https://github.com/Olubayode/datavault-ai-backend
```

Live backend:

```text
https://datavault-ai-backend.onrender.com
```

Live Swagger docs:

```text
https://datavault-ai-backend.onrender.com/docs
```

Health check:

```text
https://datavault-ai-backend.onrender.com/health
```

Render uses `render.yaml` at the root of the repository.

Required Render environment variables:

```text
GROQ_API_KEY=your_groq_api_key_here
GROQ_FAST_MODEL=llama-3.1-8b-instant
GROQ_COMPLEX_MODEL=llama-3.3-70b-versatile
AI_ANALYSIS_TIMEOUT_SECONDS=60
DEFAULT_DATASET_PATH=sample-data/Chile_real_estate_listings.csv
```

After pushing to GitHub, Render automatically redeploys the latest commit.

---

## Testing the Deployed API

Open:

```text
https://datavault-ai-backend.onrender.com/docs#/analytics/ask_dataset_analytics_ask_post
```

Click **Try it out**.

Example request for the 49ers dataset:

```json
{
  "question": "What is the average ticket price and attendance trend?",
  "dataset_path": "sample-data/49ers_ticket_prices.csv"
}
```

Example request for the Chile real estate dataset:

```json
{
  "question": "Give me a full real estate analysis with price trends, outliers, missing values, clusters, and useful charts",
  "dataset_path": "sample-data/Chile_real_estate_listings.csv"
}
```

Click **Execute**.

The API returns:

```text
answer
insights
tables
charts
```

Charts are returned as Plotly `figure_json`, which the frontend can render with `react-plotly.js`.

---

## Frontend Chart Rendering

In React, install Plotly:

```bash
npm install react-plotly.js plotly.js
```

Example chart renderer:

```jsx
import Plot from "react-plotly.js";

export default function AiCharts({ charts }) {
  if (!charts || charts.length === 0) return null;

  return (
    <div>
      {charts.map((chart, index) => {
        const fig = JSON.parse(chart.figure_json);

        return (
          <div key={index}>
            <h3>{chart.title}</h3>
            <Plot
              data={fig.data}
              layout={fig.layout}
              style={{ width: "100%", height: "450px" }}
              useResizeHandler
            />
          </div>
        );
      })}
    </div>
  );
}
```

The frontend should show:

- answer
- insights
- table title, description, interpretation, and rows
- rendered charts

It should not show raw `figure_json` to users.
