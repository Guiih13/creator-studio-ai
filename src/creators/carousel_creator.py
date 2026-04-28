"""
Carousel Creator v5

Editorial style inspirado em @brandsdecoded:
- Cover  : fundo escuro, layout bottom-aligned, título Oswald + highlight em accent
- Conteúdo: alternância dark (#0A0A0A) / light (#F4EFE8), bottom-aligned, section label
- CTA    : fundo escuro centrado, foto + CTA em accent

Fontes: Oswald Bold + Inter (baixadas automaticamente na primeira execução)
Formato: 1080x1350 (4:5 portrait Instagram)
"""

from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

W, H = 1080, 1350
PAD  = 80

_DARK  = "#0A0A0A"
_LIGHT = "#F4EFE8"

_FONT_URLS = {
    "oswald-bold":    "https://raw.githubusercontent.com/google/fonts/main/ofl/oswald/static/Oswald-Bold.ttf",
    "inter-light":    "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/static/Inter-Light.ttf",
    "inter-regular":  "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/static/Inter-Regular.ttf",
    "inter-semibold": "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/static/Inter-SemiBold.ttf",
    "inter-bold":     "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/static/Inter-Bold.ttf",
}

_SYSTEM_FALLBACKS_BOLD = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_SYSTEM_FALLBACKS = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


# ─────────────────────────────────────────────────────────────────────────────
# FONT LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _download_font(name: str, fonts_dir: Path) -> Path | None:
    path = fonts_dir / f"{name}.ttf"
    if path.exists():
        return path
    try:
        fonts_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_FONT_URLS[name], path)
        return path
    except Exception:
        return None


def _load(name: str, size: int, fonts_dir: Path | None) -> ImageFont.FreeTypeFont:
    if fonts_dir:
        p = _download_font(name, fonts_dir)
        if p:
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    # fallback sistema
    fallbacks = _SYSTEM_FALLBACKS_BOLD if "bold" in name else _SYSTEM_FALLBACKS
    for f in fallbacks:
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _tw(font: ImageFont.FreeTypeFont, text: str) -> int:
    bb = font.getbbox(text)
    return bb[2] - bb[0]


def _th(font: ImageFont.FreeTypeFont, text: str = "Ag") -> int:
    bb = font.getbbox(text)
    return bb[3] - bb[1]


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_px: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        test = (cur + " " + word).strip()
        if _tw(font, test) <= max_px:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def _title_size(title: str) -> int:
    n = len(title)
    if n <= 4:  return 220
    if n <= 8:  return 165
    if n <= 12: return 132
    if n <= 16: return 110
    if n <= 22: return 90
    return 74


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fit_cover(img: Image.Image, tw: int, th: int) -> Image.Image:
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    img = img.resize((int(iw * scale), int(ih * scale)), Image.LANCZOS)
    left = (img.width - tw) // 2
    top  = (img.height - th) // 2
    return img.crop((left, top, left + tw, top + th))


def _circle_crop(img: Image.Image, diameter: int) -> Image.Image:
    img = _fit_cover(img.convert("RGB"), diameter, diameter)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter, diameter], fill=255)
    out = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out


def _hex(color: str) -> tuple[int, int, int]:
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _accent_for_dark(accent: str) -> str:
    import colorsys
    h = accent.lstrip("#")
    if len(h) != 6:
        return accent
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    if lightness >= 0.60:
        return accent
    r2, g2, b2 = colorsys.hls_to_rgb(hue, 0.60, saturation)
    return f"#{int(r2 * 255):02x}{int(g2 * 255):02x}{int(b2 * 255):02x}"


def _accent_for_light(accent: str) -> str:
    import colorsys
    h = accent.lstrip("#")
    if len(h) != 6:
        return accent
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    if lightness <= 0.42:
        return accent
    r2, g2, b2 = colorsys.hls_to_rgb(hue, 0.42, saturation)
    return f"#{int(r2 * 255):02x}{int(g2 * 255):02x}{int(b2 * 255):02x}"


# ─────────────────────────────────────────────────────────────────────────────
# PEXELS IMAGE FETCHER
# ─────────────────────────────────────────────────────────────────────────────

def _pexels_fetch(query: str, api_key: str, cache_dir: str) -> Image.Image | None:
    if isinstance(query, list):
        query = " ".join(str(q) for q in query)
    query = str(query).strip()
    if not query or not api_key:
        return None

    slug = hashlib.md5(query.lower().encode()).hexdigest()[:14]
    cache_path = Path(cache_dir) / f"pexels_{slug}.jpg"

    if cache_path.exists():
        try:
            return Image.open(cache_path).convert("RGB")
        except Exception:
            cache_path.unlink(missing_ok=True)

    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 10, "orientation": "portrait", "size": "large"},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            # tenta sem filtro de orientação
            resp2 = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": api_key},
                params={"query": query, "per_page": 5, "size": "large"},
                timeout=10,
            )
            resp2.raise_for_status()
            photos = resp2.json().get("photos", [])
        if not photos:
            return None

        # pega a foto com maior resolução (width * height)
        best = max(photos, key=lambda p: p.get("width", 0) * p.get("height", 0))
        img_url = best["src"].get("original") or best["src"]["large2x"]
        img_resp = requests.get(img_url, timeout=30)
        img_resp.raise_for_status()
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(img_resp.content)
        return Image.open(io.BytesIO(img_resp.content)).convert("RGB")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# DRAW HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _draw_title_highlighted(
    draw: ImageDraw.ImageDraw,
    title: str,
    highlight: str,
    font: ImageFont.FreeTypeFont,
    y: int,
    color_normal: tuple,
    color_hl: tuple,
    max_w: int,
) -> int:
    """Desenha título com highlight em accent color; retorna y final."""
    upper = title.upper()
    hl    = highlight.upper() if highlight else ""
    lines = _wrap(upper, font, max_w)
    lh    = _th(font) + 10

    for line in lines:
        total_w = _tw(font, line)
        x = (W - total_w) // 2

        if hl and hl in line:
            idx = line.index(hl)
            before = line[:idx]
            mid    = line[idx: idx + len(hl)]
            after  = line[idx + len(hl):]

            bw = _tw(font, before)
            mw = _tw(font, mid)

            if before:
                draw.text((x, y), before, font=font, fill=color_normal)
            draw.text((x + bw, y), mid, font=font, fill=color_hl)
            if after:
                draw.text((x + bw + mw, y), after, font=font, fill=color_normal)
        else:
            draw.text((x, y), line, font=font, fill=color_normal)

        y += lh

    return y


# ─────────────────────────────────────────────────────────────────────────────
# CAROUSEL CREATOR
# ─────────────────────────────────────────────────────────────────────────────

class CarouselCreator:
    def __init__(
        self,
        accent_color: str = "#1565C0",
        username: str = "",
        creator_name: str = "",
        profile_photo: Image.Image | None = None,
        pexels_api_key: str = "",
        cache_dir: str = "",
        fonts_dir: str = "",
        brand_label: str = "",
    ):
        self.accent        = accent_color
        self.username      = username.lstrip("@")
        self.creator_name  = creator_name
        self.brand_label   = brand_label
        self.profile_photo = profile_photo
        self._pexels_key   = pexels_api_key
        self._cache_dir    = cache_dir
        self._fonts_dir    = Path(fonts_dir) if fonts_dir else None

    def _f(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        return _load(name, size, self._fonts_dir)

    def _paste_circle(
        self, img: Image.Image, diameter: int, x: int, y: int,
        border_color: str | None = None, border_w: int = 5,
    ) -> None:
        if not self.profile_photo:
            return
        circle = _circle_crop(self.profile_photo, diameter)
        if border_color:
            bd = diameter + border_w * 2
            border = Image.new("RGBA", (bd, bd), (0, 0, 0, 0))
            ImageDraw.Draw(border).ellipse([0, 0, bd, bd], fill=border_color)
            img.paste(border, (x - border_w, y - border_w), border)
        img.paste(circle, (x, y), circle)

    # ── Cover ─────────────────────────────────────────────────────────────────

    def _slide_cover(self, slide: dict) -> Image.Image:
        title    = slide.get("title", "")
        title_hl = slide.get("title_highlight", "")
        body     = slide.get("body", "")
        visual   = slide.get("visual_suggestion", "")

        img  = Image.new("RGB", (W, H), _DARK)
        draw = ImageDraw.Draw(img)

        # foto de fundo com gradiente
        if visual and self._pexels_key and self._cache_dir:
            bg = _pexels_fetch(visual, self._pexels_key, self._cache_dir)
            if bg:
                bg = _fit_cover(bg, W, H)
                img.paste(bg, (0, 0))
                # gradiente escuro de baixo para cima
                for row in range(H):
                    t = row / H
                    alpha = int(255 * (0.12 + 0.83 * (1 - t) ** 1.8))
                    overlay_row = Image.new("RGBA", (W, 1), (0, 0, 0, alpha))
                    img.paste(overlay_row, (0, H - 1 - row), overlay_row)
                draw = ImageDraw.Draw(img)

        acc = _accent_for_dark(self.accent)
        # barra de acento no topo
        draw.rectangle([0, 0, W, 6], fill=acc)

        # brand label topo-esquerdo
        if hasattr(self, 'brand_label') and self.brand_label:
            lf = self._f("inter-bold", 17)
            draw.text((PAD, 46), self.brand_label.upper(), font=lf,
                      fill=(255, 255, 255, 76))

        # ── conteúdo bottom-aligned ──────────────────────────────────────────
        bottom = H - 84
        fs = _title_size(title)

        # body text (Inter Light)
        body_lines: list[str] = []
        body_h = 0
        if body:
            bf = self._f("inter-light", 33)
            body_lines = _wrap(body, bf, W - PAD * 2)
            body_h = len(body_lines) * (_th(bf) + 8)

        arrow_h = 0
        if body_lines:
            arrow_h = 36

        # título (Oswald Bold)
        tf = self._f("oswald-bold", fs)
        title_lines_count = len(_wrap(title.upper(), tf, W - PAD * 2))
        title_h = title_lines_count * (_th(tf) + 10)

        handle_h = 26 + 16  # dot + text + gap

        total_content_h = handle_h + title_h + 34 + arrow_h + body_h
        y = bottom - total_content_h

        # handle: @username com dot
        hf = self._f("inter-semibold", 26)
        dot_r = 10
        dot_x = PAD
        dot_y = y + (_th(hf) - dot_r) // 2
        draw.ellipse([dot_x, dot_y, dot_x + dot_r, dot_y + dot_r], fill=acc)
        draw.text((dot_x + dot_r + 10, y), f"@{self.username}",
                  font=hf, fill=(255, 255, 255, 166))
        y += _th(hf) + 16

        # título com highlight
        acc_rgb  = _hex(acc)
        white    = (255, 255, 255)
        y = _draw_title_highlighted(draw, title, title_hl, tf, y,
                                    white, acc_rgb, W - PAD * 2)
        y += 34

        # body
        if body_lines:
            bf = self._f("inter-light", 33)
            af = self._f("inter-bold", 33)
            arr_w = _tw(af, "→")
            draw.text((PAD, y), "→", font=af, fill=acc)
            bx = PAD + arr_w + 12
            for line in body_lines:
                draw.text((bx, y), line, font=bf, fill=(255, 255, 255, 153))
                y += _th(bf) + 8

        return img

    # ── Content ───────────────────────────────────────────────────────────────

    def _slide_content(self, slide: dict, number: int, total: int, dark: bool) -> Image.Image:
        title        = slide.get("title", "")
        title_hl     = slide.get("title_highlight", "")
        body         = slide.get("body", "")
        section_label= slide.get("section_label", "")

        acc = _accent_for_dark(self.accent) if dark else _accent_for_light(self.accent)

        if dark:
            bg_color   = _DARK
            text_main  = (255, 255, 255)
            text_body  = (255, 255, 255, 166)
            text_muted = (255, 255, 255, 64)
        else:
            bg_color   = _LIGHT
            text_main  = (13, 13, 13)
            text_body  = (74, 74, 74)
            text_muted = (13, 13, 13, 64)

        img  = Image.new("RGB", (W, H), bg_color)
        draw = ImageDraw.Draw(img)

        # topo: brand label (esq) + @username (dir)
        mf = self._f("inter-bold", 17)
        brand = getattr(self, 'brand_label', '')
        if brand:
            draw.text((PAD, 48), brand.upper(), font=mf, fill=text_muted)
        draw.text((W - PAD - _tw(mf, f"@{self.username}"), 48),
                  f"@{self.username}", font=mf, fill=text_muted)

        # ── conteúdo bottom-aligned ──────────────────────────────────────────
        bottom = H - 84
        fs = _title_size(title)

        # body
        bf = self._f("inter-regular", 37)
        body_lines = _wrap(body, bf, W - PAD * 2) if body else []
        body_h = len(body_lines) * (_th(bf) + 10)

        sep_h = 4 + 26 + 26 if body_lines else 0  # separator + padding

        # título
        tf = self._f("oswald-bold", fs)
        title_lines_count = len(_wrap(title.upper(), tf, W - PAD * 2))
        title_h = title_lines_count * (_th(tf) + 10)

        lbl_h = (_th(mf) + 18) if section_label else 0

        total_h = lbl_h + title_h + sep_h + body_h
        y = bottom - total_h

        # section label
        if section_label:
            lf = self._f("inter-bold", 21)
            draw.text((PAD, y), section_label.upper(), font=lf, fill=acc)
            y += _th(lf) + 18

        # título com highlight
        acc_rgb = _hex(acc)
        y = _draw_title_highlighted(draw, title, title_hl, tf, y,
                                    text_main, acc_rgb, W - PAD * 2)

        # separador
        if body_lines:
            y += 22
            draw.rectangle([PAD, y, PAD + 120, y + 4], fill=acc)
            y += 4 + 22

            for line in body_lines:
                draw.text((PAD, y), line, font=bf, fill=text_body)
                y += _th(bf) + 10

        return img

    # ── CTA ───────────────────────────────────────────────────────────────────

    def _slide_cta(self, slide: dict) -> Image.Image:
        title = slide.get("title", "")
        body  = slide.get("body", "")

        img  = Image.new("RGB", (W, H), "#0D0D0D")
        draw = ImageDraw.Draw(img)
        acc  = _accent_for_dark(self.accent)
        acc_rgb = _hex(acc)

        cy = H // 2
        # calcula altura total para centralizar
        photo_h   = 200 + 32 if self.profile_photo else 0
        name_h    = (_th(self._f("inter-bold", 46)) + 10) if self.creator_name else 0
        user_h    = (_th(self._f("inter-regular", 32)) + 48) if self.username else 0
        sep_h     = 3 + 48
        tf = self._f("oswald-bold", 78)
        title_lines = _wrap(title.upper(), tf, W - PAD * 2)
        title_h = len(title_lines) * (_th(tf) + 14) + 28
        body_h  = 0
        bf = None
        body_lines: list[str] = []
        if body:
            bf = self._f("inter-light", 36)
            body_lines = _wrap(body, bf, W - PAD * 2)
            body_h = len(body_lines) * (_th(bf) + 10)

        total_h = photo_h + name_h + user_h + sep_h + title_h + body_h
        y = (H - total_h) // 2

        # foto circular
        if self.profile_photo:
            d  = 200
            cx = (W - d) // 2
            self._paste_circle(img, d, cx, y, border_color=acc, border_w=5)
            y += d + 32

        # nome
        if self.creator_name:
            nf = self._f("inter-bold", 46)
            nw = _tw(nf, self.creator_name)
            draw.text(((W - nw) // 2, y), self.creator_name, font=nf, fill=(255, 255, 255))
            y += _th(nf) + 10

        # @username
        if self.username:
            uf = self._f("inter-regular", 32)
            lbl = f"@{self.username}"
            uw = _tw(uf, lbl)
            draw.text(((W - uw) // 2, y), lbl, font=uf,
                      fill=(255, 255, 255, 115))
            y += _th(uf) + 48

        # separador
        draw.rectangle([(W - 80) // 2, y, (W + 80) // 2, y + 3],
                       fill=(*acc_rgb, 153))
        y += 3 + 48

        # CTA title em accent
        for line in title_lines:
            lw = _tw(tf, line)
            draw.text(((W - lw) // 2, y), line, font=tf, fill=acc_rgb)
            y += _th(tf) + 14
        y += 14

        # body
        if bf and body_lines:
            for line in body_lines:
                lw = _tw(bf, line)
                draw.text(((W - lw) // 2, y), line, font=bf,
                          fill=(255, 255, 255, 153))
                y += _th(bf) + 10

        return img

    # ── API principal ─────────────────────────────────────────────────────────

    def generate(
        self,
        carousel_data: dict,
        progress_callback=None,
    ) -> list[Image.Image]:
        # garante diretório de fontes usando data_dir do carousel
        if self._fonts_dir is None and self._cache_dir:
            self._fonts_dir = Path(self._cache_dir).parent / "fonts"

        slides = carousel_data.get("slides", [])
        total  = len(slides)
        images: list[Image.Image] = []

        for i, slide in enumerate(slides):
            if progress_callback:
                progress_callback(i, total, slide.get("title", "")[:40])

            if i == 0:
                img = self._slide_cover(slide)
            elif i == total - 1:
                img = self._slide_cta(slide)
            else:
                img = self._slide_content(slide, i + 1, total, dark=(i % 2 == 1))

            images.append(img)

        if progress_callback:
            progress_callback(total, total, "Concluído")

        return images

    def to_zip(self, images: list[Image.Image]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, img in enumerate(images):
                img_buf = io.BytesIO()
                img.save(img_buf, format="PNG", optimize=True)
                zf.writestr(f"slide_{i + 1:02d}.png", img_buf.getvalue())
        return buf.getvalue()

    def to_bytes(self, image: Image.Image) -> bytes:
        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
