import json

from datavault_ai.ai_analysis_agent import answer_dataset_question_with_ai


result = answer_dataset_question_with_ai(
    question=(
        "Give me a full real estate analysis with price trends, outliers, "
        "location insights, missing values, and useful charts"
    ),
    dataset_path="sample-data/Chile_real_estate_listings.csv",
)

print("\nANSWER:")
print(result.get("answer"))

print("\nINSIGHTS:")
for insight in result.get("insights", []):
    print("-", insight)

print("\nTABLES:")
for table in result.get("tables", []):
    print("\n" + table.get("title", "Untitled Table"))
    if table.get("description"):
        print("Description:", table.get("description"))
    if table.get("interpretation"):
        print("Interpretation:", table.get("interpretation"))
    print("Columns:", table.get("columns"))
    print("First 5 rows:")
    for row in table.get("rows", [])[:5]:
        print(row)

print("\nCHARTS:")
for chart in result.get("charts", []):
    print("-", chart.get("title"))
    print("  Type:", chart.get("type"))
    print("  Has figure_json:", bool(chart.get("figure_json")))

with open("ai_result.json", "w", encoding="utf-8") as file:
    json.dump(result, file, indent=2)

print("\nSaved full result to ai_result.json")
