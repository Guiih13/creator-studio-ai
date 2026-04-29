"""
Carousel History

Persiste os carrosseis gerados por usuário em data/{user_id}/history/.
Mantém os últimos 30 por perfil e expõe funções de save/load/list/delete.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def _history_dir(data_dir: str, user_id: str) -> Path:
    p = Path(data_dir) / user_id / "history"
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_carousel(
    data_dir: str,
    user_id: str,
    carousel_data: dict,
    topic: str,
    output_format: str = "4:5",
    keep: int = 30,
) -> str:
    """Salva carrossel no histórico. Retorna o entry_id (timestamp)."""
    hdir = _history_dir(data_dir, user_id)
    entry_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    entry = {
        "entry_id": entry_id,
        "topic": topic,
        "output_format": output_format,
        "date": datetime.now().isoformat(),
        "slides_count": len(carousel_data.get("slides", [])),
        "cover_title": carousel_data.get("slides", [{}])[0].get("title", ""),
        "carousel_data": carousel_data,
    }
    (hdir / f"{entry_id}.json").write_text(
        json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _prune(hdir, keep)
    return entry_id


def load_carousel(data_dir: str, user_id: str, entry_id: str) -> dict | None:
    path = _history_dir(data_dir, user_id) / f"{entry_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_history(data_dir: str, user_id: str) -> list[dict]:
    """Retorna entradas mais recentes primeiro (sem carousel_data para performance)."""
    hdir = _history_dir(data_dir, user_id)
    entries = []
    for path in sorted(hdir.glob("*.json"), reverse=True):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entries.append({
                "entry_id":     raw.get("entry_id", path.stem),
                "topic":        raw.get("topic", ""),
                "cover_title":  raw.get("cover_title", ""),
                "date":         raw.get("date", ""),
                "slides_count": raw.get("slides_count", 0),
                "output_format":raw.get("output_format", "4:5"),
            })
        except Exception:
            pass
    return entries


def delete_carousel(data_dir: str, user_id: str, entry_id: str) -> bool:
    path = _history_dir(data_dir, user_id) / f"{entry_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def _prune(hdir: Path, keep: int) -> None:
    for old in sorted(hdir.glob("*.json"), reverse=True)[keep:]:
        old.unlink(missing_ok=True)
