import ast
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from typing import Any, Dict

import numpy as np
import pandas as pd
from openai import OpenAI


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

client = OpenAI(
    api_key=GROQ_API_KEY or "missing-groq-api-key",
    base_url="https://api.groq.com/openai/v1",
)


ALLOWED_IMPORTS = {
    "math",
    "matplotlib",
    "numpy",
    "pandas",
    "plotly",
    "scipy",
    "sklearn",
    "statistics",
    "statsmodels",
}

BANNED_IMPORTS = {
    "builtins",
    "ftplib",
    "glob",
    "http",
    "importlib",
    "joblib",
    "os",
    "pathlib",
    "pickle",
    "requests",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "urllib",
}

BANNED_FUNCTIONS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}


def load_dataset(dataset_path: str) -> pd.DataFrame:
    path = dataset_path.lower()
    if path.endswith(".csv"):
        df = pd.read_csv(dataset_path)
    elif path.endswith((".xls", ".xlsx")):
        df = pd.read_excel(dataset_path)
    else:
        raise ValueError("Unsupported file type. Upload CSV, XLS, or XLSX.")

    df.columns = [
        str(column).strip().replace(" ", "_").replace("-", "_").lower()
        for column in df.columns
    ]
    return df


def get_dataset_profile(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    categorical_columns = [
        column for column in df.columns.tolist() if column not in numeric_columns
    ]

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": df.columns.tolist(),
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "sample_rows": df.head(10).fillna("").to_dict(orient="records"),
        "missing_values": {
            column: int(count) for column, count in df.isna().sum().items()
        },
        "numeric_summary": (
            df[numeric_columns].describe().round(3).fillna("").to_dict()
            if numeric_columns
            else {}
        ),
    }


def extract_code(raw: str) -> str:
    raw = raw.strip()
    fenced = re.search(r"```(?:python)?\s*(.*?)```", raw, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return raw


def generate_analysis_code(question: str, df: pd.DataFrame) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    profile = get_dataset_profile(df)
    prompt = f"""
You are Datavault's autonomous AI analytics engine.

The user uploaded a dataset and asked a question. You must write Python code
that performs the needed calculations, creates useful tables and Plotly charts,
and returns clear insights.

Dataset profile:
{json.dumps(profile, default=str)}

User question:
{question}

Write Python code only. Define exactly one public function:

def analyze(df):
    ...

The function must return a dictionary with this exact structure:

{{
  "answer": "clear answer to the user's question",
  "insights": ["important insight", "another important insight"],
  "tables": [
    {{
      "title": "table title",
      "description": "what this table shows",
      "interpretation": "what this table means in plain English",
      "columns": ["column_a", "column_b"],
      "rows": [
        {{"column_a": "value", "column_b": 123}}
      ]
    }}
  ],
  "charts": [
    {{
      "title": "chart title",
      "type": "plotly",
      "figure_json": "the result of fig.to_json()"
    }}
  ]
}}

Rules:
- Solve the user's analytics question as directly as possible.
- You may calculate summaries, rankings, trends, correlations, regressions,
  forecasts, clusters, outliers, segment comparisons, missing values, KPIs,
  distributions, or other relevant analytics.
- The final answer must always include a useful executive summary with dataset
  overview, key numbers, important findings, and limitations when relevant.
- When available, mention total rows/properties, total columns, average price,
  median price, main outlier finding, and cluster finding directly in the answer.
- Do not give a vague answer like "The analysis provides insights."
- The insights list must include meaningful column-level summary insights when
  those columns exist, such as median price, average surface area, average rooms,
  average listed expenses, most common property type, most common location,
  missing-value hotspots, price-per-square-meter patterns, and date/trend
  patterns.
- For real estate datasets, include these insights when available:
  median price_aprox_usd, average surface_total_in_m2, average rooms, average
  listed expenses, most common property_type, top place_name/state_name, and the
  columns with the most missing values.
- Do not say expenses are USD unless the dataset clearly proves it. Use
  "average listed expenses value" when currency is unclear.
- Insights should be specific and numeric where possible, using commas and
  sensible rounding.
- Use only columns that exist in the dataset.
- Prefer Plotly for all charts.
- Use pandas, numpy, scipy, sklearn, statsmodels, matplotlib, plotly, math, or statistics only.
- For real estate/property datasets, prefer price_aprox_usd over price when
  both columns exist, unless the user asks for local currency.
- For missing values, sort the table from highest missing count to lowest.
- Do not show missing-value rows with 0 unless the user asks for every column.
- Every table must include title, description, interpretation, columns, and rows.
- The table description should explain what the table shows.
- The table interpretation should explain what the user should pay attention to.
- For Outlier Summary, the description must explain the outlier method and
  column used. The interpretation must explain what the outlier count means.
- For Outlier Records, the description must explain that these are sample
  unusual records. The interpretation must explain why the records may matter,
  such as high price, unusual surface area, missing rooms, or data quality issues.
- For outliers, do not return only row indexes. Include useful columns such as
  place_name, property_type, price, price_aprox_usd, surface_total_in_m2,
  rooms, and expenses when available.
- Always return outliers in table format when outliers are detected.
- For outliers, return two tables when possible:
  1. "Outlier Summary" with total_outliers, outlier_method,
     price_column_used, min_outlier_value, and max_outlier_value.
  2. "Outlier Records" with the most useful records only, limited to top 20 rows.
- Include a clear reason column explaining why each outlier row is unusual.
- For outlier tables, explain whether the records suggest unusual data quality,
  extreme values, skewed distribution, or listings that need manual review.
- For real estate outlier explanations, prefer price_aprox_usd,
  surface_total_in_m2, rooms, expenses, price_usd_per_m2, and price_per_m2.
- Avoid using latitude or longitude as the main outlier reason unless the user
  specifically asks for geographic outliers.
- For clustering, do not return one row per original record. Return a cluster
  summary table with cluster, count, average price, average rooms, average
  surface area, and average expenses when available.
- Always return clustering results in table format when clustering is performed.
- The Cluster Summary table must include cluster, count, average_price,
  median_price, average_surface_area, average_rooms, average_expenses, and
  cluster_description when possible.
- For Cluster Summary, every row must include the cluster number in the cluster
  field. Do not omit the cluster value from any row.
- For Cluster Summary, the description must explain that the table groups
  similar properties. The interpretation must explain what each cluster likely
  represents.
- Do not show raw cluster labels alone without explaining what each cluster means.
- For cluster tables, explain what each cluster likely represents in plain English.
- Cluster descriptions must be specific and based on average_price,
  median_price, average_surface_area, average_rooms, average_expenses, and count.
- Do not use generic cluster descriptions like "groups listings with similar values."
- If a cluster has a very small count, say it may represent unusual listings or
  data-quality issues.
- If clustering is performed on a sample, clearly say the cluster counts are
  based on sampled valid records, not the full dataset.
- For real estate data, use business-friendly phrases such as "typical
  mid-market listings", "high-price luxury listings", "large-surface
  properties", "small unusual cluster", "possible data-quality issue", or
  "larger family-style properties" when supported by the values.
- Do not show standardized/scaled values in cluster summary tables.
- If clustering uses StandardScaler, use scaled values only to fit the model.
  Calculate displayed cluster averages from the original unscaled dataframe.
- Every table row must be a dictionary keyed by column name. Do not return table
  rows as lists.
- For large datasets, limit tables to the top 10 or top 20 most useful rows.
- Format important numbers in answers and insights with commas and sensible
  rounding instead of long raw decimals.
- Do not assume expenses are in USD unless the dataset clearly says so. Say
  "listed expenses value" when the currency is unclear.
- If a chart is created, the chart title must clearly explain what the chart shows.
- A helper function safe_numeric_frame(df) is already available. Use it for
  correlations, clustering, regression, forecasting, outlier detection, and
  machine learning.
- Never call df.corr() directly. Use safe_numeric_frame(df).corr().
- Never pass raw df values into sklearn. Use safe_numeric_frame(df), then select
  useful numeric columns.
- Before KMeans, regression, PCA, or any sklearn model, make sure the input has
  no NaN or infinite values.
- If there are not enough numeric columns for an advanced method, fall back to
  summary, rankings, distributions, and missing-value analysis.
- Do not use Streamlit.
- Do not read files.
- Do not write files.
- Do not access the network.
- Do not use os, sys, subprocess, requests, socket, pathlib, pickle, joblib,
  importlib, open, eval, exec, globals, locals, or __import__.
- Make the result JSON serializable.
- If the question is ambiguous, perform the most useful general analysis.
- Return only Python code. No markdown fences. No explanation outside code.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior data analyst. You write safe Python "
                    "analysis functions only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return extract_code(response.choices[0].message.content)


def validate_code_safety(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"Generated code has syntax error: {exc}") from exc

    analyze_functions = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "analyze"
    ]
    if len(analyze_functions) != 1:
        raise ValueError("Generated code must define exactly one analyze(df) function.")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            else:
                imported_names = [node.module or ""]

            for name in imported_names:
                top_level_name = name.split(".")[0]
                if top_level_name in BANNED_IMPORTS:
                    raise ValueError(f"Unsafe import blocked: {name}")
                if top_level_name not in ALLOWED_IMPORTS:
                    raise ValueError(f"Import not allowed: {name}")

        if isinstance(node, ast.Name) and node.id in BANNED_FUNCTIONS:
            raise ValueError(f"Unsafe function blocked: {node.id}")

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in BANNED_FUNCTIONS:
                raise ValueError(f"Unsafe function call blocked: {node.func.id}")

        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Unsafe dunder attribute blocked.")


def run_analysis_code_safely(
    code: str,
    df: pd.DataFrame,
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    validate_code_safety(code)

    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_path = os.path.join(tmpdir, "dataset.csv")
        runner_path = os.path.join(tmpdir, "runner.py")
        df.to_csv(dataset_path, index=False)

        runner_code = f"""
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_csv({dataset_path!r})

for column in df.columns:
    if df[column].dtype == "object":
        converted = pd.to_numeric(df[column], errors="coerce")
        if converted.notna().sum() >= max(3, int(len(df) * 0.3)):
            df[column] = converted

def safe_numeric_frame(input_df):
    numeric_df = input_df.select_dtypes(include=[np.number]).copy()
    numeric_df = numeric_df.replace([np.inf, -np.inf], np.nan)
    numeric_df = numeric_df.dropna(axis=1, how="all")

    for column in numeric_df.columns:
        if numeric_df[column].isna().any():
            median_value = numeric_df[column].median()
            if pd.isna(median_value):
                median_value = 0
            numeric_df[column] = numeric_df[column].fillna(median_value)

    return numeric_df

{code}

result = analyze(df)

def make_json_safe(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    return str(value)

print(json.dumps(result, default=make_json_safe))
"""
        with open(runner_path, "w", encoding="utf-8") as file:
            file.write(textwrap.dedent(runner_code))

        safe_env = {
            key: value
            for key, value in os.environ.items()
            if "KEY" not in key.upper()
            and "TOKEN" not in key.upper()
            and "SECRET" not in key.upper()
            and "PASSWORD" not in key.upper()
        }
        safe_env["MPLBACKEND"] = "Agg"

        completed = subprocess.run(
            [sys.executable, runner_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=safe_env,
        )

    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Analysis code failed.")

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Analysis did not return valid JSON.") from exc

    if not isinstance(result, dict):
        raise RuntimeError("Analysis result must be a JSON object.")

    result.setdefault("answer", "Analysis completed.")
    result.setdefault("insights", [])
    result.setdefault("tables", [])
    result.setdefault("charts", [])
    return normalize_result(result)


def repair_analysis_code(
    question: str,
    df: pd.DataFrame,
    failed_code: str,
    error: Exception,
) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    prompt = f"""
The previous Datavault analytics code failed.

User question:
{question}

Dataset columns:
{df.columns.tolist()}

Error:
{str(error)}

Failed code:
{failed_code}

Write corrected Python code only.

It must define:
def analyze(df):
    ...

It must return answer, insights, tables, and charts.
Use Plotly figures with fig.to_json().
Important repair rules:
- The answer must include a useful executive summary, not a vague sentence.
- Mention total rows/properties, total columns, average price, median price, main
  outlier finding, and cluster finding when available.
- The insights list must include meaningful column-level summary insights when
  available, including median price, average surface area, average rooms, average
  listed expenses, most common property type, most common location, top missing
  columns, and price-per-square-meter patterns.
- Do not say expenses are USD unless the dataset clearly proves it. Use
  "listed expenses value" when currency is unclear.
- Use safe_numeric_frame(df) for all numeric analytics.
- Do not call df.corr() directly.
- Do not pass NaN values into sklearn.
- For KMeans, PCA, regression, forecasting, or outlier detection, use only
  safe_numeric_frame(df).
- For clustering, always include cluster count plus average metrics in the
  cluster summary table.
- Cluster Summary must include cluster, count, average_price, median_price,
  average_surface_area, average_rooms, average_expenses, and cluster_description
  when those fields can be calculated.
- Every Cluster Summary row must include the cluster number in the cluster field.
- Cluster Summary must include description and interpretation explaining what
  the clusters represent.
- Cluster descriptions must be specific and based on actual displayed values.
- Do not use generic descriptions like "groups listings with similar values."
- If a cluster has a very small count, say it may represent unusual listings or
  data-quality issues.
- If clustering is performed on a sample, clearly say counts are based on sampled
  valid records.
- Do not show standardized/scaled values in Cluster Summary. If StandardScaler is
  used, calculate displayed cluster averages from the original unscaled dataframe.
- Outlier results must include an Outlier Summary table and an Outlier Records
  table with useful property details and a reason column when possible.
- Outlier Summary must include description and interpretation explaining the
  outlier method, column used, and what the outlier count means.
- Outlier Records must include description and interpretation explaining why
  the sample rows matter.
- For outliers, avoid latitude/longitude as the reason unless the user asks for
  geographic outliers. Prefer price, surface area, rooms, expenses, and price per
  square meter.
- Every table row must be a dictionary keyed by column name. Do not return table
  rows as lists.
- Every table must include title, description, interpretation, columns, and rows.
- Do not assume expenses are in USD unless the dataset clearly says so.
- If advanced analytics are not possible, return useful summary insights instead.
Do not include markdown fences.
Do not use unsafe imports, file operations, network calls, os, sys, subprocess,
requests, pathlib, open, eval, exec, importlib, pickle, or joblib.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You fix Python analytics code and return code only.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return extract_code(response.choices[0].message.content)


def make_compact_result_for_polish(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    compact = {
        "answer": raw_result.get("answer", ""),
        "insights": raw_result.get("insights", []),
        "tables": [],
        "charts": [],
    }

    for table in raw_result.get("tables", [])[:3]:
        rows = table.get("rows", [])
        compact["tables"].append(
            {
                "title": table.get("title", "Table"),
                "description": table.get("description", ""),
                "interpretation": table.get("interpretation", ""),
                "columns": table.get("columns", []),
                "sample_rows": rows[:10],
                "row_count": len(rows),
            }
        )

    for chart in raw_result.get("charts", [])[:5]:
        compact["charts"].append(
            {
                "title": chart.get("title", "Chart"),
                "type": chart.get("type", "plotly"),
                "has_figure_json": bool(chart.get("figure_json")),
            }
        )

    return compact


def clean_json_value(value: Any) -> Any:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if hasattr(value, "item"):
        return clean_json_value(value.item())

    if isinstance(value, dict):
        return {str(key): clean_json_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [clean_json_value(item) for item in value]

    return value


def normalize_table(table: Dict[str, Any]) -> Dict[str, Any]:
    columns = [str(column) for column in table.get("columns", [])]
    rows = table.get("rows", [])
    normalized_rows = []
    title = table.get("title", "Table")
    description = table.get("description") or f"This table shows {title.lower()}."
    interpretation = table.get("interpretation") or (
        "Review the rows and compare the values to understand the main pattern."
    )

    for row in rows:
        if isinstance(row, dict):
            normalized_rows.append(clean_json_value(row))
        elif isinstance(row, list):
            normalized_rows.append(
                {
                    column: clean_json_value(row[index])
                    if index < len(row)
                    else None
                    for index, column in enumerate(columns)
                }
            )
        else:
            normalized_rows.append({"value": clean_json_value(row)})

    return {
        "title": title,
        "description": description,
        "interpretation": interpretation,
        "columns": columns,
        "rows": normalized_rows,
    }


def normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    normalized = clean_json_value(result)
    normalized["tables"] = [
        normalize_table(table)
        for table in normalized.get("tables", [])
        if isinstance(table, dict)
    ]
    normalized.setdefault("answer", "Analysis completed.")
    normalized.setdefault("insights", [])
    normalized.setdefault("charts", [])
    return normalized


def ai_unavailable_response(question: str, error: Exception | str) -> Dict[str, Any]:
    message = str(error)
    is_rate_limited = "rate" in message.lower() or "429" in message
    reason = (
        "Groq was rate-limited"
        if is_rate_limited
        else "the AI analysis service is temporarily unavailable"
    )

    return normalize_result(
        {
            "question": question,
            "answer": (
                f"AI analysis is temporarily unavailable because {reason}. "
                "Kindly come back later."
            ),
            "analysis_mode": "ai_unavailable",
            "insights": [
                "AI analysis is temporarily unavailable.",
                f"Reason: {reason}.",
                "Kindly come back later and try the same question again.",
            ],
            "recommended_followups": [
                "Try again later",
                "Check Groq usage limits",
            ],
            "tables": [],
            "charts": [],
            "debug_code": None,
        }
    )


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def numeric_series(df: pd.DataFrame, column: str | None) -> pd.Series:
    if not column or column not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def table(
    title: str,
    description: str,
    interpretation: str,
    rows: list[Dict[str, Any]],
    columns: list[str] | None = None,
) -> Dict[str, Any]:
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    return {
        "title": title,
        "description": description,
        "interpretation": interpretation,
        "columns": columns,
        "rows": rows,
    }


def describe_cluster(
    row: Dict[str, Any],
    global_price_median: float | None,
    global_surface_median: float | None,
    global_rooms_median: float | None,
) -> str:
    count = int(row.get("count") or 0)
    avg_price = row.get("average_price")
    avg_surface = row.get("average_surface_area")
    avg_rooms = row.get("average_rooms")

    parts = []

    if count <= 10:
        parts.append("small unusual cluster that may represent special-case listings or data-quality issues")
    elif global_price_median is not None and avg_price is not None:
        if avg_price >= global_price_median * 3:
            parts.append("high-price luxury listings")
        elif avg_price >= global_price_median * 1.5:
            parts.append("upper-market listings")
        elif avg_price <= global_price_median * 0.6:
            parts.append("lower-price listings")
        else:
            parts.append("typical mid-market listings")

    if global_surface_median is not None and avg_surface is not None:
        if avg_surface >= global_surface_median * 3:
            parts.append("large-surface properties")
        elif avg_surface <= global_surface_median * 0.6:
            parts.append("smaller-surface properties")

    if global_rooms_median is not None and avg_rooms is not None:
        if avg_rooms >= global_rooms_median * 1.8:
            parts.append("larger family-style properties")
        elif avg_rooms <= max(1, global_rooms_median * 0.7):
            parts.append("lower-room-count listings")

    if not parts:
        parts.append("properties with a balanced profile across the selected metrics")

    return f"Cluster {int(row.get('cluster', 0))} appears to represent " + ", ".join(parts) + "."


def fallback_analysis(question: str, df: pd.DataFrame, errors: list[str]) -> Dict[str, Any]:
    import plotly.express as px

    rows_count = int(len(df))
    column_count = int(len(df.columns))
    price_col = first_existing_column(
        df,
        ["price_aprox_usd", "price_usd", "price", "price_aprox_local_currency"],
    )
    surface_col = first_existing_column(df, ["surface_total_in_m2", "surface_covered_in_m2"])
    rooms_col = first_existing_column(df, ["rooms", "bedrooms"])
    expenses_col = first_existing_column(df, ["expenses"])
    property_type_col = first_existing_column(df, ["property_type", "type"])
    location_col = first_existing_column(df, ["place_name", "state_name", "city", "region"])

    price = numeric_series(df, price_col)
    surface = numeric_series(df, surface_col)
    rooms = numeric_series(df, rooms_col)
    expenses = numeric_series(df, expenses_col)

    avg_price = float(price.mean()) if price.notna().any() else None
    median_price = float(price.median()) if price.notna().any() else None
    avg_surface = float(surface.mean()) if surface.notna().any() else None
    avg_rooms = float(rooms.mean()) if rooms.notna().any() else None
    avg_expenses = float(expenses.mean()) if expenses.notna().any() else None

    insights = [
        f"The dataset contains {rows_count:,} rows and {column_count:,} columns.",
    ]
    if median_price is not None and price_col:
        insights.append(f"The median {price_col} is {median_price:,.2f}.")
    if avg_surface is not None and surface_col:
        insights.append(f"The average {surface_col} is {avg_surface:,.2f}.")
    if avg_rooms is not None and rooms_col:
        insights.append(f"The average {rooms_col} value is {avg_rooms:,.2f}.")
    if avg_expenses is not None and expenses_col:
        insights.append(f"The average listed expenses value is {avg_expenses:,.2f}.")
    if property_type_col:
        mode = df[property_type_col].dropna().mode()
        if not mode.empty:
            insights.append(f"The most common {property_type_col} is {mode.iloc[0]}.")
    if location_col:
        mode = df[location_col].dropna().mode()
        if not mode.empty:
            insights.append(f"The most common {location_col} is {mode.iloc[0]}.")

    missing = (
        df.isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "column", 0: "missing_count"})
    )
    missing = missing[missing["missing_count"] > 0].sort_values(
        "missing_count", ascending=False
    )
    missing_rows = missing.head(20).to_dict(orient="records")
    if missing_rows:
        top_missing = missing_rows[0]
        insights.append(
            f"The largest missing-value hotspot is {top_missing['column']} "
            f"with {int(top_missing['missing_count']):,} missing values."
        )

    tables = [
        table(
            "Missing Values",
            "This table lists the columns with missing data, sorted from highest to lowest missing count.",
            "High missing counts point to fields that may need cleaning or careful handling before modeling or reporting.",
            missing_rows,
            ["column", "missing_count"],
        )
    ]

    if price_col and price.notna().any():
        summary_rows = [
            {"statistic": "count", "value": int(price.count())},
            {"statistic": "mean", "value": avg_price},
            {"statistic": "median", "value": median_price},
            {"statistic": "min", "value": float(price.min())},
            {"statistic": "max", "value": float(price.max())},
        ]
        tables.insert(
            0,
            table(
                "Price Summary",
                f"This table summarizes the main distribution statistics for {price_col}.",
                "Compare mean and median to understand skew. A mean much larger than the median usually suggests high-value outliers.",
                summary_rows,
                ["statistic", "value"],
            ),
        )

        q1 = price.quantile(0.25)
        q3 = price.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_mask = price.notna() & ((price < lower) | (price > upper))
        outlier_count = int(outlier_mask.sum())
        outlier_prices = price[outlier_mask]

        if outlier_count:
            insights.append(
                f"Using the IQR method on {price_col}, {outlier_count:,} price outliers were detected."
            )
            tables.append(
                table(
                    "Outlier Summary",
                    f"This table summarizes price outliers detected with the IQR method using {price_col}.",
                    "A large outlier count means the price distribution is skewed. These may be luxury listings, unusual listings, or records that need data-quality review.",
                    [
                        {
                            "total_outliers": outlier_count,
                            "outlier_method": "IQR",
                            "price_column_used": price_col,
                            "min_outlier_value": float(outlier_prices.min()),
                            "max_outlier_value": float(outlier_prices.max()),
                        }
                    ],
                    [
                        "total_outliers",
                        "outlier_method",
                        "price_column_used",
                        "min_outlier_value",
                        "max_outlier_value",
                    ],
                )
            )

            useful_cols = [
                column
                for column in [
                    location_col,
                    property_type_col,
                    "price",
                    "price_aprox_usd",
                    surface_col,
                    rooms_col,
                    expenses_col,
                ]
                if column and column in df.columns
            ]
            outlier_records = df.loc[outlier_mask, useful_cols].copy()
            outlier_records["reason"] = np.where(
                price[outlier_mask] > upper,
                f"High {price_col} compared with typical listings",
                f"Low {price_col} compared with typical listings",
            )
            tables.append(
                table(
                    "Outlier Records",
                    "This table shows sample records flagged as price outliers.",
                    "Review these listings before pricing models or averages because extreme values can strongly affect results.",
                    outlier_records.head(20).to_dict(orient="records"),
                    useful_cols + ["reason"],
                )
            )

    charts = []
    if price_col and price.notna().any():
        chart_df = pd.DataFrame({price_col: price.dropna()})
        charts.append(
            {
                "title": f"{price_col} Distribution",
                "type": "plotly",
                "figure_json": px.histogram(
                    chart_df,
                    x=price_col,
                    nbins=50,
                    title=f"{price_col} Distribution",
                ).to_json(),
            }
        )

    if location_col and price_col:
        location_prices = df.copy()
        location_prices[price_col] = price
        grouped = (
            location_prices.dropna(subset=[location_col, price_col])
            .groupby(location_col)[price_col]
            .mean()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        if not grouped.empty:
            charts.append(
                {
                    "title": f"Average {price_col} by {location_col}",
                    "type": "plotly",
                    "figure_json": px.bar(
                        grouped,
                        x=location_col,
                        y=price_col,
                        title=f"Average {price_col} by {location_col}",
                    ).to_json(),
                }
            )

    if price_col and surface_col:
        scatter_df = df[[price_col, surface_col]].copy()
        scatter_df[price_col] = price
        scatter_df[surface_col] = surface
        scatter_df = scatter_df.dropna().head(5000)
        if not scatter_df.empty:
            charts.append(
                {
                    "title": f"{price_col} vs {surface_col}",
                    "type": "plotly",
                    "figure_json": px.scatter(
                        scatter_df,
                        x=surface_col,
                        y=price_col,
                        title=f"{price_col} vs {surface_col}",
                    ).to_json(),
                }
            )

    cluster_feature_cols = [
        column
        for column in [price_col, surface_col, rooms_col, expenses_col]
        if column and column in df.columns
    ]
    if len(cluster_feature_cols) >= 2:
        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler

            cluster_original = df[cluster_feature_cols].apply(
                pd.to_numeric, errors="coerce"
            )
            cluster_original = cluster_original.replace([np.inf, -np.inf], np.nan)
            cluster_original = cluster_original.dropna(how="all")
            for column in cluster_original.columns:
                cluster_original[column] = cluster_original[column].fillna(
                    cluster_original[column].median()
                )

            if len(cluster_original) >= 10:
                sample_original = cluster_original.sample(
                    min(len(cluster_original), 10000), random_state=42
                )
                scaled = StandardScaler().fit_transform(sample_original)
                n_clusters = min(5, max(2, len(sample_original) // 500))
                labels = KMeans(
                    n_clusters=n_clusters,
                    random_state=42,
                    n_init=10,
                ).fit_predict(scaled)
                sample_with_labels = sample_original.copy()
                sample_with_labels["cluster"] = labels
                cluster_rows = []
                global_price_median = (
                    float(sample_original[price_col].median())
                    if price_col in sample_original
                    else None
                )
                global_surface_median = (
                    float(sample_original[surface_col].median())
                    if surface_col in sample_original
                    else None
                )
                global_rooms_median = (
                    float(sample_original[rooms_col].median())
                    if rooms_col in sample_original
                    else None
                )
                for cluster_id, group in sample_with_labels.groupby("cluster"):
                    row = {
                        "cluster": int(cluster_id),
                        "count": int(len(group)),
                    }
                    if price_col in group:
                        row["average_price"] = float(group[price_col].mean())
                        row["median_price"] = float(group[price_col].median())
                    if surface_col in group:
                        row["average_surface_area"] = float(group[surface_col].mean())
                    if rooms_col in group:
                        row["average_rooms"] = float(group[rooms_col].mean())
                    if expenses_col in group:
                        row["average_expenses"] = float(group[expenses_col].mean())
                    row["cluster_description"] = describe_cluster(
                        row,
                        global_price_median,
                        global_surface_median,
                        global_rooms_median,
                    )
                    cluster_rows.append(row)

                cluster_columns = [
                    "cluster",
                    "count",
                    "average_price",
                    "median_price",
                    "average_surface_area",
                    "average_rooms",
                    "average_expenses",
                    "cluster_description",
                ]
                tables.append(
                    table(
                        "Cluster Summary",
                        f"This table groups {len(sample_original):,} sampled valid records by price, surface area, rooms, and expenses.",
                        "Cluster counts are based on sampled valid records, not necessarily the full dataset. Very small clusters may represent unusual listings or data-quality issues.",
                        cluster_rows,
                        cluster_columns,
                    )
                )
                insights.append(
                    f"Clustering found {len(cluster_rows)} property groups using original unscaled values for the displayed summary."
                )
        except Exception:
            pass

    if avg_price is not None and median_price is not None:
        answer = (
            f"The dataset contains {rows_count:,} properties across {column_count:,} columns. "
            f"The average {price_col} is {avg_price:,.2f}, while the median is {median_price:,.2f}. "
            "The analysis includes column summaries, missing-value hotspots, price outliers, "
            "and visual charts for market patterns."
        )
    else:
        answer = (
            f"The dataset contains {rows_count:,} rows across {column_count:,} columns. "
            "The analysis includes column summaries, missing-value hotspots, and useful charts."
        )

    if errors and os.getenv("SHOW_AI_CODE") == "true":
        insights.extend([f"AI generated code error: {error}" for error in errors])

    return normalize_result(
        {
            "question": question,
            "answer": answer,
            "insights": insights,
            "recommended_followups": [
                "Compare average price by property type",
                "Show the most expensive locations",
                "Explain the outlier records",
            ],
            "tables": tables,
            "charts": charts,
            "debug_code": None,
        }
    )


def polish_response(question: str, raw_result: Dict[str, Any]) -> Dict[str, Any]:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    compact_result = make_compact_result_for_polish(raw_result)

    prompt = f"""
You are Datavault's final analytics explainer.

User question:
{question}

Computed analytics result summary:
{json.dumps(compact_result, default=str)}

Return valid JSON only:
{{
  "answer": "polished answer",
  "insights": ["insight 1", "insight 2"],
  "recommended_followups": ["follow-up question 1", "follow-up question 2"]
}}

Rules:
- Do not invent numbers.
- Use only the computed analytics result summary.
- Keep it clear and useful.
- Mention chart/table titles when relevant.
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "answer": raw_result.get("answer", "Analysis completed."),
            "insights": raw_result.get("insights", []),
            "recommended_followups": [],
        }


def answer_dataset_question_with_ai(question: str, dataset_path: str) -> Dict[str, Any]:
    df = load_dataset(dataset_path)

    try:
        generated_code = generate_analysis_code(question, df)
    except Exception as ai_error:
        return ai_unavailable_response(question, ai_error)

    try:
        raw_result = run_analysis_code_safely(generated_code, df)
    except Exception as first_error:
        try:
            repaired_code = repair_analysis_code(question, df, generated_code, first_error)
        except Exception as repair_error:
            return ai_unavailable_response(question, repair_error)

        try:
            raw_result = run_analysis_code_safely(repaired_code, df)
            generated_code = repaired_code
        except Exception as second_error:
            return ai_unavailable_response(question, second_error)

    try:
        polished = polish_response(question, raw_result)
    except Exception:
        polished = {
            "answer": raw_result.get("answer"),
            "insights": raw_result.get("insights", []),
            "recommended_followups": raw_result.get("recommended_followups", []),
        }

    return normalize_result({
        "question": question,
        "answer": polished.get("answer", raw_result.get("answer")),
        "analysis_mode": "ai_generated",
        "insights": polished.get("insights", raw_result.get("insights", [])),
        "recommended_followups": polished.get("recommended_followups", []),
        "tables": raw_result.get("tables", []),
        "charts": raw_result.get("charts", []),
        "debug_code": generated_code if os.getenv("SHOW_AI_CODE") == "true" else None,
    })
