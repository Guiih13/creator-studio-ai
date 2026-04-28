"""
Creator Studio AI

Gerador de carrosseis profissionais com IA.
"""

from __future__ import annotations

import io
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

DATA_DIR = settings.DATA_DIR
USER_ID = "default"  # fase MVP — single user; substituir por auth depois


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
        username=st.session_state.get("username", brand.get("username", "")),
        creator_name=st.session_state.get("creator_name", brand.get("creator_name", "")),
        brand_label=st.session_state.get("brand_label", brand.get("brand_label", "")),
        profile_photo=photo,
        pexels_api_key=settings.PEXELS_API_KEY,
        cache_dir=cache_dir,
    )

    try:
        from src.creators.carousel_html_renderer import CarouselHTMLRenderer, PLAYWRIGHT_OK
        if PLAYWRIGHT_OK:
            return CarouselHTMLRenderer(**kwargs)
        raise ImportError
    except Exception:
        from src.creators.carousel_creator import CarouselCreator
        kwargs.pop("brand_label", None)
        return CarouselCreator(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Marca Pessoal
# ─────────────────────────────────────────────────────────────────────────────

brand = load_brand(DATA_DIR, USER_ID)
saved_photo_bytes = photo_bytes(DATA_DIR, USER_ID)

with st.sidebar:
    st.title("Marca Pessoal")

    accent = st.color_picker(
        "Cor de destaque",
        value=brand.get("accent_color", "#1565C0"),
        key="accent",
    )
    creator_name = st.text_input(
        "Seu nome",
        value=brand.get("creator_name", ""),
        placeholder="Ex: Guilherme Martins",
        key="creator_name",
    )
    username = st.text_input(
        "@username",
        value=brand.get("username", ""),
        placeholder="Ex: guicode_",
        key="username",
    )
    niche = st.text_input(
        "Sua área / nicho",
        value=brand.get("niche", ""),
        placeholder="Ex: médico, designer, dev, coach...",
        key="niche",
    )
    brand_label = st.text_input(
        "Label dos slides",
        value=brand.get("brand_label", ""),
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

st.title("Creator Studio AI")
st.caption("Gere carrosseis profissionais com IA em segundos.")

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
            )
        except Exception as e:
            st.error(f"Erro na geração: {e}")
            st.stop()

    if not data:
        st.error("Não foi possível gerar o roteiro. Tente novamente.")
        st.stop()

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
        st.text_area("", value=data["caption"], height=120, label_visibility="collapsed")

    if data.get("hashtags"):
        st.caption(" ".join(data["hashtags"]))
