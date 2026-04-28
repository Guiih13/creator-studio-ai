"""
Carousel Creator v4

Layout:
- Cover  : fundo branco | circulo + nome + @username no topo | hook text no centro
- Conteudo: imagem Pexels como fundo + overlay escuro + texto branco | foto no rodape
- CTA    : fundo colorido | foto grande centralizada | @username | call to action

Formato: 1080x1350 (4:5 portrait Instagram)
Dependencias: pillow, requests
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

W = 1080
H = 1350
PAD = 80

ACCENT_BAR     = 10
HEADER_H       = 90
FOOTER_H       = 150

CIRCLE_COVER   = 130   # circulo do criador no cover
CIRCLE_HEADER  = 60    # circulo no header dos slides de conteudo
CIRCLE_FOOTER  = 100   # circulo no rodape dos slides de conteudo
CIRCLE_CTA     = 210   # circulo no slide CTA

BG_OVERLAY_ALPHA = 165  # opacidade do overlay sobre imagem Pexels (0-255)


# ─────────────────────────────────────────────────────────────────────────────
# FONT
# ─────────────────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        (r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
        (r"C:\Windows\Fonts\arialbd.ttf"  if bold else r"C:\Windows\Fonts\arial.ttf"),
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except (OSError, IOError):
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
    """Retorna imagem circular RGBA."""
    img = _fit_cover(img.convert("RGB"), diameter, diameter)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter, diameter], fill=255)
    out = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out


def _solid_overlay(w: int, h: int, alpha: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (10, 10, 10, alpha))


# ─────────────────────────────────────────────────────────────────────────────
# PEXELS IMAGE FETCHER
# ─────────────────────────────────────────────────────────────────────────────

def _pexels_fetch(query: str, api_key: str, cache_dir: str) -> Image.Image | None:
    # visual_suggestion pode vir como lista ou string
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
            params={"query": query, "per_page": 3, "orientation": "portrait"},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None

        img_url = photos[0]["src"]["large2x"]
        img_resp = requests.get(img_url, timeout=20)
        img_resp.raise_for_status()

        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(img_resp.content)
        return Image.open(io.BytesIO(img_resp.content)).convert("RGB")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CAROUSEL CREATOR
# ─────────────────────────────────────────────────────────────────────────────

class CarouselCreator:
    """
    Gera slides PNG para carrossel Instagram.

    Args:
        accent_color  : Cor de destaque em hex.
        username      : @username (sem @).
        creator_name  : Nome do criador (ex: "Guilherme Martins").
        profile_photo : Foto do criador (PIL Image, opcional).
        pexels_api_key: Chave Pexels para imagens automaticas de fundo.
        cache_dir     : Diretorio de cache local das imagens Pexels.
    """

    def __init__(
        self,
        accent_color: str = "#1565C0",
        username: str = "",
        creator_name: str = "",
        profile_photo: Image.Image | None = None,
        pexels_api_key: str = "",
        cache_dir: str = "",
    ):
        self.accent        = accent_color
        self.username      = username
        self.creator_name  = creator_name
        self.profile_photo = profile_photo
        self._pexels_key   = pexels_api_key
        self._cache_dir    = cache_dir

        self.bg      = "#FFFFFF"
        self.fg_dark = "#0D1117"
        self.fg_body = "#3D444D"
        self.fg_muted= "#6E7681"

    # ── Photo helpers ─────────────────────────────────────────────────────────

    def _paste_circle(
        self,
        img: Image.Image,
        diameter: int,
        x: int,
        y: int,
        border_color: str | None = None,
        border_w: int = 5,
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

    # ── Cover slide ───────────────────────────────────────────────────────────

    def _slide_cover(self, title: str, body: str, total: int) -> Image.Image:
        """
        Fundo branco.
        Topo: circulo da foto + nome + @username.
        Centro: hook text em bold grande.
        """
        img  = Image.new("RGB", (W, H), self.bg)
        draw = ImageDraw.Draw(img)

        # Barra de acento no topo
        draw.rectangle([0, 0, W, ACCENT_BAR], fill=self.accent)

        # ── Secao do perfil ──────────────────────────────────────────────────
        PROFILE_PAD_TOP = 48
        cy_profile = ACCENT_BAR + PROFILE_PAD_TOP

        if self.profile_photo:
            d = CIRCLE_COVER
            # Circulo centralizado horizontalmente
            cx = (W - d) // 2
            self._paste_circle(img, d, cx, cy_profile, border_color=self.accent)
            text_x = cx + d + 28
            profile_bottom = cy_profile + d
        else:
            d = 0
            profile_bottom = cy_profile

        # Nome e @username abaixo (ou ao lado) do circulo
        name_y = cy_profile
        if self.creator_name:
            nf = _font(40, bold=True)
            if self.profile_photo:
                # Centralizado abaixo do circulo
                nw = _tw(nf, self.creator_name)
                draw.text(((W - nw) // 2, profile_bottom + 20), self.creator_name, font=nf, fill=self.fg_dark)
                name_y = profile_bottom + 20

            uf = _font(32)
            label = f"@{self.username}" if self.username else ""
            if label:
                uw = _tw(uf, label)
                draw.text(((W - uw) // 2, name_y + _th(nf) + 10), label, font=uf, fill=self.accent)
                profile_bottom = name_y + _th(nf) + 10 + _th(uf)
            else:
                profile_bottom = name_y + _th(nf)

        elif self.username:
            uf = _font(36, bold=True)
            label = f"@{self.username}"
            lw = _tw(uf, label)
            if self.profile_photo:
                draw.text(((W - lw) // 2, profile_bottom + 20), label, font=uf, fill=self.accent)
                profile_bottom = profile_bottom + 20 + _th(uf)
            else:
                draw.text(((W - lw) // 2, cy_profile), label, font=uf, fill=self.accent)
                profile_bottom = cy_profile + _th(uf)

        # Linha separadora
        SEP_TOP = profile_bottom + 36
        draw.rectangle([PAD, SEP_TOP, W - PAD, SEP_TOP + 3], fill=self.accent)

        # ── Hook text no centro ───────────────────────────────────────────────
        text_y_start = SEP_TOP + 50
        text_y_end   = H - 80

        cw = W - PAD * 2
        tf = _font(76, bold=True)
        title_lines = _wrap(title, tf, cw)
        tlh = _th(tf) + 16

        bf = _font(44)
        body_lines = _wrap(body, bf, cw) if body else []
        blh = _th(bf) + 12

        gap = 36 if body_lines else 0
        total_h = len(title_lines) * tlh + gap + len(body_lines) * blh
        zone_h  = text_y_end - text_y_start
        cy = text_y_start + max(0, (zone_h - total_h) // 2)

        for line in title_lines:
            lw = _tw(tf, line)
            draw.text(((W - lw) // 2, cy), line, font=tf, fill=self.fg_dark)
            cy += tlh

        if body_lines:
            cy += gap
            for line in body_lines:
                lw = _tw(bf, line)
                draw.text(((W - lw) // 2, cy), line, font=bf, fill=self.fg_body)
                cy += blh

        # Barra de acento no fundo
        draw.rectangle([0, H - ACCENT_BAR, W, H], fill=self.accent)

        return img

    # ── Content slide ─────────────────────────────────────────────────────────

    def _draw_header(
        self, draw: ImageDraw.ImageDraw, img: Image.Image, fg_user: str
    ) -> None:
        uf = _font(30, bold=True)
        label = f"@{self.username}" if self.username else ""

        if self.profile_photo:
            d = CIRCLE_HEADER
            cy = ACCENT_BAR + (HEADER_H - d) // 2
            self._paste_circle(img, d, PAD, cy, border_w=3)
            if label:
                tx = PAD + d + 16
                ty = ACCENT_BAR + (HEADER_H - _th(uf)) // 2
                draw.text((tx, ty), label, font=uf, fill=fg_user)
        elif label:
            ty = ACCENT_BAR + (HEADER_H - _th(uf)) // 2
            draw.text((PAD, ty), label, font=uf, fill=fg_user)

    def _draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        img: Image.Image,
        number: int,
        total: int,
        fg_muted: str,
        acc_line: str,
    ) -> None:
        fy = H - FOOTER_H
        draw.rectangle([PAD, fy, W - PAD, fy + 3], fill=acc_line)
        fy += 16

        if self.profile_photo:
            d = CIRCLE_FOOTER
            cy = fy + (FOOTER_H - 16 - d) // 2
            self._paste_circle(img, d, PAD, cy, border_color=acc_line, border_w=4)
            if self.username:
                uf = _font(28, bold=True)
                uy = cy + (d - _th(uf)) // 2
                draw.text((PAD + d + 16, uy), f"@{self.username}", font=uf, fill=fg_muted)

        nf = _font(28, bold=True)
        num_label = f"{number}/{total}"
        nw = _tw(nf, num_label)
        ny = fy + (FOOTER_H - 16 - _th(nf)) // 2
        draw.text((W - PAD - nw, ny), num_label, font=nf, fill=fg_muted)

    def _draw_body(
        self,
        draw: ImageDraw.ImageDraw,
        title: str,
        body: str,
        y0: int,
        y1: int,
        fg_title: str,
        fg_body: str,
        accent: str | None = None,
    ) -> None:
        """Texto centralizado verticalmente na zona [y0, y1]. Linha de acento entre titulo e corpo."""
        cw = W - PAD * 2
        tf = _font(72, bold=True)
        bf = _font(44)

        title_lines = _wrap(title, tf, cw)
        body_lines  = _wrap(body, bf, cw) if body else []
        tlh = _th(tf) + 14
        blh = _th(bf) + 10

        # Separador entre titulo e body (3px)
        sep_h   = 3 + 28 + 28 if body_lines else 0
        total_h = len(title_lines) * tlh + sep_h + len(body_lines) * blh
        cy = y0 + max(0, ((y1 - y0) - total_h) // 2)

        for line in title_lines:
            lw = _tw(tf, line)
            draw.text(((W - lw) // 2, cy), line, font=tf, fill=fg_title)
            cy += tlh

        if body_lines:
            cy += 22
            # Linha fina de acento separando titulo do corpo
            acc = accent or self.accent
            draw.rectangle([(W - 72) // 2, cy, (W + 72) // 2, cy + 3], fill=acc)
            cy += 28

            for line in body_lines:
                lw = _tw(bf, line)
                draw.text(((W - lw) // 2, cy), line, font=bf, fill=fg_body)
                cy += blh

    def _slide_content(
        self, number: int, total: int, title: str, body: str, visual: str = ""
    ) -> Image.Image:
        img  = Image.new("RGB", (W, H), self.bg)
        draw = ImageDraw.Draw(img)

        # Tentar imagem Pexels como fundo
        has_bg = False
        if visual and self._pexels_key and self._cache_dir:
            bg_img = _pexels_fetch(visual, self._pexels_key, self._cache_dir)
            if bg_img:
                has_bg = True
                bg_img = _fit_cover(bg_img, W, H)
                img.paste(bg_img, (0, 0))
                overlay = _solid_overlay(W, H, BG_OVERLAY_ALPHA)
                img.paste(overlay, (0, 0), overlay)

        if has_bg:
            fg_user  = "#FFFFFF"
            fg_title = "#FFFFFF"
            fg_body_ = "#E8E8E8"
            fg_muted = "#CCCCCC"
            acc_line = "#FFFFFF"
            top_bar  = Image.new("RGBA", (W, ACCENT_BAR), (255, 255, 255, 130))
            img.paste(top_bar, (0, 0), top_bar)
        else:
            fg_user  = self.accent
            fg_title = self.fg_dark
            fg_body_ = self.fg_body
            fg_muted = self.fg_muted
            acc_line = self.accent
            draw.rectangle([0, 0, W, ACCENT_BAR], fill=self.accent)

        self._draw_header(draw, img, fg_user)

        y_start = ACCENT_BAR + HEADER_H + 24
        y_end   = H - FOOTER_H - 24
        self._draw_body(draw, title, body, y_start, y_end, fg_title, fg_body_,
                        accent=acc_line)

        self._draw_footer(draw, img, number, total, fg_muted, acc_line)
        return img

    # ── CTA slide ─────────────────────────────────────────────────────────────

    def _slide_cta(self, number: int, total: int, title: str, body: str) -> Image.Image:
        img  = Image.new("RGB", (W, H), self.accent)
        draw = ImageDraw.Draw(img)

        cy = 80

        if self.profile_photo:
            d  = CIRCLE_CTA
            cx = (W - d) // 2
            self._paste_circle(img, d, cx, cy, border_color="#FFFFFF", border_w=6)
            cy += d + 36

        if self.creator_name:
            nf = _font(44, bold=True)
            lw = _tw(nf, self.creator_name)
            draw.text(((W - lw) // 2, cy), self.creator_name, font=nf, fill="#FFFFFF")
            cy += _th(nf) + 10

        if self.username:
            uf = _font(34)
            label = f"@{self.username}"
            lw = _tw(uf, label)
            draw.text(((W - lw) // 2, cy), label, font=uf, fill="#FFFFFFBB")
            cy += _th(uf) + 32

        draw.rectangle([(W - 80) // 2, cy, (W + 80) // 2, cy + 4], fill="#FFFFFF66")
        cy += 40

        tf = _font(64, bold=True)
        for line in _wrap(title, tf, W - PAD * 2):
            lw = _tw(tf, line)
            draw.text(((W - lw) // 2, cy), line, font=tf, fill="#FFFFFF")
            cy += _th(tf) + 14

        if body:
            cy += 20
            bf = _font(42)
            for line in _wrap(body, bf, W - PAD * 2):
                lw = _tw(bf, line)
                draw.text(((W - lw) // 2, cy), line, font=bf, fill="#FFFFFFCC")
                cy += _th(bf) + 10

        return img

    # ── API principal ─────────────────────────────────────────────────────────

    def generate(
        self,
        carousel_data: dict,
        progress_callback=None,
    ) -> list[Image.Image]:
        slides = carousel_data.get("slides", [])
        total  = len(slides)
        images: list[Image.Image] = []

        for i, s in enumerate(slides):
            number = s.get("number", i + 1)
            title  = s.get("title", "")
            body   = s.get("body", "")
            visual = s.get("visual_suggestion", "")

            if progress_callback:
                progress_callback(i, total, f"Slide {number}: {title[:40]}")

            if i == 0:
                img = self._slide_cover(title, body, total)
            elif i == total - 1:
                img = self._slide_cta(number, total, title, body)
            else:
                img = self._slide_content(number, total, title, body, visual)

            images.append(img)

        if progress_callback:
            progress_callback(total, total, "Concluido")

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
