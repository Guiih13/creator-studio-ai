"""
Carousel HTML Renderer

Renderiza slides de carrossel como PNG usando HTML/CSS + Playwright.
Estilo editorial inspirado em @brandsdecoded - tipografia Oswald, layout bottom-aligned,
variantes dark/light alternadas, cover com foto de fundo.

Requer: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import base64
import html as html_lib
import io
import re
import zipfile
from pathlib import Path

from PIL import Image

try:
    from playwright.sync_api import sync_playwright as _sp
    with _sp() as _p:
        _b = _p.chromium.launch(headless=True)
        _b.close()
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except Exception:
    PLAYWRIGHT_OK = False

from src.creators.carousel_creator import _pexels_fetch

_GOOGLE_FONTS = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Oswald:wght@700&family=Inter:wght@300;400;600;700;900&display=swap');"
)

_BASE_CSS = f"""
{_GOOGLE_FONTS}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:1080px; height:1350px; overflow:hidden; -webkit-font-smoothing:antialiased; }}
"""


def _accent_for_light(accent: str) -> str:
    """Ajusta a cor de acento para fundos claros (#F4EFE8).
    Cores muito brilhantes ficam neon no creme — cap de lightness em 42%."""
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


def _accent_for_dark(accent: str) -> str:
    """Garante que a cor de acento seja visível em fundo escuro (#0A0A0A).
    Usa HLS para elevar a lightness mínima para 60%, preservando hue e saturação."""
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


def _title_font_size(title: str) -> int:
    n = len(title)
    if n <= 4:  return 220
    if n <= 8:  return 165
    if n <= 12: return 132
    if n <= 16: return 110
    if n <= 22: return 90
    return 74


def _apply_highlight(title: str, highlight: str, css_class: str = "hl") -> str:
    e = html_lib.escape
    if not highlight:
        return e(title)
    search = highlight.upper()
    upper = title.upper()
    if search not in upper:
        return e(title)
    idx = upper.index(search)
    return (
        e(title[:idx])
        + f'<span class="{css_class}">{e(title[idx: idx + len(highlight)])}</span>'
        + e(title[idx + len(highlight):])
    )


def _apply_bold(text: str, keywords: list) -> str:
    result = html_lib.escape(text)
    for kw in sorted(keywords, key=len, reverse=True):
        escaped = html_lib.escape(kw)
        result = re.sub(
            re.escape(escaped),
            f"<strong>{escaped}</strong>",
            result,
            count=1,
            flags=re.IGNORECASE,
        )
    return result


def _pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


class CarouselHTMLRenderer:
    """
    Gera slides PNG para carrossel Instagram usando HTML/CSS + Playwright.

    Args:
        accent_color  : Cor de destaque hex (ex: "#FF4500").
        username      : Handle do Instagram (sem @).
        creator_name  : Nome do criador.
        profile_photo : PIL Image (opcional) — usada no CTA.
        pexels_api_key: API key Pexels para foto de fundo no cover.
        cache_dir     : Diretório de cache Pexels.
    """

    def __init__(
        self,
        accent_color: str = "#1565C0",
        username: str = "",
        creator_name: str = "",
        profile_photo: Image.Image | None = None,
        pexels_api_key: str = "",
        cache_dir: str = "",
        brand_label: str = "",
    ):
        self.accent = accent_color
        self.username = username
        self.creator_name = creator_name
        self.profile_photo = profile_photo
        self.brand_label = brand_label
        self._pexels_key = pexels_api_key
        self._cache_dir = cache_dir
        self._pw = None
        self._browser = None

    # ── Browser lifecycle ─────────────────────────────────────────────────────

    def _start(self) -> None:
        if not PLAYWRIGHT_OK:
            raise RuntimeError(
                "Playwright não instalado. Execute:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )
        if not self._browser:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch()

    def close(self) -> None:
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    # ── Render HTML → PIL ─────────────────────────────────────────────────────

    def _render(self, html_str: str) -> Image.Image:
        self._start()
        page = self._browser.new_page(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=1,
        )
        try:
            page.set_content(html_str, wait_until="networkidle")
            screenshot = page.screenshot(type="png")
        finally:
            page.close()
        return Image.open(io.BytesIO(screenshot)).convert("RGB")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fetch_bg_b64(self, query: str) -> str | None:
        if not query or not self._pexels_key or not self._cache_dir:
            return None
        img = _pexels_fetch(query, self._pexels_key, self._cache_dir)
        return _pil_to_b64(img) if img else None

    # ── Slide templates ───────────────────────────────────────────────────────

    def _cover_html(self, slide: dict) -> str:
        title    = slide.get("title", "")
        title_hl = slide.get("title_highlight", "")
        body     = slide.get("body", "")
        visual   = slide.get("visual_suggestion", "")

        title_html = _apply_highlight(title.upper(), title_hl.upper())
        fs         = _title_font_size(title)
        bg_b64     = self._fetch_bg_b64(visual)
        bg_html    = (
            f'<img class="bg" src="data:image/jpeg;base64,{bg_b64}">'
            if bg_b64 else ""
        )
        acc  = _accent_for_dark(self.accent)
        user = html_lib.escape(self.username)
        body_e = html_lib.escape(body)

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_BASE_CSS}
.slide{{width:1080px;height:1350px;position:relative;display:flex;flex-direction:column;
  justify-content:flex-end;background:#0A0A0A;}}
.bg{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center top;}}
.ov{{position:absolute;inset:0;background:linear-gradient(to top,
  rgba(0,0,0,.95) 0%,rgba(0,0,0,.55) 50%,rgba(0,0,0,.12) 100%);}}
.bar{{position:absolute;top:0;left:0;right:0;height:6px;background:{acc};}}
.brand{{position:absolute;top:46px;left:80px;font-family:'Inter',sans-serif;
  font-size:18px;font-weight:700;color:rgba(255,255,255,.3);letter-spacing:.2em;
  text-transform:uppercase;z-index:2;}}
.cnt{{position:relative;z-index:2;padding:0 80px 84px 80px;}}
.handle{{display:inline-flex;align-items:center;gap:10px;margin-bottom:26px;}}
.dot{{width:10px;height:10px;border-radius:50%;background:{acc};flex-shrink:0;}}
.hdl{{font-family:'Inter',sans-serif;font-size:26px;font-weight:600;
  color:rgba(255,255,255,.65);}}
.title{{font-family:'Oswald',sans-serif;font-size:{fs}px;font-weight:700;
  line-height:.88;text-transform:uppercase;color:#fff;margin-bottom:34px;}}
.hl{{color:{acc};}}
.sub{{font-family:'Inter',sans-serif;font-size:33px;font-weight:300;
  color:rgba(255,255,255,.6);line-height:1.5;display:flex;align-items:flex-start;gap:12px;}}
.arrow{{color:{acc};font-weight:700;flex-shrink:0;}}
</style></head><body>
<div class="slide">{bg_html}<div class="ov"></div><div class="bar"></div>
{f'<div class="brand">{html_lib.escape(self.brand_label.upper())}</div>' if self.brand_label else ''}
<div class="cnt">
  <div class="handle"><div class="dot"></div><div class="hdl">@{user}</div></div>
  <div class="title">{title_html}</div>
  <div class="sub"><span class="arrow">→</span>{body_e}</div>
</div></div></body></html>"""

    def _content_html(self, slide: dict, number: int, total: int, dark: bool) -> str:
        title        = slide.get("title", "")
        title_hl     = slide.get("title_highlight", "")
        body         = slide.get("body", "")
        section_label= slide.get("section_label", "")
        bold_kws     = slide.get("bold_keywords", [])

        title_html = _apply_highlight(title.upper(), title_hl.upper())
        body_html  = _apply_bold(body, bold_kws)
        fs         = _title_font_size(title)
        acc        = _accent_for_dark(self.accent) if dark else _accent_for_light(self.accent)
        user       = html_lib.escape(self.username)
        label_e    = html_lib.escape(section_label.upper())

        if dark:
            bg        = "#0A0A0A"
            text_main = "#FFFFFF"
            text_body = "rgba(255,255,255,.65)"
            text_muted= "rgba(255,255,255,.25)"
        else:
            bg        = "#F4EFE8"
            text_main = "#0D0D0D"
            text_body = "#4A4A4A"
            text_muted= "rgba(13,13,13,.25)"

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_BASE_CSS}
.slide{{width:1080px;height:1350px;background:{bg};position:relative;
  display:flex;flex-direction:column;justify-content:flex-end;
  padding:0 80px 84px 80px;}}
.top{{position:absolute;top:48px;left:80px;right:80px;
  display:flex;justify-content:space-between;align-items:center;}}
.brand{{font-family:'Inter',sans-serif;font-size:17px;font-weight:700;
  color:{text_muted};letter-spacing:.2em;text-transform:uppercase;}}
.counter{{font-family:'Inter',sans-serif;font-size:17px;font-weight:700;
  color:{text_muted};letter-spacing:.1em;}}
.cnt{{display:flex;flex-direction:column;gap:26px;}}
.lbl{{font-family:'Inter',sans-serif;font-size:21px;font-weight:700;
  color:{acc};letter-spacing:.22em;text-transform:uppercase;opacity:.85;}}
.title{{font-family:'Oswald',sans-serif;font-size:{fs}px;font-weight:700;
  line-height:.88;text-transform:uppercase;color:{text_main};}}
.hl{{color:{acc};}}
.sep{{width:120px;height:4px;background:{acc};opacity:.5;}}
.body{{font-family:'Inter',sans-serif;font-size:37px;font-weight:400;
  line-height:1.55;color:{text_body};}}
.body strong{{font-weight:700;color:{text_main};}}
</style></head><body>
<div class="slide">
  <div class="top">
    <span class="brand">{html_lib.escape(self.brand_label.upper()) if self.brand_label else ''}</span>
    <span class="counter">@{user}</span>
  </div>
  <div class="cnt">
    <div class="lbl">{label_e}</div>
    <div class="title">{title_html}</div>
    <div class="sep"></div>
    <div class="body">{body_html}</div>
  </div>
</div></body></html>"""

    def _cta_html(self, slide: dict) -> str:
        title  = slide.get("title", "")
        body   = slide.get("body", "")
        acc    = _accent_for_dark(self.accent)
        user   = html_lib.escape(self.username)
        cname  = html_lib.escape(self.creator_name)

        photo_html = '<div class="ph"></div>'
        if self.profile_photo:
            b64 = _pil_to_b64(self.profile_photo)
            photo_html = f'<img class="pi" src="data:image/jpeg;base64,{b64}">'

        name_html = f'<div class="name">{cname}</div>' if cname else ""
        u_html    = f'<div class="uname">@{user}</div>' if user else ""
        title_e   = html_lib.escape(title.upper())
        body_html = f'<div class="body">{html_lib.escape(body)}</div>' if body else ""

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_BASE_CSS}
.slide{{width:1080px;height:1350px;background:#0D0D0D;display:flex;
  flex-direction:column;align-items:center;justify-content:center;
  padding:80px;text-align:center;}}
.pi{{width:200px;height:200px;border-radius:50%;border:5px solid {acc};
  object-fit:cover;margin-bottom:32px;}}
.ph{{width:200px;height:200px;border-radius:50%;border:5px solid {acc};
  background:rgba(255,255,255,.08);margin-bottom:32px;}}
.name{{font-family:'Inter',sans-serif;font-size:46px;font-weight:700;
  color:#FFFFFF;margin-bottom:10px;}}
.uname{{font-family:'Inter',sans-serif;font-size:32px;font-weight:400;
  color:rgba(255,255,255,.45);margin-bottom:48px;}}
.div{{width:80px;height:3px;background:{acc};opacity:.6;margin-bottom:48px;}}
.cta{{font-family:'Oswald',sans-serif;font-size:78px;font-weight:700;
  color:{acc};text-transform:uppercase;line-height:.9;margin-bottom:28px;}}
.body{{font-family:'Inter',sans-serif;font-size:36px;font-weight:300;
  color:rgba(255,255,255,.6);line-height:1.55;}}
</style></head><body>
<div class="slide">
  {photo_html}{name_html}{u_html}
  <div class="div"></div>
  <div class="cta">{title_e}</div>
  {body_html}
</div></body></html>"""

    # ── Main API ──────────────────────────────────────────────────────────────

    def generate(
        self,
        carousel_data: dict,
        progress_callback=None,
    ) -> list[Image.Image]:
        slides = carousel_data.get("slides", [])
        total  = len(slides)
        images: list[Image.Image] = []

        for i, slide in enumerate(slides):
            if progress_callback:
                progress_callback(i, total, slide.get("title", "")[:40])

            if i == 0:
                html_str = self._cover_html(slide)
            elif i == total - 1:
                html_str = self._cta_html(slide)
            else:
                dark     = (i % 2 == 1)
                html_str = self._content_html(slide, i + 1, total, dark)

            images.append(self._render(html_str))

        self.close()

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
