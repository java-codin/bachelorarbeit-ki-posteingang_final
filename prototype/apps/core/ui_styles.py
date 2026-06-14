"""Lädt optionale CSS-Dateien für die Streamlit-Demonstrationsoberflächen.

Die Styling-Helfer sind bewusst klein gehalten und trennen visuelle Anpassungen
von fachlicher Pipeline-Logik.
"""

from pathlib import Path

import streamlit as st

from prototype.shared.constants import ENCODING_UTF8

STYLE_DIR = Path(__file__).resolve().parent / "styles"
BASE_CSS = "base.css"
STATUS_PILL_CSS_PATH = STYLE_DIR / "status_pills.css"


def load_css(css_path: Path) -> str:
    return css_path.read_text(encoding=ENCODING_UTF8)


def apply_css_files(*file_names: str) -> None:
    css_blocks = [
        load_css(STYLE_DIR / file_name)
        for file_name in file_names
    ]

    st.markdown(f"<style>{''.join(css_blocks)}</style>", unsafe_allow_html=True)


def apply_app_styles(*file_names: str) -> None:
    apply_css_files(BASE_CSS, *file_names)


def apply_status_pill_styles() -> None:
    apply_css_files(STATUS_PILL_CSS_PATH.name)
