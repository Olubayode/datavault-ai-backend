import json
import os
import re

import plotly.io as pio


with open("ai_result.json", "r", encoding="utf-8") as file:
    result = json.load(file)

os.makedirs("ai_charts", exist_ok=True)

charts = result.get("charts", [])

if not charts:
    print("No charts found in ai_result.json")

for index, chart in enumerate(charts, start=1):
    title = chart.get("title", f"chart_{index}")
    figure_json = chart.get("figure_json")

    if not figure_json:
        print(f"Skipping {title}: no figure_json")
        continue

    safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_").lower()
    output_path = os.path.join("ai_charts", f"{index}_{safe_title}.html")

    fig = pio.from_json(figure_json)
    fig.write_html(output_path)

    print(f"Saved: {output_path}")
