"""Wiederverwendbare Tabellenfilter für Streamlit-Dashboards.

Das Modul bündelt globale Suche, Spaltenfilter und Session-State-Reset, damit
Dashboard-Tabellen konsistent bedienbar bleiben.
"""

from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st


def has_missing_table_value(value: Any) -> bool:
    try:
        return value is None or pd.isna(value)
    except (TypeError, ValueError):
        return value is None


def stringify_table_value(value: Any) -> str:
    if has_missing_table_value(value):
        return ""

    return str(value)


def apply_global_table_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    search_text = query.strip().lower()

    if not search_text:
        return df

    search_mask = df.apply(
        lambda row: row.astype(str).str.lower().str.contains(search_text, na=False, regex=False).any(),
        axis=1,
    )

    return df[search_mask]


def reset_dataframe_filter_state(key_prefix: str) -> None:
    stale_keys = [
        key
        for key in st.session_state
        if key.startswith(f"{key_prefix}_filters_v")
    ]

    for stale_key in stale_keys:
        st.session_state.pop(stale_key, None)

    version_key = f"{key_prefix}_filter_version"
    st.session_state[version_key] = int(st.session_state.get(version_key, 0)) + 1


def render_dataframe_filters(
        df: pd.DataFrame,
        *,
        key_prefix: str,
        title: str = "Tabelle filtern",
        categorical_unique_limit: int = 16,
        excluded_columns: set[str] | None = None,
        column_label_formatter: Callable[[str], str] | None = None,
        visible_item_label: str = "Einträgen",
) -> pd.DataFrame:
    if df.empty:
        return df

    filtered_df = df.copy()
    version_key = f"{key_prefix}_filter_version"
    filter_version = int(st.session_state.get(version_key, 0))
    widget_prefix = f"{key_prefix}_filters_v{filter_version}"

    with st.expander(title, expanded=False):
        if st.button(
                "Filter zurücksetzen",
                key=f"{key_prefix}_reset",
                help="Setzt alle Spaltenfilter und die globale Suche auf die Standardwerte zurück.",
        ):
            reset_dataframe_filter_state(key_prefix)
            st.rerun()

        global_query = st.text_input(
            "Globale Suche",
            key=f"{widget_prefix}_global_search",
            help="Durchsucht alle Tabellenspalten nach dem eingegebenen Text.",
        )
        filtered_df = apply_global_table_search(filtered_df, global_query)

        st.caption(
            "Spalten mit wenigen unterschiedlichen Werten nutzen Auswahllisten. "
            "Spalten mit vielen unterschiedlichen Werten nutzen eine Enthält-Suche."
        )

        excluded_filter_columns = excluded_columns or set()
        filter_columns = [
            column_name
            for column_name in df.columns
            if column_name not in excluded_filter_columns
        ]
        column_containers = st.columns(3)

        for index, column_name in enumerate(filter_columns):
            series = df[column_name]
            unique_values = [
                value
                for value in sorted(series.dropna().unique().tolist(), key=lambda item: str(item))
                if not has_missing_table_value(value)
            ]

            if not unique_values:
                continue

            label = column_label_formatter(column_name) if column_label_formatter else column_name

            with column_containers[index % len(column_containers)]:
                if len(unique_values) <= categorical_unique_limit:
                    selected_values = st.multiselect(
                        label,
                        unique_values,
                        default=unique_values,
                        key=f"{widget_prefix}_{column_name}_multiselect",
                    )
                    if set(selected_values) != set(unique_values):
                        filtered_df = filtered_df[filtered_df[column_name].isin(selected_values)]
                else:
                    column_query = st.text_input(
                        label,
                        key=f"{widget_prefix}_{column_name}_text",
                        help=f"Filtert die Spalte {label} per Enthält-Suche.",
                    ).strip().lower()

                    if column_query:
                        filtered_df = filtered_df[
                            filtered_df[column_name]
                            .map(stringify_table_value)
                            .str.lower()
                            .str.contains(column_query, na=False, regex=False)
                        ]

        st.caption(f"{len(filtered_df)} von {len(df)} {visible_item_label} sichtbar.")

    return filtered_df
