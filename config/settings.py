from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
