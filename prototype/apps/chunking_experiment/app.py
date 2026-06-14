"""Streamlit-Oberfläche für die explorative Auswertung der Chunking-Experimente.

Das Modul bereitet Retrieval- und Routing-Ergebnisse so auf, dass Unterschiede
zwischen Chunking-Strategien im Demonstrationskontext nachvollziehbar bleiben.
"""

import json
import logging
import html
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

from prototype.shared.paths import (
    CHUNKING_EXPERIMENT_OUTPUT_DIR,
    KNOWLEDGE_BASE_V5_PATH,
    V5_MUNICIPALITY_CONFIG_PATH,
)
from prototype.shared.model_profiles import (
    get_active_model_profile_id,
    load_model_profiles,
)
from apps.core.ui_styles import apply_app_styles
from evaluation_suite.core.cases import CHUNKING_EVALUATION_CASES_PATH
from evaluation_suite.chunking.experiment import (
    DEFAULT_STRATEGIES,
    FIXED_CHUNK_OVERLAP,
    FIXED_CHUNK_SIZE,
    K_AVG_CHUNK_CHARS,
    K_CHUNK_COUNT,
    K_MAX_CHUNK_CHARS,
    K_MIN_CHUNK_CHARS,
    K_MODEL_PROFILE_ID,
    K_MODEL_PROFILE_LABEL,
    SENTENCE_AWARE_MAX_CHARS,
    STRUCTURE_MAX_CHARS,
    STRUCTURE_OVERLAP_CHARS,
    load_existing_experiment_config,
    load_existing_results,
    load_existing_summary,
    run_experiment,
)


RECOMMENDED_MODEL_PROFILE_ID = "openai_baseline"
RECOMMENDED_MAX_CASES = 30
DEFAULT_TESTSET_PATH = CHUNKING_EVALUATION_CASES_PATH
DEFAULT_KNOWLEDGE_BASE_PATH = KNOWLEDGE_BASE_V5_PATH


st.set_page_config(
    page_title="Chunking Experiment",
    page_icon="CE",
    layout="wide",
)


METRIC_LABELS = {
    K_MODEL_PROFILE_LABEL: "Modellprofil",
    K_MODEL_PROFILE_ID: "Profil-ID",
    "top1_accuracy": "Top-1 Accuracy",
    "top3_accuracy": "Top-3 Accuracy",
    "v5_department_accuracy": "Fachbereich korrekt",
    "v5_division_accuracy": "Bereich korrekt",
    "v5_team_accuracy": "Team korrekt",
    "human_review_rate": "Human Review",
    "escalation_rate": "Escalation",
    "blocked_rate": "Blocked",
    "auto_draft_rate": "Auto Draft",
    "avg_risk_score": "Risk Score",
    "retrieved_source_coverage": "Retrieved Sources",
    "used_source_coverage": "Used Sources",
    "avg_completeness_score": "Completeness",
    "total_cases": "Fälle",
    K_CHUNK_COUNT: "Chunks",
    K_AVG_CHUNK_CHARS: "Avg. Zeichen",
    K_MIN_CHUNK_CHARS: "Min. Zeichen",
    K_MAX_CHUNK_CHARS: "Max. Zeichen",
}

COMPARISON_COLUMNS = [
    K_MODEL_PROFILE_LABEL,
    "strategy",
    "total_cases",
    "top1_accuracy",
    "top3_accuracy",
    "v5_department_accuracy",
    "v5_division_accuracy",
    "v5_team_accuracy",
    "avg_completeness_score",
    "retrieved_source_coverage",
    "used_source_coverage",
    "human_review_rate",
    "avg_risk_score",
    K_CHUNK_COUNT,
    K_AVG_CHUNK_CHARS,
]

CASE_COLUMNS = [
    "case_id",
    "text",
    "ground_truth_team",
    "expected_department_v5",
    "expected_division_v5",
    "expected_team_v5",
    "predicted_team",
    "predicted_department",
    "matched_subteam",
    "matched_team",
    "top1_correct",
    "top3_correct",
    "v5_department_correct",
    "v5_division_correct",
    "v5_team_correct",
    "confidence",
    "calibrated_confidence",
    "retrieved_sources",
    "used_sources",
    "answer_completeness_score",
    "risk_score",
    "workflow_status",
]


def format_path(path: Path) -> str:
    return str(path)


def load_testset_preview(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def testset_summary_text(df: pd.DataFrame) -> str:
    if df.empty:
        return "Keine Testfälle gefunden."

    parts = [f"{len(df)} Fälle"]
    if "category" in df.columns:
        parts.append(f"{df['category'].nunique()} Fallkategorien")
    if "expected_sources" in df.columns:
        source_count = df["expected_sources"].fillna("").astype(str).str.strip().ne("").sum()
        parts.append(f"{source_count} Fälle mit erwarteten Quellen")
    if "expected_key_information" in df.columns:
        key_info_count = df["expected_key_information"].fillna("").astype(str).str.strip().ne("").sum()
        parts.append(f"{key_info_count} Fälle mit Kerninformationen")

    return " · ".join(parts)


def model_profile_label(profile_id: str, profiles: dict[str, Any]) -> str:
    profile = profiles[profile_id]
    return f"{profile.label} ({profile_id})"


def experiment_run_size(strategy_count: int, case_count: int) -> str:
    total_runs = strategy_count * case_count
    return f"{total_runs} Pipeline-Läufe ({strategy_count} Strategien × {case_count} Fälle)"


def config_uses_current_inputs(
        config: dict[str, Any] | None,
        testset_path: Path,
        knowledge_base_path: Path,
        selected_strategies: list[str],
        model_profile_id: str,
) -> bool:
    if not config:
        return False

    return (
        Path(str(config.get("testset_file", ""))) == testset_path
        and Path(str(config.get("knowledge_base", ""))) == knowledge_base_path
        and list(config.get("strategies", [])) == selected_strategies
        and str(config.get("model_profile_id", "")) == model_profile_id
    )


class StreamlitLogHandler(logging.Handler):
    def __init__(self, append_log_line) -> None:
        super().__init__(level=logging.INFO)
        self.append_log_line = append_log_line

    def emit(self, record: logging.LogRecord) -> None:
        self.append_log_line(self.format(record))


def format_percent(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def format_number(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def display_summary_table(summary: pd.DataFrame) -> None:
    visible_columns = [column for column in COMPARISON_COLUMNS if column in summary.columns]
    renamed = summary[visible_columns].rename(columns=METRIC_LABELS)
    st.dataframe(renamed, width="stretch", hide_index=True)


def summary_row_label(row: pd.Series) -> str:
    strategy = str(row.get("strategy", "-"))
    profile = str(row.get(K_MODEL_PROFILE_LABEL) or row.get(K_MODEL_PROFILE_ID) or "").strip()
    return f"{profile} · {strategy}" if profile else strategy


def display_metric_cards(summary: pd.DataFrame) -> None:
    if summary.empty:
        return

    best_top1 = summary.sort_values("top1_accuracy", ascending=False).iloc[0]
    best_top3 = summary.sort_values("top3_accuracy", ascending=False).iloc[0]
    leanest = summary.sort_values(K_CHUNK_COUNT, ascending=True).iloc[0]
    complete = summary.sort_values("avg_completeness_score", ascending=False).iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Beste Top-1", format_percent(best_top1.get("top1_accuracy")), summary_row_label(best_top1))
    col2.metric("Beste Top-3", format_percent(best_top3.get("top3_accuracy")), summary_row_label(best_top3))
    col3.metric("Hohe Completeness", format_number(complete.get("avg_completeness_score")), summary_row_label(complete))
    col4.metric("Wenigste Chunks", format_number(leanest.get(K_CHUNK_COUNT)), summary_row_label(leanest))


def display_charts(summary: pd.DataFrame) -> None:
    if summary.empty:
        st.info("Noch keine Ergebnisdaten vorhanden.")
        return

    chart_columns = [
        column
        for column in [
            "top1_accuracy",
            "top3_accuracy",
            "avg_completeness_score",
            "retrieved_source_coverage",
            "used_source_coverage",
            "human_review_rate",
        ]
        if column in summary.columns
    ]

    chart_summary = summary.copy()
    chart_summary["chart_label"] = chart_summary.apply(summary_row_label, axis=1)

    if chart_columns:
        st.bar_chart(chart_summary.set_index("chart_label")[chart_columns])

    chunk_columns = [
        column
        for column in [K_CHUNK_COUNT, K_AVG_CHUNK_CHARS, K_MAX_CHUNK_CHARS]
        if column in summary.columns
    ]

    if chunk_columns:
        st.bar_chart(chart_summary.set_index("chart_label")[chunk_columns])


def display_config(config: dict[str, Any] | None) -> None:
    if not config:
        st.info("Noch keine Experimentkonfiguration gespeichert.")
        return

    st.json(config, expanded=False)


def display_last_run_overview(config: dict[str, Any] | None, summary: pd.DataFrame | None) -> None:
    if not config:
        st.info("Noch kein gespeicherter Chunking-Lauf vorhanden.")
        return

    values = [
        ("Testset", Path(str(config.get("testset_file", ""))).name or "-"),
        ("Wissensbasis", Path(str(config.get("knowledge_base", ""))).name or "-"),
        ("Profil", str(config.get("model_profile_id") or "-")),
        (
            "Fälle",
            str(
                config.get("max_cases")
                or (
                    int(summary["total_cases"].max())
                    if summary is not None and "total_cases" in summary.columns
                    else "-"
                )
            ),
        ),
        ("Strategien", ", ".join(str(item) for item in config.get("strategies", [])) or "-"),
    ]
    items = "".join(
        f"<div><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>"
        for label, value in values
    )

    st.markdown(
        f"<section class='last-run-overview'>{items}</section>",
        unsafe_allow_html=True,
    )

    if Path(str(config.get("knowledge_base", ""))).name != DEFAULT_KNOWLEDGE_BASE_PATH.name:
        st.warning(
            "Der gespeicherte Lauf nutzt nicht die aktuell voreingestellte Wissensbasis. "
            "Für die V5-Chunking-Evaluation sollte das Experiment neu gestartet werden."
        )


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
        <div id="chunking-experiment-log-{update_id}" class="experiment-log">{content}</div>
        <script>
            const scrollLog = () => {{
                const log = document.getElementById("chunking-experiment-log-{update_id}");
                if (log) {{
                    log.scrollTop = log.scrollHeight;
                }}
            }};
            requestAnimationFrame(scrollLog);
            setTimeout(scrollLog, 50);
            setTimeout(scrollLog, 150);
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


def create_log_file_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return CHUNKING_EXPERIMENT_OUTPUT_DIR / f"streamlit_run_log_{timestamp}.log"


def append_log_file(log_file_path: Path, message: str) -> None:
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    with log_file_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


def render_log_download(log_file_path: Path, key_suffix: str) -> None:
    if not log_file_path.exists():
        return

    st.download_button(
        "Experiment-Log herunterladen",
        data=log_file_path.read_bytes(),
        file_name=log_file_path.name,
        mime="text/plain",
        key=f"download_experiment_log_{key_suffix}_{log_file_path.stem}",
    )


def display_strategy_details(strategy: str, model_profile_id: str | None = None) -> None:
    results = load_existing_results(strategy, model_profile_id=model_profile_id)

    if results is None:
        st.info(f"Keine Detailergebnisse für '{strategy}' gefunden.")
        return

    visible_columns = [column for column in CASE_COLUMNS if column in results.columns]
    detail_options = results[visible_columns].copy()

    if "case_id" not in detail_options.columns:
        detail_options.insert(0, "Zeile", list(results.index))

    with st.expander("Fallübersicht", expanded=True):
        table_event = st.dataframe(
            detail_options,
            width="stretch",
            hide_index=True,
            key=f"chunking_case_table_{model_profile_id or 'legacy'}_{strategy}",
            on_select="rerun",
            selection_mode="single-row",
        )

    selected_rows = table_event.selection.rows

    if not selected_rows:
        st.info("Fall in der Tabelle auswählen, um die Detailansicht zu öffnen.")
        return

    if "case_id" in results.columns:
        selected_case_id = detail_options.iloc[selected_rows[0]]["case_id"]
        selected_row = results.loc[results["case_id"] == selected_case_id].iloc[0]
    else:
        selected_index = int(detail_options.iloc[selected_rows[0]]["Zeile"])
        selected_row = results.iloc[selected_index]

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Routing und Retrieval")
        st.write("**Erwarteter Fachbereich:**", selected_row.get("expected_department_v5", selected_row.get("ground_truth_team", "-")))
        st.write("**Erwarteter Bereich:**", selected_row.get("expected_division_v5", "-"))
        st.write("**Erwartetes Team:**", selected_row.get("expected_team_v5", "-"))
        st.write("**Prediction Fachbereich:**", selected_row.get("predicted_department", selected_row.get("predicted_team", "-")))
        st.write("**Prediction Bereich:**", selected_row.get("matched_subteam", "-"))
        st.write("**Prediction Team:**", selected_row.get("matched_team", "-"))
        st.write("**Workflow:**", selected_row.get("workflow_status", "-"))
        st.write("**Retrieved Sources:**", selected_row.get("retrieved_sources", "-"))
        st.write("**Used Sources:**", selected_row.get("used_sources", "-"))

    with col2:
        st.subheader("Bewertung")
        st.write("**Top-1 korrekt:**", selected_row.get("top1_correct", "-"))
        st.write("**Top-3 korrekt:**", selected_row.get("top3_correct", "-"))
        st.write("**Fachbereich korrekt:**", selected_row.get("v5_department_correct", "-"))
        st.write("**Bereich korrekt:**", selected_row.get("v5_division_correct", "-"))
        st.write("**Team korrekt:**", selected_row.get("v5_team_correct", "-"))
        st.write("**Risk Score:**", selected_row.get("risk_score", "-"))
        st.write("**Completeness:**", selected_row.get("answer_completeness_score", "-"))
        st.write("**Human Review:**", selected_row.get("human_review_required", "-"))

    with st.expander("Antwortentwurf"):
        st.write(selected_row.get("draft_answer", ""))


def run_from_sidebar() -> None:
    with st.sidebar:
        st.header("Experiment")
        profiles = load_model_profiles()
        active_profile_id = get_active_model_profile_id()
        default_profile_id = (
            active_profile_id
            if active_profile_id in profiles
            else RECOMMENDED_MODEL_PROFILE_ID
            if RECOMMENDED_MODEL_PROFILE_ID in profiles
            else next(iter(profiles))
        )
        profile_ids = list(profiles)
        selected_profile_id = st.selectbox(
            "LLM-Profil",
            options=profile_ids,
            index=profile_ids.index(default_profile_id),
            format_func=lambda profile_id: model_profile_label(profile_id, profiles),
            help="Das Profil sollte für den Chunking-Vergleich konstant bleiben.",
        )
        testset_path = DEFAULT_TESTSET_PATH
        testset_df = load_testset_preview(testset_path)
        total_cases = len(testset_df)
        selected_strategies = st.multiselect(
            "Strategien",
            options=list(DEFAULT_STRATEGIES),
            default=list(DEFAULT_STRATEGIES),
        )
        run_scope = st.radio(
            "Umfang",
            options=["Pilot", "Vollständig"],
            index=0,
            horizontal=True,
            help="Pilot nutzt standardmäßig 30 Fälle. Vollständig nutzt das komplette Testset.",
        )
        max_cases = None
        if run_scope == "Pilot":
            max_cases = st.number_input(
                "Max. Fälle",
                min_value=1,
                max_value=max(1, total_cases or 1),
                value=min(RECOMMENDED_MAX_CASES, max(1, total_cases or RECOMMENDED_MAX_CASES)),
                step=1,
            )

        with st.expander("Chunking Parameter"):
            fixed_chunk_size = st.number_input(
                "Fixed chunk size",
                min_value=100,
                max_value=2500,
                value=FIXED_CHUNK_SIZE,
                step=50,
                help="Maximale Zeichenanzahl pro Chunk beim einfachen Fixed-Size-Chunking.",
            )
            fixed_chunk_overlap = st.number_input(
                "Fixed overlap",
                min_value=0,
                max_value=max(0, int(fixed_chunk_size) // 2),
                value=FIXED_CHUNK_OVERLAP,
                step=25,
                help="Zeichenüberlappung zwischen zwei aufeinanderfolgenden Fixed-Size-Chunks.",
            )
            sentence_aware_max_chars = st.number_input(
                "Sentence-aware max chars",
                min_value=100,
                max_value=2500,
                value=SENTENCE_AWARE_MAX_CHARS,
                step=50,
                help="Maximale Zeichenanzahl pro satzgrenzenorientiertem Chunk.",
            )
            structure_max_chars = st.number_input(
                "Structure max chars",
                min_value=300,
                max_value=5000,
                value=STRUCTURE_MAX_CHARS,
                step=100,
                help="Maximale Zeichenanzahl pro strukturorientiertem Chunk nach Markdown-Abschnitten.",
            )
            structure_overlap_chars = st.number_input(
                "Structure overlap",
                min_value=0,
                max_value=max(0, int(structure_max_chars) // 2),
                value=STRUCTURE_OVERLAP_CHARS,
                step=50,
                help="Zeichenüberlappung, wenn lange strukturierte Abschnitte weiter geteilt werden.",
            )

        st.caption("Eingabedaten")
        st.markdown(f"<div class='path-box'>{format_path(testset_path)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='path-box'>{format_path(DEFAULT_KNOWLEDGE_BASE_PATH)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='path-box'>{format_path(V5_MUNICIPALITY_CONFIG_PATH)}</div>", unsafe_allow_html=True)

        effective_cases = int(max_cases) if max_cases is not None else total_cases
        st.markdown(
            "<div class='experiment-plan'>"
            f"<strong>{html.escape(experiment_run_size(len(selected_strategies), effective_cases))}</strong>"
            f"<span>{html.escape(testset_summary_text(testset_df))}</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        run_requested = st.button(
            "Experiment starten",
            type="primary",
            disabled=not selected_strategies or testset_df.empty,
        )

    if not run_requested:
        return

    progress = st.progress(0.0)
    status = st.empty()
    st.subheader("Experiment-Log")
    log_placeholder = st.empty()
    log_lines: list[str] = []
    log_file_path = create_log_file_path()
    strategy_count = len(selected_strategies)
    progress_state = {"current_strategy_index": 0}

    def append_log_line(message: str) -> None:
        log_lines.append(message)
        append_log_file(log_file_path, message)
        render_log(log_placeholder, log_lines)

    append_log_line("Experiment wird vorbereitet.")
    append_log_line(f"Profil: {selected_profile_id}")
    append_log_line(f"Testset: {testset_path}")
    append_log_line(f"Wissensbasis: {DEFAULT_KNOWLEDGE_BASE_PATH}")
    append_log_line(f"Strategien: {', '.join(selected_strategies)}")
    append_log_line(f"Umfang: {effective_cases} Fälle")

    def update_progress(event: dict[str, Any]) -> None:
        strategy = event["strategy"]
        if strategy in selected_strategies:
            progress_state["current_strategy_index"] = selected_strategies.index(strategy)

        case_index = int(event.get("case_index", 0))
        total_cases = max(1, int(event.get("total_cases", 1)))
        total_steps = max(1, strategy_count * total_cases)
        completed_steps = progress_state["current_strategy_index"] * total_cases + case_index - 1
        progress.progress(min(0.99, completed_steps / total_steps))
        status.info(
            f"Strategie {strategy}: Fall {case_index}/{total_cases} "
            f"(case_id={event.get('case_id')})"
        )
        append_log_line(
            f"Strategie {strategy}: Fall {case_index}/{total_cases} "
            f"(case_id={event.get('case_id')})"
        )

    log_handler = StreamlitLogHandler(append_log_line)
    log_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)

    try:
        summary, _ = run_experiment(
            strategies=selected_strategies,
            testset_path=testset_path,
            model_profile_id=selected_profile_id,
            max_cases=int(max_cases) if max_cases is not None else None,
            fixed_chunk_size=int(fixed_chunk_size),
            fixed_chunk_overlap=int(fixed_chunk_overlap),
            sentence_aware_max_chars=int(sentence_aware_max_chars),
            structure_max_chars=int(structure_max_chars),
            structure_overlap_chars=int(structure_overlap_chars),
            progress_callback=update_progress,
        )
    except Exception as exc:
        append_log_line(f"FEHLER: Experiment abgebrochen: {exc}")
        render_log_download(log_file_path, key_suffix="run_error")
        st.session_state["latest_log_path"] = str(log_file_path)
        status.error(f"Experiment abgebrochen: {exc}")
        raise
    finally:
        root_logger.removeHandler(log_handler)

    progress.progress(1.0)
    status.success("Experiment abgeschlossen.")
    append_log_line("Experiment abgeschlossen.")
    render_log_download(log_file_path, key_suffix="run_complete")
    st.session_state["latest_log_path"] = str(log_file_path)
    st.session_state["latest_summary"] = summary


def main() -> None:
    apply_app_styles("chunking_experiment.css")
    st.title("Chunking Experiment")
    st.markdown(
        "<p class='chunking-note'>Vergleich von fixed, structure und sentence-aware chunking "
        "für die v5-Pipeline. Die Oberfläche dient der nachvollziehbaren "
        "Evaluation von Retrieval-Qualität, Quellenbindung und Workflow-Risiken.</p>",
        unsafe_allow_html=True,
    )

    run_from_sidebar()

    summary = st.session_state.get("latest_summary")
    if summary is None:
        summary = load_existing_summary()

    config = load_existing_experiment_config()

    st.caption(f"Output: {CHUNKING_EXPERIMENT_OUTPUT_DIR}")
    display_last_run_overview(config, summary)

    tab_summary, tab_charts, tab_details, tab_config = st.tabs([
        "Vergleich",
        "Visualisierung",
        "Fälle",
        "Konfiguration",
    ])

    with tab_summary:
        if summary is None:
            st.info("Noch keine Ergebnisse vorhanden. Starte links ein Experiment oder führe das Skript aus.")
        else:
            display_metric_cards(summary)
            display_summary_table(summary)

    with tab_charts:
        if summary is None:
            st.info("Noch keine Ergebnisse vorhanden.")
        else:
            display_charts(summary)

    with tab_details:
        detail_summary = summary if summary is not None else load_existing_summary()
        if detail_summary is None or detail_summary.empty or "strategy" not in detail_summary.columns:
            st.info("Noch keine Strategie-Detaildaten vorhanden.")
        else:
            available_profiles = (
                detail_summary[[K_MODEL_PROFILE_ID, K_MODEL_PROFILE_LABEL]]
                .fillna("")
                .drop_duplicates()
                .to_dict("records")
                if K_MODEL_PROFILE_ID in detail_summary.columns
                else [{K_MODEL_PROFILE_ID: "", K_MODEL_PROFILE_LABEL: ""}]
            )
            selected_profile = st.selectbox(
                "Modellprofil",
                options=available_profiles,
                format_func=lambda row: str(row.get(K_MODEL_PROFILE_LABEL) or row.get(K_MODEL_PROFILE_ID) or "Legacy"),
            )
            selected_profile_id = str(selected_profile.get(K_MODEL_PROFILE_ID) or "")
            profile_rows = detail_summary
            if K_MODEL_PROFILE_ID in profile_rows.columns:
                profile_rows = profile_rows[
                    profile_rows[K_MODEL_PROFILE_ID].fillna("").astype(str) == selected_profile_id
                ]
            available_strategies = [
                strategy
                for strategy in DEFAULT_STRATEGIES
                if strategy in set(profile_rows["strategy"].astype(str))
            ]
            if not available_strategies:
                st.info("Für dieses Profil liegen keine Strategie-Detaildaten vor.")
            else:
                selected_strategy = st.selectbox("Strategie", available_strategies)
                display_strategy_details(
                    selected_strategy,
                    model_profile_id=selected_profile_id or None,
                )

    with tab_config:
        display_config(config)
        latest_log_path = st.session_state.get("latest_log_path")
        if latest_log_path:
            render_log_download(Path(latest_log_path), key_suffix="config_tab")
        if summary is not None:
            csv_data = summary.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Summary CSV herunterladen",
                data=csv_data,
                file_name="chunking_summary.csv",
                mime="text/csv",
                key="download_chunking_summary_csv",
            )
        if config is not None:
            st.download_button(
                "Experiment Config herunterladen",
                data=json.dumps(config, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name="chunking_experiment_config.json",
                mime="application/json",
                key="download_chunking_experiment_config_json",
            )


if __name__ == "__main__":
    main()
