"""Kommandozeilen-Runner für Pipeline v1.

Das Skript verbindet Konfiguration, Testset und Pipeline-API zu einem
reproduzierbaren Batch-Lauf und exportiert Ergebnisse, Metriken und
Laufzeitkonfiguration für die Auswertung.
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import src.v1.core.constants as c
from prototype.shared.constants import ENC_UTF8, JSON_INDENT
from prototype.shared.logging_config import configure_logging
from prototype.shared.paths import LEGACY_MUNICIPALITY_CONFIG_PATH, DEFAULT_TESTSET_PATH, V1_OUTPUT_DIR
from src.v1.api.v1_api import run_v1_pipeline
from src.v1.core.response_messages import (
    PIPELINE_CASE_DONE,
    PIPELINE_CASE_START,
    PIPELINE_V1_SUMMARY_HEADER,
)
from src.v1.evaluation import evaluate


config_path = LEGACY_MUNICIPALITY_CONFIG_PATH
testset_path = DEFAULT_TESTSET_PATH
output_path = V1_OUTPUT_DIR

results_csv_path = output_path / c.FILENAME_V1_RESULTS_CSV
metrics_json_path = output_path / c.FILENAME_V1_METRICS_JSON
config_json_path = output_path / c.FILENAME_V1_CONFIG_JSON

output_path.mkdir(parents=True, exist_ok=True)
configure_logging()


def load_config(path):
    return yaml.safe_load(path.read_text(encoding=ENC_UTF8))


config = load_config(config_path)
testset = pd.read_csv(testset_path)

results = []
total_cases = len(testset)

for index, row in testset.iterrows():
    case_start = time.time()

    print(PIPELINE_CASE_START.format(
        index=index + 1,
        total=total_cases,
        case_id=row[c.K_CASE_ID],
    ))

    result = run_v1_pipeline(
        inquiry_text=row[c.K_TEXT],
        config=config,
        row_metadata=row,
    )

    case_duration = result.get(c.K_PROCESSING_TIME, time.time() - case_start)
    results.append(result)

    print(PIPELINE_CASE_DONE.format(
        predicted_team=result.get(c.K_PREDICTED_TEAM),
        routing_status=result.get(c.K_ROUTING_STATUS),
        case_duration=case_duration,
    ))


df_results, metrics = evaluate(results)

df_results.to_csv(results_csv_path, index=False)

metrics_json_path.write_text(
    json.dumps(metrics, indent=JSON_INDENT, ensure_ascii=False),
    encoding=ENC_UTF8,
)

v1_config = {
    c.K_VERSION: c.PIPELINE_VERSION_V1,
    c.K_FEATURES: c.V1_PIPELINE_FEATURES,
    c.K_CONFIG_FILE: str(config_path),
    c.K_TESTSET_FILE: str(testset_path),
    c.K_OUTPUT_FILES: {
        c.K_RESULTS_CSV: str(results_csv_path),
        c.K_METRICS_JSON: str(metrics_json_path),
        c.K_CONFIG_JSON: str(config_json_path),
    },
}

config_json_path.write_text(
    json.dumps(v1_config, indent=JSON_INDENT, ensure_ascii=False),
    encoding=ENC_UTF8,
)

print(PIPELINE_V1_SUMMARY_HEADER)
print(metrics)
