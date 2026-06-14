"""Kommandozeilen-Runner für die Baseline-Pipeline v0.

Das Skript lädt Testdaten und Konfiguration, führt die einfache Routing-
Baseline aus und schreibt Ergebnis- sowie Metrikartefakte für den
wissenschaftlichen Versionsvergleich.
"""

import json
import yaml
import pandas as pd

from pathlib import Path
from datetime import datetime

from prototype.src.v0.classifier import classify
from prototype.src.v0.router import route
from prototype.src.v0.answer import generate_answer
from prototype.src.v0.evaluation import evaluate

BASE_DIR = Path(__file__).resolve().parent.parent

config_path = BASE_DIR / "config" / "municipality.yaml"
testset_path = BASE_DIR / "data" / "inquiries" / "test_inquiries.csv"
output_path = BASE_DIR / "outputs" / "v0"

output_path.parent.mkdir(parents=True, exist_ok=True)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config(config_path)
testset = pd.read_csv(testset_path)

results = []

for _, row in testset.iterrows():
    inquiry_text = row["text"]

    classification = classify(row["text"], config)
    routing = route(classification, config)
    answer = generate_answer(classification, routing)

    results.append({
        "case_id": row["case_id"],
        "text": inquiry_text,
        "ground_truth_team": row["ground_truth_team"],
        "predicted_team": classification["top_team"],
        "top3": classification["top3"],
        "confidence": classification["confidence"],
        "reason": classification["reason"],
        "matched_keywords": classification["matched_keywords"],
        "target_email": routing["target_email"],
        "routing_status": routing["routing_status"],
        "draft_answer": answer,
        "version": "v0_rule_based_baseline",
        "timestamp": datetime.now().isoformat()
    })

df_results, metrics = evaluate(results)

df_results.to_csv(
    output_path / "v0_results.csv",
    index=False
)

with open(
    output_path / "v0_metrics.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        metrics,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\n===== V0 Rule-Based Baseline =====\n")
print(metrics)
