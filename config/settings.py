from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    """Lê de env vars (local) ou st.secrets (Streamlit Cloud)."""
    value = os.getenv(key, "")
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


DATA_DIR = _get("DATA_DIR") or str(Path(__file__).parent.parent / "data")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _get("ANTHROPIC_MODEL") or "claude-sonnet-4-6"
PEXELS_API_KEY = _get("PEXELS_API_KEY")

# Marca pessoal pré-configurada via secrets (usado como default no Streamlit Cloud)
DEFAULT_CREATOR_NAME = _get("DEFAULT_CREATOR_NAME")
DEFAULT_USERNAME = _get("DEFAULT_USERNAME")
DEFAULT_ACCENT_COLOR = _get("DEFAULT_ACCENT_COLOR") or "#1565C0"
DEFAULT_BRAND_LABEL = _get("DEFAULT_BRAND_LABEL")
DEFAULT_NICHE = _get("DEFAULT_NICHE")
