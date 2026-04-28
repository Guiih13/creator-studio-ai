"""
Brand Profile

Salva e carrega as configurações permanentes do criador por usuário.
Persistência: data/{user_id}/brand.json + photo.jpg
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image


BRAND_DEFAULTS = {
    "creator_name": "",
    "username": "",
    "accent_color": "#1565C0",
    "accent_color_2": "#E53935",
    "accent_color_3": "#F9A825",
    "brand_label": "",
    "niche": "",
}


def _profile_dir(data_dir: str, user_id: str = "default") -> Path:
    p = Path(data_dir) / user_id / "brand"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _json_path(data_dir: str, user_id: str = "default") -> Path:
    return _profile_dir(data_dir, user_id) / "brand.json"


def _photo_path(data_dir: str, user_id: str = "default") -> Path:
    return _profile_dir(data_dir, user_id) / "photo.jpg"


def load_brand(data_dir: str, user_id: str = "default") -> dict:
    path = _json_path(data_dir, user_id)
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            return {**BRAND_DEFAULTS, **saved}
        except Exception:
            pass
    return dict(BRAND_DEFAULTS)


def save_brand(
    data_dir: str,
    user_id: str = "default",
    *,
    creator_name: str = "",
    username: str = "",
    accent_color: str = "#1565C0",
    accent_color_2: str = "#E53935",
    accent_color_3: str = "#F9A825",
    brand_label: str = "",
    niche: str = "",
) -> None:
    _json_path(data_dir, user_id).write_text(
        json.dumps(
            {
                "creator_name": creator_name,
                "username": username,
                "accent_color": accent_color,
                "accent_color_2": accent_color_2,
                "accent_color_3": accent_color_3,
                "brand_label": brand_label,
                "niche": niche,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_photo(data_dir: str, user_id: str = "default") -> Image.Image | None:
    path = _photo_path(data_dir, user_id)
    if path.exists():
        try:
            return Image.open(path).convert("RGB")
        except Exception:
            return None
    return None


def save_photo(data_dir: str, photo: Image.Image, user_id: str = "default") -> None:
    photo.convert("RGB").save(_photo_path(data_dir, user_id), format="JPEG", quality=92)


def has_photo(data_dir: str, user_id: str = "default") -> bool:
    return _photo_path(data_dir, user_id).exists()


def photo_bytes(data_dir: str, user_id: str = "default") -> bytes | None:
    path = _photo_path(data_dir, user_id)
    if not path.exists():
        return None
    try:
        img = Image.open(path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None
