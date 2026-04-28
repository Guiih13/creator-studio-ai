"""
Script Generator

Gera roteiros de carrossel via Claude API.
Desacoplado de qualquer UI — pode ser chamado de Streamlit, FastAPI, CLI, etc.
"""

from __future__ import annotations

import json
import re as _re
from datetime import date


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT EDITORIAL
# ─────────────────────────────────────────────────────────────────────────────

CAROUSEL_SYSTEM = """## IDIOMA E ORTOGRAFIA — REGRA ABSOLUTA

Todo o texto gerado em português DEVE usar acentuação correta e completa.
Exemplos obrigatórios: você (não "voce"), não (não "nao"), está (não "esta"), então (não "entao"),
também (não "tambem"), é (não "e" quando verbo), ação (não "acao"), à/às, através.
Nunca omitir cedilha (ç), til (ã/õ), acento agudo (é/á/ó/ú/í) ou circunflexo (ê/â/ô).

---

## MISSÃO

Você é um especialista em carrosseis de Instagram com estilo editorial.
Referência visual: @brandsdecoded — tipografia gigante, section labels, alternância dark/light.
Carrosseis devem ser: informativos, visualmente impactantes, com progressão narrativa que prende do slide 1 ao último.

## PRINCÍPIOS EDITORIAIS

- Cada slide = um conceito nomeado. O section_label é o rótulo editorial (como em revista).
- Título: 2-4 palavras em MAIÚSCULO, impacto de manchete de jornal.
- Corpo: 20-35 palavras — denso, direto, com dados e exemplos concretos.
- Progressão lógica: cada slide cria expectativa para o próximo.
- Sem adjetivos genéricos. Linguagem que provoca e informa.

## ESTRUTURA

Slide 1 (cover): Hook visual — título provocativo que para o scroll. section_label: vazio. Não entrega o conteúdo, cria curiosidade.
Slides do meio: Um conceito por slide. section_label nomeia a posição narrativa (O PROBLEMA, A CAUSA, O ERRO, A SOLUÇÃO, O MÉTODO, DICA BÔNUS, etc.).
Penúltimo: Resumo ou dica bônus surpresa.
Último (CTA): Pergunta para comentários + chamada para ação.

## REGRAS DE TÍTULO

- Máximo 4 palavras — preferencialmente 2-3.
- Todo em MAIÚSCULO no JSON (ex: "CONTEXT ROT.", "A SOLUÇÃO.", "COMPACTAÇÃO MANUAL.").
- title_highlight: a última palavra ou o conceito-chave para destacar na cor de acento.
  Exemplo: título "CONTEXT ROT." → title_highlight "ROT."
  Exemplo: título "O CUSTO É COMPOSTO." → title_highlight "COMPOSTO."

## BOLD_KEYWORDS

- 2-4 termos ou frases curtas do corpo que merecem negrito (dados, números, conceitos-chave).
- Devem ser substrings exatas do campo "body".

## FERRAMENTAS E TECNOLOGIA

Quando mencionar ferramentas, IAs ou modelos:
- NUNCA afirme que uma versão é "a mais recente" ou "a melhor" — muda rápido.
- Use: "uma das ferramentas mais avançadas", "o modelo mais capaz disponível".
- Se o criador forneceu versões específicas no contexto, evite números de versão.

## FORMATO DE OUTPUT

Responda APENAS com JSON válido. Sem texto antes ou depois. Sem markdown. Sem ```json.

{
  "slides": [
    {
      "number": 1,
      "section_label": "rótulo editorial 2-4 palavras MAIÚSCULO (vazio no cover)",
      "title": "TÍTULO 2-4 PALAVRAS MAIÚSCULO",
      "title_highlight": "PALAVRA DO TÍTULO para cor de acento",
      "body": "explicação 20-35 palavras com dados e exemplos concretos",
      "bold_keywords": ["termo chave", "dado impactante"],
      "visual_suggestion": "3-5 keywords IN ENGLISH for cover background photo (ex: doctor office, city skyline)"
    }
  ],
  "caption": "legenda do post 2-3 frases mais CTA",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# PT ACCENT FIXES
# ─────────────────────────────────────────────────────────────────────────────

_PT_FIXES = [
    (_re.compile(r'\bvoce\b',       _re.IGNORECASE), lambda m: 'Você'   if m.group()[0].isupper() else 'você'),
    (_re.compile(r'\bnao\b',        _re.IGNORECASE), lambda m: 'Não'    if m.group()[0].isupper() else 'não'),
    (_re.compile(r'\bentao\b',      _re.IGNORECASE), lambda m: 'Então'  if m.group()[0].isupper() else 'então'),
    (_re.compile(r'\btambem\b',     _re.IGNORECASE), lambda m: 'Também' if m.group()[0].isupper() else 'também'),
    (_re.compile(r'\balem\b',       _re.IGNORECASE), lambda m: 'Além'   if m.group()[0].isupper() else 'além'),
    (_re.compile(r'\bate\b',        _re.IGNORECASE), lambda m: 'Até'    if m.group()[0].isupper() else 'até'),
    (_re.compile(r'\bapos\b',       _re.IGNORECASE), lambda m: 'Após'   if m.group()[0].isupper() else 'após'),
    (_re.compile(r'\batrave[sz]\b', _re.IGNORECASE), lambda m: 'Através' if m.group()[0].isupper() else 'através'),
    (_re.compile(r'\bporem\b',      _re.IGNORECASE), lambda m: 'Porém'  if m.group()[0].isupper() else 'porém'),
]


def _fix_pt_accents(text: str) -> str:
    for pattern, repl in _PT_FIXES:
        text = pattern.sub(repl, text)
    return text


def _fix_dict_accents(data: dict) -> dict:
    result = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = _fix_pt_accents(v)
        elif isinstance(v, list):
            fixed = []
            for item in v:
                if isinstance(item, dict):
                    fixed.append(_fix_dict_accents(item))
                elif isinstance(item, str):
                    fixed.append(_fix_pt_accents(item))
                else:
                    fixed.append(item)
            result[k] = fixed
        else:
            result[k] = v
    return result


def _parse_json(text: str) -> dict | None:
    if not text:
        return None
    for attempt in [
        lambda t: json.loads(t.strip()),
        lambda t: json.loads("\n".join(t.strip().split("\n")[1:-1]).strip()) if "```" in t else None,
        lambda t: json.loads(t[t.find("{"):t.rfind("}") + 1]) if "{" in t else None,
    ]:
        try:
            result = attempt(text)
            if result:
                return _fix_dict_accents(result)
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def build_user_prompt(
    topic: str,
    niche: str = "",
    n_slides: int = 8,
    objective: str = "Educar e gerar engajamento",
    tone: str = "Direto e informativo",
    required_topics: list[str] | None = None,
) -> str:
    niche_section = f"Nicho/área do criador: {niche}\n" if niche else ""
    required_section = ""
    if required_topics:
        items = "\n".join(f"- {t}" for t in required_topics if t.strip())
        if items:
            required_section = f"\n## TÓPICOS OBRIGATÓRIOS\n\nOs slides devem cobrir obrigatoriamente os seguintes pontos (distribua-os naturalmente ao longo do carrossel):\n{items}\n"
    return f"""{niche_section}## CONFIGURAÇÃO DO CARROSSEL

Data atual: {date.today().strftime("%d/%m/%Y")}
Tema: {topic}
Objetivo: {objective}
Tom: {tone}
Número de slides: {n_slides}
{required_section}
Crie um carrossel com exatamente {n_slides} slides sobre este tema."""


def generate_carousel_script(
    topic: str,
    anthropic_api_key: str,
    model: str = "claude-sonnet-4-6",
    niche: str = "",
    n_slides: int = 8,
    objective: str = "Educar e gerar engajamento",
    tone: str = "Direto e informativo",
    required_topics: list[str] | None = None,
) -> dict | None:
    """
    Gera roteiro de carrossel via Claude.

    Returns:
        dict com 'slides', 'caption', 'hashtags' ou None em caso de erro.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    user_prompt = build_user_prompt(topic, niche, n_slides, objective, tone, required_topics)

    try:
        msg = client.messages.create(
            model=model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": CAROUSEL_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        return _parse_json(msg.content[0].text)
    except Exception as e:
        raise RuntimeError(f"Erro na geração: {e}") from e
