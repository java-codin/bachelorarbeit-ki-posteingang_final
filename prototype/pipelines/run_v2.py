"""Kommandozeilen-Runner für Pipeline v2.

Die Datei baut Wissensbasis und Vector Store für das Chunking-Experiment auf,
führt alle Testfälle aus und dokumentiert Ergebnisse samt Embedding- und
Retrieval-Metadaten.
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


import src.v2.core.constants as c
from prototype.shared.constants import ENC_UTF8, JSON_INDENT
from prototype.shared.logging_config import configure_logging
from prototype.shared.paths import (
    LEGACY_MUNICIPALITY_CONFIG_PATH,
    DEFAULT_TESTSET_PATH,
    KNOWLEDGE_BASE_V2_PATH,
    V2_OUTPUT_DIR,
)
from src.v2.api.v2_api import run_v2_pipeline
from src.v2.chunking.structure_chunking import create_chunks
from src.v2.core.response_messages import (
    PIPELINE_CASE_DONE,
    PIPELINE_CASE_START,
    PIPELINE_V2_SUMMARY_HEADER,
)
from src.v2.evaluation import evaluate
from src.v2.knowledge_loader import load_knowledge_base
from src.v2.retrieval import build_vector_store
from src.v2.embeddings import get_embedding_metadata


config_path = LEGACY_MUNICIPALITY_CONFIG_PATH
testset_path = DEFAULT_TESTSET_PATH
knowledge_base_path = KNOWLEDGE_BASE_V2_PATH
output_path = V2_OUTPUT_DIR

results_csv_path = output_path / c.FILENAME_V2_RESULTS_CSV
metrics_json_path = output_path / c.FILENAME_V2_METRICS_JSON
config_json_path = output_path / c.FILENAME_V2_CONFIG_JSON

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
        case_id=row[c.K_CASE_ID],
    ))

    result = run_v2_pipeline(
        inquiry_text=row[c.K_TEXT],
        config=config,
        vector_store=vector_store,
        row_metadata=row,
    )

    case_duration = result.get(c.K_PROCESSING_TIME, time.time() - case_start)
    results.append(result)

    print(PIPELINE_CASE_DONE.format(
        predicted_team=result.get(c.K_PREDICTED_TEAM),
        source_count=len(result.get(c.K_RETRIEVED_SOURCES, [])),
        case_duration=case_duration,
    ))


df_results, metrics = evaluate(results)

df_results.to_csv(results_csv_path, index=False)

metrics_json_path.write_text(
    json.dumps(metrics, indent=JSON_INDENT, ensure_ascii=False),
    encoding=ENC_UTF8,
)

embedding_metadata = get_embedding_metadata()

v2_config = {
    c.K_VERSION: c.PIPELINE_VERSION_V2,
    c.K_FEATURES: c.V2_PIPELINE_FEATURES,
    c.K_CHUNKING: c.CHUNKING_STRATEGY,
    c.K_RETRIEVAL: c.RETRIEVAL_K,
    c.K_EMBEDDING_MODEL: embedding_metadata[c.K_EMBEDDING_MODEL],
    c.K_EMBEDDING_PROVIDER: embedding_metadata[c.K_EMBEDDING_PROVIDER],
    c.K_CONFIG_FILE: str(config_path),
    c.K_TESTSET_FILE: str(testset_path),
    c.K_KNOWLEDGE_BASE: str(knowledge_base_path),
    c.K_OUTPUT_FILES: {
        c.K_RESULTS_CSV: str(results_csv_path),
        c.K_METRICS_JSON: str(metrics_json_path),
        c.K_CONFIG_JSON: str(config_json_path),
    },
}

config_json_path.write_text(
    json.dumps(v2_config, indent=JSON_INDENT, ensure_ascii=False),
    encoding=ENC_UTF8,
)

print(PIPELINE_V2_SUMMARY_HEADER)
print(metrics)
