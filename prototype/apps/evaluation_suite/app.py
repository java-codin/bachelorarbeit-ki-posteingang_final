"""Streamlit-App für die interaktive Auswertung der Evaluationssuite.

Sie visualisiert versionierte Ergebnisdateien, Metriken und Fallansichten für
den wissenschaftlichen Vergleich der Prototyp-Iterationen.
"""

import html
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import streamlit as st


CURRENT_FILE = Path(__file__).resolve()
LOCAL_PROTOTYPE_DIR = next(parent for parent in CURRENT_FILE.parents if parent.name == "prototype")
LOCAL_PROJECT_ROOT = LOCAL_PROTOTYPE_DIR.parent

for path in [LOCAL_PROJECT_ROOT, LOCAL_PROTOTYPE_DIR]:
    path_value = str(path)
    if path_value not in sys.path:
        sys.path.insert(0, path_value)

from prototype.shared.bootstrap import ensure_project_import_paths

ensure_project_import_paths(__file__)

from apps.core.ui_styles import apply_app_styles
from evaluation_suite.core.cases import evaluation_cases_path_for_version, load_evaluation_cases
from evaluation_suite.core.run_dirs import RUNS_DIR, create_run_output_dir
from evaluation_suite.core.runner import DEFAULT_OUTPUT_DIR, DEFAULT_VERSIONS, run_evaluation_suite
from prototype.shared.model_profiles import get_active_model_profile_id, load_model_profiles
from prototype.shared.paths import LEGACY_MUNICIPALITY_CONFIG_PATH, V5_MUNICIPALITY_CONFIG_PATH


RECOMMENDED_MODEL_PROFILE_ID = "openai_baseline"
RECOMMENDED_MAX_CASES = 20

RESULTS_FILE = "all_results_long.csv"
METRICS_BY_VERSION_FILE = "metrics_by_version.csv"
METRICS_BY_CATEGORY_FILE = "metrics_by_version_and_category.csv"
METRICS_BY_PROFILE_FILE = "metrics_by_model_profile.csv"
CONFIG_FILE = "evaluation_config.json"

SUMMARY_COLUMNS = [
    "version",
    "total_cases",
    "error_rate",
    "top1_accuracy_strict",
    "top3_accuracy_strict",
    "behavior_match_rate",
    "human_review_rate",
    "used_source_coverage",
    "avg_completeness_score",
    "avg_processing_time_seconds",
]

CASE_COLUMNS = [
    "case_id",
    "version",
    "model_profile_label",
    "category",
    "ground_truth_team",
    "predicted_department",
    "matched_subteam",
    "matched_team",
    "predicted_team",
    "top1_correct_strict",
    "top3_correct_strict",
    "expected_behavior",
    "actual_behavior",
    "behavior_correct",
    "workflow_status",
    "response_mode",
    "risk_score",
    "answer_completeness_score",
    "status",
    "error",
]

METRIC_LABELS = {
    "version": "Version",
    "model_profile_id": "Profil-ID",
    "model_profile_label": "Modellprofil",
    "total_cases": "Fälle",
    "error_rate": "Fehlerquote",
    "top1_accuracy_strict": "Top-1",
    "top3_accuracy_strict": "Top-3",
    "behavior_match_rate": "Regelübereinstimmung",
    "human_review_rate": "Human Review",
    "used_source_coverage": "Quellen genutzt",
    "avg_completeness_score": "Completeness",
    "avg_processing_time_seconds": "Ø Sekunden",
}


st.set_page_config(
    page_title="Haupt-Evaluation",
    page_icon="EV",
    layout="wide",
)


class StreamlitLogHandler(logging.Handler):
    def __init__(self, append_log_line) -> None:
        super().__init__(level=logging.INFO)
        self.append_log_line = append_log_line

    def emit(self, record: logging.LogRecord) -> None:
        self.append_log_line(self.format(record))


def format_path(path: Path) -> str:
    return str(path)


def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def latest_run_output_dir() -> Path | None:
    if not RUNS_DIR.exists():
        return None

    run_dirs = sorted(
        path
        for path in RUNS_DIR.iterdir()
        if path.is_dir() and (path / RESULTS_FILE).exists()
    )
    return run_dirs[-1] if run_dirs else None


def existing_output_dir() -> Path:
    return latest_run_output_dir() or DEFAULT_OUTPUT_DIR


def load_existing_metrics() -> pd.DataFrame | None:
    return load_csv(existing_output_dir() / METRICS_BY_VERSION_FILE)


def load_existing_results() -> pd.DataFrame | None:
    return load_csv(existing_output_dir() / RESULTS_FILE)


def load_existing_category_metrics() -> pd.DataFrame | None:
    return load_csv(existing_output_dir() / METRICS_BY_CATEGORY_FILE)


def load_existing_profile_metrics() -> pd.DataFrame | None:
    return load_csv(existing_output_dir() / METRICS_BY_PROFILE_FILE)


def load_existing_config() -> dict[str, Any] | None:
    return load_json(existing_output_dir() / CONFIG_FILE)


def model_profile_label(profile_id: str, profiles: dict[str, Any]) -> str:
    profile = profiles[profile_id]
    return f"{profile.label} ({profile_id})"


def format_percent(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def format_number(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def selected_run_size(profile_count: int, version_count: int, case_count: int) -> str:
    total = profile_count * version_count * case_count
    return f"{total} Pipeline-Läufe ({profile_count} Profile × {version_count} Versionen × {case_count} Fälle)"


def selected_run_size_by_version(profile_count: int, case_counts_by_version: dict[str, int]) -> str:
    total_cases = sum(case_counts_by_version.values())
    total = profile_count * total_cases
    version_text = ", ".join(
        f"{version}: {count}"
        for version, count in case_counts_by_version.items()
    )
    return f"{total} Pipeline-Läufe ({profile_count} Profile × {total_cases} Fälle; {version_text})"


def testset_summary_text(df: pd.DataFrame) -> str:
    if df.empty:
        return "Keine Testfälle gefunden."

    parts = [f"{len(df)} Fälle"]
    if "category" in df.columns:
        parts.append(f"{df['category'].nunique()} Fallkategorien")
    if "expected_sources" in df.columns:
        parts.append(f"{df['expected_sources'].fillna('').astype(str).str.strip().ne('').sum()} Fälle mit erwarteten Quellen")
    return " · ".join(parts)


def display_last_run_overview(config: dict[str, Any] | None, metrics: pd.DataFrame | None) -> None:
    if not config:
        st.info("Noch kein gespeicherter Haupt-Evaluationslauf vorhanden.")
        return

    profiles = config.get("model_profiles") or []
    profile_labels = [
        profile.get("model_profile_label") or profile.get("model_profile_id") or "-"
        for profile in profiles
        if isinstance(profile, dict)
    ]
    testset_files_by_version = config.get("testset_files_by_version") or {}
    if testset_files_by_version:
        testset_value = ", ".join(
            f"{version}: {Path(str(path)).name}"
            for version, path in testset_files_by_version.items()
        )
    else:
        testset_value = Path(str(config.get("testset_file", ""))).name or "-"

    values = [
        ("Testsets", testset_value),
        ("Versionen", ", ".join(config.get("versions", [])) or "-"),
        ("Profile", ", ".join(profile_labels) or "-"),
        ("Fälle", str(config.get("max_cases") or (int(metrics["total_cases"].max()) if metrics is not None and "total_cases" in metrics.columns else "-"))),
    ]
    items = "".join(
        f"<div><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>"
        for label, value in values
    )
    st.markdown(f"<section class='last-run-overview'>{items}</section>", unsafe_allow_html=True)


def display_summary_cards(metrics: pd.DataFrame) -> None:
    if metrics.empty:
        return

    latest = metrics.sort_values("version").iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Versionen", str(metrics["version"].nunique()))
    col2.metric("Top-1 letzte Version", format_percent(latest.get("top1_accuracy_strict")))
    col3.metric("Regelübereinstimmung", format_percent(latest.get("behavior_match_rate")))
    col4.metric("Ø Laufzeit", format_number(latest.get("avg_processing_time_seconds")))


def display_metrics_table(metrics: pd.DataFrame | None) -> None:
    if metrics is None or metrics.empty:
        st.info("Noch keine Versionsmetriken vorhanden.")
        return

    visible = [column for column in SUMMARY_COLUMNS if column in metrics.columns]
    st.dataframe(metrics[visible].rename(columns=METRIC_LABELS), width="stretch", hide_index=True)


def display_case_details(results: pd.DataFrame | None) -> None:
    if results is None or results.empty:
        st.info("Noch keine Einzelfallergebnisse vorhanden.")
        return

    visible = [column for column in CASE_COLUMNS if column in results.columns]
    table = results[visible].copy()

    filters = st.columns(3)
    version = filters[0].selectbox("Version", ["Alle"] + sorted(table["version"].dropna().astype(str).unique().tolist()))
    category = filters[1].selectbox("Kategorie", ["Alle"] + sorted(table["category"].dropna().astype(str).unique().tolist()) if "category" in table else ["Alle"])
    status = filters[2].selectbox("Status", ["Alle"] + sorted(table["status"].dropna().astype(str).unique().tolist()) if "status" in table else ["Alle"])

    filtered = table
    if version != "Alle":
        filtered = filtered[filtered["version"].astype(str) == version]
    if category != "Alle" and "category" in filtered:
        filtered = filtered[filtered["category"].astype(str) == category]
    if status != "Alle" and "status" in filtered:
        filtered = filtered[filtered["status"].astype(str) == status]

    st.dataframe(filtered, width="stretch", hide_index=True)


def render_log(log_placeholder, log_lines: list[str]) -> None:
    content = html.escape("\n".join(log_lines[-300:]))
    update_id = len(log_lines)
    log_document = f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            :root {{
                color-scheme: light dark;
            }}
            body {{
                margin: 0;
            }}
            .experiment-log {{
                background: Canvas;
                border: 1px solid rgba(148, 163, 184, 0.45);
                border-radius: 8px;
                color: CanvasText;
                font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
                font-size: 0.82rem;
                height: 26rem;
                line-height: 1.45;
                overflow-y: auto;
                padding: 0.8rem 0.9rem;
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
        <div id="evaluation-suite-log-{update_id}" class="experiment-log">{content}</div>
        <script>
            const log = document.getElementById("evaluation-suite-log-{update_id}");
            if (log) {{
                log.scrollTop = log.scrollHeight;
            }}
        </script>
    </body>
    </html>
    """
    log_placeholder.empty()
    with log_placeholder.container():
        st.iframe(
            f"data:text/html;charset=utf-8,{quote(log_document)}",
            height=450,
        )


def create_log_file_path(output_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"streamlit_run_log_{timestamp}.log"


def append_log_file(log_file_path: Path, message: str) -> None:
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    with log_file_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


def render_log_download(log_file_path: Path, key_suffix: str) -> None:
    if not log_file_path.exists():
        return

    st.download_button(
        "Evaluation-Log herunterladen",
        data=log_file_path.read_bytes(),
        file_name=log_file_path.name,
        mime="text/plain",
        key=f"download_evaluation_log_{key_suffix}_{log_file_path.stem}",
    )


def run_from_sidebar() -> None:
    with st.sidebar:
        st.header("Evaluation")
        profiles = load_model_profiles()
        active_profile_id = get_active_model_profile_id()
        default_profile_id = (
            active_profile_id
            if active_profile_id in profiles
            else RECOMMENDED_MODEL_PROFILE_ID
            if RECOMMENDED_MODEL_PROFILE_ID in profiles
            else next(iter(profiles))
        )
        selected_versions = st.multiselect(
            "Versionen",
            options=list(DEFAULT_VERSIONS),
            default=list(DEFAULT_VERSIONS),
        )
        selected_profile_ids = st.multiselect(
            "LLM-Profile",
            options=list(profiles),
            default=[default_profile_id],
            format_func=lambda profile_id: model_profile_label(profile_id, profiles),
            help="Für einen sauberen Versionsvergleich zunächst nur ein Profil verwenden.",
        )
        selected_testset_paths = {
            version: evaluation_cases_path_for_version(version)
            for version in selected_versions
        }
        cases_by_version = {
            version: load_evaluation_cases(path)
            for version, path in selected_testset_paths.items()
        }
        max_available_cases = max((len(df) for df in cases_by_version.values()), default=1)
        run_scope = st.radio(
            "Umfang",
            options=["Pilot", "Vollständig"],
            index=0,
            horizontal=True,
        )
        max_cases = None
        if run_scope == "Pilot":
            max_cases = st.number_input(
                "Max. Fälle",
                min_value=1,
                max_value=max_available_cases,
                value=min(RECOMMENDED_MAX_CASES, max_available_cases),
                step=1,
            )

        case_counts_by_version = {
            version: min(int(max_cases), len(df)) if max_cases is not None else len(df)
            for version, df in cases_by_version.items()
        }
        st.caption("Eingabedaten")
        for version, path in selected_testset_paths.items():
            st.markdown(
                f"<div class='path-box'>{html.escape(version)}: {format_path(path)}</div>",
                unsafe_allow_html=True,
            )
        st.markdown(f"<div class='path-box'>V1-V4: {format_path(LEGACY_MUNICIPALITY_CONFIG_PATH)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='path-box'>V5: {format_path(V5_MUNICIPALITY_CONFIG_PATH)}</div>", unsafe_allow_html=True)
        summary_text = " | ".join(
            f"{version}: {testset_summary_text(df)}"
            for version, df in cases_by_version.items()
        )
        st.markdown(
            "<div class='experiment-plan'>"
            f"<strong>{html.escape(selected_run_size_by_version(len(selected_profile_ids), case_counts_by_version))}</strong>"
            f"<span>{html.escape(summary_text)}</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        run_requested = st.button(
            "Evaluation starten",
            type="primary",
            disabled=not selected_versions or not selected_profile_ids,
        )

    if not run_requested:
        return

    run_output_dir = create_run_output_dir(
        profile_ids=list(selected_profile_ids),
        versions=list(selected_versions),
    )
    progress = st.progress(0.0)
    status = st.empty()
    st.subheader("Evaluation-Log")
    log_placeholder = st.empty()
    log_lines: list[str] = []
    log_file_path = create_log_file_path(run_output_dir)

    def append_log_line(message: str) -> None:
        log_lines.append(message)
        append_log_file(log_file_path, message)
        render_log(log_placeholder, log_lines)

    append_log_line("Evaluation wird vorbereitet.")
    append_log_line(f"Profile: {', '.join(selected_profile_ids)}")
    append_log_line(f"Versionen: {', '.join(selected_versions)}")
    for version, path in selected_testset_paths.items():
        append_log_line(f"Testset {version}: {path}")
    append_log_line(f"Run-Ordner: {run_output_dir}")
    append_log_line(
        "Umfang: "
        + ", ".join(f"{version}: {count} Fälle" for version, count in case_counts_by_version.items())
    )

    def update_progress(event: dict[str, Any]) -> None:
        completed = int(event.get("completed_steps", 0))
        total = max(1, int(event.get("total_steps", 1)))
        progress.progress(min(0.99, completed / total))

        if event.get("event") == "start_case":
            message = (
                f"Profil {event.get('profile_id')}, Version {event.get('version')}: "
                f"Fall {event.get('case_index')}/{event.get('total_cases')} "
                f"(case_id={event.get('case_id')})"
            )
            status.info(message)
            append_log_line(message)
        elif event.get("event") == "build_vector_store":
            append_log_line(
                f"Baue Vector Store für Profil {event.get('profile_id')}, Version {event.get('version')}."
            )

    log_handler = StreamlitLogHandler(append_log_line)
    log_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)

    try:
        results, metrics, category_metrics, config = run_evaluation_suite(
            versions=selected_versions,
            output_dir=run_output_dir,
            max_cases=int(max_cases) if max_cases is not None else None,
            model_profiles=selected_profile_ids,
            progress_callback=update_progress,
        )
    except Exception as exc:
        append_log_line(f"FEHLER: Evaluation abgebrochen: {exc}")
        render_log_download(log_file_path, key_suffix="run_error")
        status.error(f"Evaluation abgebrochen: {exc}")
        raise
    finally:
        root_logger.removeHandler(log_handler)

    progress.progress(1.0)
    status.success("Evaluation abgeschlossen.")
    append_log_line("Evaluation abgeschlossen.")
    render_log_download(log_file_path, key_suffix="run_complete")
    st.session_state["latest_output_dir"] = str(run_output_dir)
    st.session_state["latest_log_path"] = str(log_file_path)
    st.session_state["latest_results"] = results
    st.session_state["latest_metrics"] = metrics
    st.session_state["latest_category_metrics"] = category_metrics
    st.session_state["latest_config"] = config


def main() -> None:
    apply_app_styles("evaluation_suite.css")
    st.title("Haupt-Evaluation")
    st.markdown(
        "<p class='evaluation-note'>Vergleich der Pipeline-Versionen anhand des zentralen annotierten Testsets. "
        "Die App dient zur reproduzierbaren Ausführung, Kontrolle und Dokumentation der Haupt-Evaluation.</p>",
        unsafe_allow_html=True,
    )

    run_from_sidebar()

    metrics = st.session_state.get("latest_metrics")
    if metrics is None:
        metrics = load_existing_metrics()
    results = st.session_state.get("latest_results")
    if results is None:
        results = load_existing_results()
    category_metrics = st.session_state.get("latest_category_metrics")
    if category_metrics is None:
        category_metrics = load_existing_category_metrics()
    profile_metrics = load_existing_profile_metrics()
    config = st.session_state.get("latest_config") or load_existing_config()

    latest_output_dir = st.session_state.get("latest_output_dir")
    if latest_output_dir:
        st.caption(f"Aktueller Run: {latest_output_dir}")
    elif latest_run_output_dir():
        st.caption(f"Geladener Run: {latest_run_output_dir()}")
    display_last_run_overview(config, metrics)

    tab_summary, tab_categories, tab_profiles, tab_cases, tab_config = st.tabs([
        "Versionsvergleich",
        "Fallkategorien",
        "Profile",
        "Fälle",
        "Konfiguration",
    ])

    with tab_summary:
        if metrics is not None:
            display_summary_cards(metrics)
        display_metrics_table(metrics)

    with tab_categories:
        if category_metrics is None or category_metrics.empty:
            st.info("Noch keine Fallkategorie-Metriken vorhanden.")
        else:
            st.dataframe(category_metrics, width="stretch", hide_index=True)

    with tab_profiles:
        if profile_metrics is None or profile_metrics.empty:
            st.info("Keine Profilmetriken vorhanden. Diese entstehen, wenn mindestens ein Modellprofil gesetzt ist.")
        else:
            st.dataframe(profile_metrics.rename(columns=METRIC_LABELS), width="stretch", hide_index=True)

    with tab_cases:
        display_case_details(results)

    with tab_config:
        if config:
            st.json(config, expanded=False)
        else:
            st.info("Noch keine Evaluationskonfiguration vorhanden.")
        latest_log_path = st.session_state.get("latest_log_path")
        if latest_log_path:
            render_log_download(Path(latest_log_path), key_suffix="config_tab")
        if metrics is not None:
            st.download_button(
                "Metriken nach Version herunterladen",
                data=metrics.to_csv(index=False).encode("utf-8"),
                file_name=METRICS_BY_VERSION_FILE,
                mime="text/csv",
                key="download_main_metrics_by_version",
            )
        if results is not None:
            st.download_button(
                "Einzelfallergebnisse herunterladen",
                data=results.to_csv(index=False).encode("utf-8"),
                file_name=RESULTS_FILE,
                mime="text/csv",
                key="download_main_results",
            )
        if config:
            st.download_button(
                "Evaluation Config herunterladen",
                data=json.dumps(config, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name=CONFIG_FILE,
                mime="application/json",
                key="download_main_config",
            )


if __name__ == "__main__":
    main()
