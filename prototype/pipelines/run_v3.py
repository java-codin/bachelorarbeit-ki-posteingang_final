"""Kommandozeilen-Runner für Pipeline v3.

Der Batch-Lauf ergänzt die früheren RAG-Schritte um Robustheits- und
Guardrail-Auswertungen und schreibt neben Ergebnissen auch ein Audit-Log für
die nachvollziehbare Evaluation.
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


import src.v3.core.constants as v3c
from prototype.shared.constants import ENC_UTF8, JSON_INDENT
from prototype.shared.logging_config import configure_logging
from prototype.shared.paths import (
    LEGACY_MUNICIPALITY_CONFIG_PATH,
    DEFAULT_TESTSET_PATH,
    V3_OUTPUT_DIR, knowledge_base_path_for_version,
)
from src.v3.api.v3_api import run_v3_pipeline
from src.v3.retrieval import build_vector_store
from src.v3.knowledge_loader import load_knowledge_base
from src.v3.chunking.structure_chunking import create_chunks
from src.v3.logging_audit import log_decision
from src.v3.evaluation import evaluate
from src.v3.core.response_messages import (
    PIPELINE_CASE_DONE,
    PIPELINE_CASE_START,
    PIPELINE_V3_SUMMARY_HEADER,
)


config_path = LEGACY_MUNICIPALITY_CONFIG_PATH
testset_path = DEFAULT_TESTSET_PATH
knowledge_base_path = knowledge_base_path_for_version("V3")
output_path = V3_OUTPUT_DIR

results_csv_path = output_path / v3c.FILENAME_V3_RESULTS_CSV
metrics_json_path = output_path / v3c.FILENAME_V3_METRICS_JSON
config_json_path = output_path / v3c.FILENAME_V3_CONFIG_JSON
audit_log_path = output_path / v3c.FILENAME_V3_AUDIT_LOG_JSONL

output_path.mkdir(parents=True, exist_ok=True)
configure_logging()


def load_config(path):
    return yaml.safe_load(path.read_text(encoding=ENC_UTF8))


config = load_config(config_path)
testset = pd.read_csv(testset_path)

documents = load_knowledge_base(knowledge_base_path)
chunks = create_chunks(documents)
vector_store = build_vector_store(chunks)

results = []
total_cases = len(testset)

for index, row in testset.iterrows():
    case_start = time.time()

    print(PIPELINE_CASE_START.format(
        index=index + 1,
        total=total_cases,
        case_id=row[v3c.K_CASE_ID],
    ))

    result = run_v3_pipeline(
        inquiry_text=row[v3c.K_TEXT],
        config=config,
        vector_store=vector_store,
        row_metadata=row
    )

    case_duration = result.get(v3c.K_PROCESSING_TIME, time.time() - case_start)

    results.append(result)
    log_decision(audit_log_path, result)

    print(PIPELINE_CASE_DONE.format(
        injection_detected=result.get(v3c.K_INJECTION_DETECTED),
        no_answer_triggered=result.get(v3c.K_NO_ANSWER_TRIGGERED),
        human_review_required=result.get(v3c.K_HUMAN_REVIEW_REQUIRED),
        guardrail_triggered=result.get(v3c.K_GUARDRAIL_TRIGGERED),
        case_duration=case_duration,
    ))


df_results, metrics = evaluate(results)

df_results.to_csv(results_csv_path, index=False)

metrics_json_path.write_text(
    json.dumps(metrics, indent=JSON_INDENT, ensure_ascii=False),
    encoding=ENC_UTF8
)

v3_config = {
    v3c.K_VERSION: v3c.PIPELINE_VERSION_V3,
    v3c.K_FEATURES: v3c.V3_PIPELINE_FEATURES,
    v3c.K_CONFIG_FILE: str(config_path),
    v3c.K_TESTSET_FILE: str(testset_path),
    v3c.K_KNOWLEDGE_BASE: str(knowledge_base_path),
    v3c.K_RETRIEVAL_K: v3c.RETRIEVAL_K,
    v3c.K_OUTPUT_FILES: {
        v3c.K_RESULTS_CSV: str(results_csv_path),
        v3c.K_METRICS_JSON: str(metrics_json_path),
        v3c.K_CONFIG_JSON: str(config_json_path),
        v3c.K_AUDIT_LOG_JSONL: str(audit_log_path),
    },
}

config_json_path.write_text(
    json.dumps(v3_config, indent=JSON_INDENT, ensure_ascii=False),
    encoding=ENC_UTF8
)

print(PIPELINE_V3_SUMMARY_HEADER)
print(metrics)
