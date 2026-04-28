"""
Creator Studio AI

Gerador de carrosseis profissionais com IA.
"""

from __future__ import annotations

import io
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

from config import settings
from src.ai.script_generator import generate_carousel_script
from src.creators.brand_profile import (
    load_brand, save_brand,
    load_photo, save_photo, photo_bytes,
)

st.set_page_config(
    page_title="Creator Studio AI",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

/* Hero */
.hero-badge {
    display: inline-block;
    background: linear-gradient(135deg, #7C3AED22, #EC489922);
    border: 1px solid #7C3AED44;
    color: #a78bfa;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .15em;
    text-transform: uppercase;
    padding: 5px 14px;
    border-radius: 100px;
    margin-bottom: 16px;
}
.hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(135deg, #fff 30%, #a78bfa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 12px 0;
}
.hero-sub {
    font-size: 1.05rem;
    color: rgba(255,255,255,.45);
    margin-bottom: 32px;
    line-height: 1.6;
}

/* Input label */
.input-label {
    font-size: 13px;
    font-weight: 600;
    color: rgba(255,255,255,.6);
    letter-spacing: .04em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

/* Section divider */
.section-card {
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 16px;
    padding: 24px;
    margin: 16px 0;
}

/* Primary button */
div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #7C3AED, #EC4899) !important;
    border: none !important;
    border-radius: 14px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: .03em !important;
    padding: 0.65rem 1.5rem !important;
    box-shadow: 0 4px 24px rgba(124,58,237,.3) !important;
    transition: transform .15s, box-shadow .15s !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(124,58,237,.45) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0f0f13 !important;
    border-right: 1px solid rgba(255,255,255,.07) !important;
}
[data-testid="stSidebar"] .stCaption {
    color: rgba(255,255,255,.35) !important;
    font-size: 11px !important;
    letter-spacing: .12em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,.08) !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,.02) !important;
}

/* Toggle */
[data-testid="stToggle"] label {
    font-weight: 600 !important;
}

/* Progress bar */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #7C3AED, #EC4899) !important;
}

/* Download button */
div[data-testid="stDownloadButton"] button {
    border-radius: 12px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

DATA_DIR = settings.DATA_DIR
USER_ID = "default"  # fase MVP — single user; substituir por auth depois


@st.cache_resource(show_spinner=False)
def _ensure_playwright() -> bool:
    """Instala o binário do Chromium uma vez por instância do servidor."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
            capture_output=True, text=True, timeout=300,
        )
        return result.returncode == 0
    except Exception:
        return False


_ensure_playwright()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_creator() -> object:
    """Retorna CarouselHTMLRenderer se Playwright disponível, senão CarouselCreator."""
    from src.creators.brand_profile import load_brand, load_photo
    brand = load_brand(DATA_DIR, USER_ID)
    photo = load_photo(DATA_DIR, USER_ID)
    cache_dir = str(Path(DATA_DIR) / "pexels_cache")

    kwargs = dict(
        accent_color=st.session_state.get("accent", brand.get("accent_color", "#1565C0")),
        accent_color_2=st.session_state.get("accent2", brand.get("accent_color_2", "")),
        accent_color_3=st.session_state.get("accent3", brand.get("accent_color_3", "")),
        username=st.session_state.get("username", brand.get("username", "")),
        creator_name=st.session_state.get("creator_name", brand.get("creator_name", "")),
        brand_label=st.session_state.get("brand_label", brand.get("brand_label", "")),
        profile_photo=photo,
        pexels_api_key=settings.PEXELS_API_KEY,
        cache_dir=cache_dir,
        use_images=st.session_state.get("use_images", True),
    )

    fonts_dir = str(Path(DATA_DIR) / "fonts")

    try:
        from src.creators.carousel_html_renderer import CarouselHTMLRenderer, PLAYWRIGHT_OK
        if PLAYWRIGHT_OK:
            return CarouselHTMLRenderer(**kwargs)
        raise ImportError
    except Exception:
        from src.creators.carousel_creator import CarouselCreator
        return CarouselCreator(**kwargs, fonts_dir=fonts_dir)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Marca Pessoal
# ─────────────────────────────────────────────────────────────────────────────

brand = load_brand(DATA_DIR, USER_ID)
saved_photo_bytes = photo_bytes(DATA_DIR, USER_ID)

# Fallback para defaults de secrets quando não há dados salvos no disco
def _brand_default(key: str, secret_val: str) -> str:
    return brand.get(key) or secret_val

with st.sidebar:
    st.title("Marca Pessoal")

    st.caption("Paleta de cores dos slides")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        accent = st.color_picker(
            "Destaque",
            value=_brand_default("accent_color", settings.DEFAULT_ACCENT_COLOR),
            help="Cor dos highlights, labels e separadores",
            key="accent",
        )
    with col_b:
        accent2 = st.color_picker(
            "Fundo escuro",
            value=_brand_default("accent_color_2", "#0A0A0A"),
            help="Fundo dos slides escuros e cover",
            key="accent2",
        )
    with col_c:
        accent3 = st.color_picker(
            "Fundo claro",
            value=_brand_default("accent_color_3", "#F4EFE8"),
            help="Fundo dos slides claros",
            key="accent3",
        )
    creator_name = st.text_input(
        "Seu nome",
        value=_brand_default("creator_name", settings.DEFAULT_CREATOR_NAME),
        placeholder="Ex: Guilherme Martins",
        key="creator_name",
    )
    username = st.text_input(
        "@username",
        value=_brand_default("username", settings.DEFAULT_USERNAME),
        placeholder="Ex: guicode_",
        key="username",
    )
    niche = st.text_input(
        "Sua área / nicho",
        value=_brand_default("niche", settings.DEFAULT_NICHE),
        placeholder="Ex: médico, designer, dev, coach...",
        key="niche",
    )
    brand_label = st.text_input(
        "Label dos slides",
        value=_brand_default("brand_label", settings.DEFAULT_BRAND_LABEL),
        placeholder="Ex: @guicode_, SAUDE EM FOCO...",
        help="Aparece no canto superior de cada slide. Deixe vazio para não exibir.",
        key="brand_label",
    )

    st.divider()

    if saved_photo_bytes:
        st.image(saved_photo_bytes, caption="Foto atual", width=100)
    photo_file = st.file_uploader(
        "Foto de perfil",
        type=["jpg", "jpeg", "png"],
        key="photo_file",
    )
    if photo_file:
        st.image(photo_file, width=100)

    if st.button("Salvar marca", use_container_width=True):
        save_brand(
            DATA_DIR, USER_ID,
            creator_name=creator_name,
            username=username,
            accent_color=accent,
            accent_color_2=accent2,
            accent_color_3=accent3,
            brand_label=brand_label,
            niche=niche,
        )
        if photo_file:
            photo_file.seek(0)
            img = Image.open(io.BytesIO(photo_file.read())).convert("RGB")
            save_photo(DATA_DIR, img, USER_ID)
        st.success("Salvo!")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — Gerador
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="padding: 8px 0 24px 0;">
  <div class="hero-badge">✦ Powered by Claude AI</div>
  <div class="hero-title">Creator Studio AI</div>
  <div class="hero-sub">Gere carrosseis editoriais prontos para o Instagram<br>em segundos — sem Canva, sem template.</div>
</div>
""", unsafe_allow_html=True)

st.divider()

topic = st.text_input(
    "Sobre o que é o carrossel?",
    placeholder="Ex: Como usar IA no consultório médico sem violar a LGPD",
)

with st.expander("Configurações avançadas"):
    col1, col2 = st.columns(2)
    with col1:
        n_slides = st.slider("Número de slides", min_value=5, max_value=12, value=8)
        objective = st.selectbox(
            "Objetivo",
            ["Educar e gerar engajamento", "Gerar leads", "Vender produto/serviço", "Construir autoridade"],
        )
    with col2:
        tone = st.selectbox(
            "Tom",
            ["Direto e informativo", "Provocativo e instigante", "Didático e acessível", "Técnico e aprofundado"],
        )
        use_images = st.toggle(
            "Imagens automáticas nos slides",
            value=True,
            key="use_images",
            help="Busca fotos do Pexels automaticamente. Desative para slides sem imagem de fundo.",
        )

    required_topics_raw = st.text_area(
        "Tópicos obrigatórios",
        placeholder="Digite um tópico por linha. A IA garantirá que todos apareçam no carrossel.\nEx:\nBenefícios do produto X\nComparação com concorrentes\nChamada para compra",
        height=120,
        help="Pontos que obrigatoriamente devem aparecer nos slides.",
    )
    required_topics = [t.strip() for t in required_topics_raw.splitlines() if t.strip()]

gerar = st.button("Gerar Carrossel", type="primary", use_container_width=True, disabled=not topic)

if gerar and topic:
    if not settings.ANTHROPIC_API_KEY:
        st.error("Configure ANTHROPIC_API_KEY no arquivo .env")
        st.stop()

    with st.spinner("Gerando roteiro com IA..."):
        try:
            data = generate_carousel_script(
                topic=topic,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                model=settings.ANTHROPIC_MODEL,
                niche=st.session_state.get("niche", ""),
                n_slides=n_slides,
                objective=objective,
                tone=tone,
                required_topics=required_topics or None,
            )
        except Exception as e:
            st.error(f"Erro na geração: {e}")
            st.stop()

    if not data:
        st.error("Não foi possível gerar o roteiro. Tente novamente.")
        st.stop()

    st.session_state["carousel_data"] = data

if "carousel_data" in st.session_state:
    data = st.session_state["carousel_data"]

    st.success(f"Roteiro gerado — {len(data.get('slides', []))} slides")

    # Preview dos slides do roteiro
    with st.expander("Ver roteiro completo", expanded=False):
        for slide in data.get("slides", []):
            st.markdown(f"**Slide {slide.get('number', '')}** — {slide.get('section_label', 'COVER')}")
            st.markdown(f"_{slide.get('title', '')}_")
            st.markdown(slide.get("body", ""))
            st.divider()

    st.divider()
    st.subheader("Gerar Imagens")

    gerar_imgs = st.button("Renderizar Slides", type="primary", use_container_width=True)

    if gerar_imgs:
        creator = _get_creator()
        bar = st.progress(0, text="Iniciando...")

        def _prog(current, total, label):
            bar.progress(current / max(total, 1), text=f"Slide {current}/{total}: {label[:50]}")

        try:
            images = creator.generate(data, progress_callback=_prog)
        except Exception:
            # Playwright falhou — tenta com renderer PIL preservando todas as cores
            from src.creators.carousel_creator import CarouselCreator
            brand_local = load_brand(DATA_DIR, USER_ID)
            photo_local = load_photo(DATA_DIR, USER_ID)
            creator = CarouselCreator(
                accent_color=st.session_state.get("accent", brand_local.get("accent_color", "#1565C0")),
                accent_color_2=st.session_state.get("accent2", brand_local.get("accent_color_2", "")),
                accent_color_3=st.session_state.get("accent3", brand_local.get("accent_color_3", "")),
                username=st.session_state.get("username", brand_local.get("username", "")),
                creator_name=st.session_state.get("creator_name", brand_local.get("creator_name", "")),
                brand_label=st.session_state.get("brand_label", brand_local.get("brand_label", "")),
                profile_photo=photo_local,
                pexels_api_key=settings.PEXELS_API_KEY,
                cache_dir=str(Path(DATA_DIR) / "pexels_cache"),
                use_images=st.session_state.get("use_images", True),
                fonts_dir=str(Path(DATA_DIR) / "fonts"),
            )
            images = creator.generate(data, progress_callback=_prog)
        bar.progress(1.0, text="Concluído!")

        st.success(f"{len(images)} slides gerados.")

        cols = st.columns(min(3, len(images)))
        for i, img in enumerate(images[:3]):
            with cols[i]:
                st.image(img, caption=f"Slide {i + 1}", use_container_width=True)

        zip_bytes = creator.to_zip(images)
        st.download_button(
            label="Baixar todos os slides (ZIP)",
            data=zip_bytes,
            file_name=f"carrossel_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip",
            use_container_width=True,
        )

    # Legenda e hashtags
    if data.get("caption"):
        st.divider()
        st.subheader("Legenda")
        st.text_area("Legenda", value=data["caption"], height=120, label_visibility="collapsed")

    if data.get("hashtags"):
        st.caption(" ".join(data["hashtags"]))
