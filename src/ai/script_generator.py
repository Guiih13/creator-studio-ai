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

Slide 1 (cover): Hook visual — o título DEVE parar o scroll. section_label: vazio. NÃO entrega o conteúdo, cria curiosidade irresistível.
Slides do meio: Um conceito por slide. section_label nomeia a posição narrativa (O PROBLEMA, A CAUSA, O ERRO, A SOLUÇÃO, O MÉTODO, DICA BÔNUS, etc.).
Penúltimo: Resumo ou dica bônus surpresa.
Último (CTA): Pergunta para comentários + chamada para ação.

## REGRAS DE TÍTULO

- Máximo 4 palavras — preferencialmente 2-3.
- Todo em MAIÚSCULO no JSON (ex: "CONTEXT ROT.", "A SOLUÇÃO.", "COMPACTAÇÃO MANUAL.").
- Evite títulos descritivos e previsíveis. Prefira títulos que criam tensão, curiosidade ou choque.
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
      "visual_suggestion": "3-5 keywords IN ENGLISH for THIS slide's background photo — must relate to the slide's specific content (ex: doctor office, city skyline, data charts, handshake)"
    }
  ],
  "caption": "legenda do post 2-3 frases mais CTA",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# HOOK STYLES — fórmulas concretas para o título do cover
# ─────────────────────────────────────────────────────────────────────────────

HOOK_STYLES: dict[str, str] = {
    "Choque e polêmica": (
        "O título do COVER deve confrontar diretamente uma crença popular ou prática comum. "
        "Use imperativo forte, negação impactante ou afirmação que contraria o senso comum. "
        "Exemplos de estrutura: 'VOCÊ ESTÁ ERRADO', 'ISSO É MENTIRA', 'PARE DE FAZER ISSO', "
        "'NÃO FUNCIONA', 'É UMA FARSA'. O leitor deve sentir que a crença dele está sendo desafiada."
    ),
    "Pergunta incômoda": (
        "O título do COVER deve ser uma pergunta curta e direta que o leitor não consegue ignorar — "
        "que gera reflexão imediata ou desconforto. "
        "Exemplos de estrutura: 'POR QUE VOCÊ FALHA?', 'ONDE ESTÁ O ERRO?', 'VALE A PENA?', "
        "'VOCÊ SABE MESMO?', 'POR QUÊ NÃO CRESCE?'. Máximo 4 palavras incluindo o ponto de interrogação."
    ),
    "Número impactante": (
        "O título do COVER deve conter um número específico e surpreendente que gera credibilidade e curiosidade. "
        "O número pode ser porcentagem, valor monetário, quantidade de erros, dias, anos, etc. "
        "Exemplos de estrutura: '3 ERROS FATAIS', '90% ERRA ISSO', 'R$50K PERDIDOS', "
        "'7 SINAIS CLAROS', '1 MUDANÇA. TUDO.'. O número ancora a atenção antes do leitor processar o resto."
    ),
    "Segredo revelado": (
        "O título do COVER deve prometer revelar algo que poucos sabem, que é ocultado ou contraintuitivo. "
        "Cria expectativa de revelação exclusiva. "
        "Exemplos de estrutura: 'O QUE OCULTAM', 'A VERDADE É', 'NINGUÉM TE CONTA', "
        "'O SEGREDO REAL', 'O QUE ESTÁ ESCONDIDO'. O leitor sente que vai receber informação privilegiada."
    ),
    "Chamada direta": (
        "O título do COVER deve ser um imperativo urgente e curtíssimo que interrompe o scroll de forma abrupta. "
        "Sem rodeios, sem contexto — direto ao ponto. "
        "Exemplos de estrutura: 'LEIA ISSO AGORA', 'PARA TUDO', 'MUDA TUDO', "
        "'PRESTA ATENÇÃO', 'ISSO TE AFETA'. O impacto vem da brevidade e da força do comando."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# TONE INSTRUCTIONS — instruções concretas por tom (além do label)
# ─────────────────────────────────────────────────────────────────────────────

_TONE_INSTRUCTIONS: dict[str, str] = {
    "Direto e informativo": (
        "Linguagem objetiva e sem rodeios. Frases curtas, afirmativas. "
        "Cada slide entrega um dado ou conceito claro. Sem metáforas excessivas, sem hipérboles."
    ),
    "Provocativo e instigante": (
        "Linguagem que desafia, confronta e incomoda — mas com substância. "
        "Use afirmações fortes, contradições com o senso comum, perguntas retóricas. "
        "Os slides de conteúdo também devem carregar tensão narrativa, não apenas o cover. "
        "Evite suavizar. Se algo é um erro grave, chame de erro grave."
    ),
    "Didático e acessível": (
        "Linguagem clara, com analogias e exemplos do cotidiano. "
        "Explique conceitos como se o leitor nunca tivesse ouvido falar. "
        "Use comparações ('é como se...'), listas de passos, e vocabulário simples."
    ),
    "Técnico e aprofundado": (
        "Linguagem especializada, com terminologia do setor. "
        "Inclua dados precisos, referências a mecanismos e causas. "
        "O leitor-alvo já tem base no assunto — não simplifique em excesso."
    ),
}


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


_DASH_RE = _re.compile(r'\s*[—–]\s*')


def _fix_pt_accents(text: str) -> str:
    for pattern, repl in _PT_FIXES:
        text = pattern.sub(repl, text)
    text = _DASH_RE.sub(' ', text)
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

_TOPIC_GEN_PROMPT = """Você é um estrategista de conteúdo para Instagram. O criador vai te dar uma descrição geral sobre o que quer abordar, e você deve sugerir exatamente 5 temas específicos para carrosseis.

Cada tema deve:
- Ser uma frase completa e específica (não um título de slide, mas o ASSUNTO do carrossel)
- Ter potencial de gerar engajamento alto (curiosidade, polêmica ou utilidade prática)
- Ser diferente dos outros 4 em ângulo e abordagem
- Estar adequado para o formato carrossel (profundidade suficiente para 6-10 slides)

Responda APENAS com JSON válido. Sem texto antes ou depois.

{"topics": ["tema 1 específico e completo", "tema 2", "tema 3", "tema 4", "tema 5"]}"""

_TITLE_GEN_PROMPT = """Gere exatamente 5 opções de título para o COVER de um carrossel Instagram sobre o tema informado.
Cada opção deve usar uma fórmula de hook diferente. Regras:
- Máximo 4 palavras por título, preferencialmente 2-3.
- Todo em MAIÚSCULO.
- Não entregue o conteúdo — crie curiosidade irresistível.
- title_highlight: a palavra ou trecho de maior impacto para destacar em cor de acento.
- hook: rótulo curto da fórmula usada (ex: "Choque", "Pergunta", "Número", "Segredo", "Chamada direta").

Responda APENAS com JSON válido. Sem texto antes ou depois.

{
  "options": [
    {"title": "TÍTULO AQUI", "title_highlight": "PALAVRA", "hook": "Choque e polêmica"},
    {"title": "POR QUE VOCÊ FALHA?", "title_highlight": "FALHA?", "hook": "Pergunta incômoda"},
    {"title": "3 ERROS FATAIS", "title_highlight": "FATAIS", "hook": "Número impactante"},
    {"title": "O QUE OCULTAM", "title_highlight": "OCULTAM", "hook": "Segredo revelado"},
    {"title": "LEIA ISSO AGORA", "title_highlight": "AGORA", "hook": "Chamada direta"}
  ]
}"""

_CAPTION_GEN_PROMPT = """Gere exatamente 5 opções de legenda para publicação no Instagram de um carrossel.
Cada opção deve ter um ângulo diferente: educacional, provocador, narrativa pessoal, dado impactante, pergunta para engajamento.
Regras:
- 2-4 frases por legenda.
- Inclua chamada para ação no final.
- Use emojis com moderação (máximo 2-3 por legenda).
- Linguagem natural, não robótica.

Responda APENAS com JSON válido. Sem texto antes ou depois.

{"options": ["legenda 1", "legenda 2", "legenda 3", "legenda 4", "legenda 5"]}"""


def generate_topic_options(
    description: str,
    anthropic_api_key: str,
    model: str = "claude-sonnet-4-6",
    niche: str = "",
) -> list[str]:
    """Sugere 5 temas específicos de carrossel a partir de uma descrição ampla."""
    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    niche_ctx = f"Nicho/área do criador: {niche}\n" if niche else ""
    user_msg = f"{niche_ctx}Descrição do que o criador quer abordar: {description}"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=512,
            system=_TOPIC_GEN_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        data = _parse_json(msg.content[0].text)
        if data and "topics" in data:
            return [t for t in data["topics"] if isinstance(t, str)]
    except Exception:
        pass
    return []


def generate_title_options(
    topic: str,
    anthropic_api_key: str,
    model: str = "claude-sonnet-4-6",
    niche: str = "",
) -> list[dict]:
    """Gera 5 opções de título para o cover. Retorna lista de {title, title_highlight, hook}."""
    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    niche_ctx = f"Nicho do criador: {niche}\n" if niche else ""
    user_msg = f"{niche_ctx}Tema do carrossel: {topic}"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=512,
            system=_TITLE_GEN_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        data = _parse_json(msg.content[0].text)
        if data and "options" in data:
            return data["options"]
    except Exception:
        pass
    return []


def generate_caption_options(
    topic: str,
    chosen_title: str,
    anthropic_api_key: str,
    model: str = "claude-sonnet-4-6",
    niche: str = "",
) -> list[str]:
    """Gera 5 opções de legenda para publicação. Retorna lista de strings."""
    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    niche_ctx = f"Nicho do criador: {niche}\n" if niche else ""
    user_msg = f"{niche_ctx}Tema do carrossel: {topic}\nTítulo do cover escolhido: {chosen_title}"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            system=_CAPTION_GEN_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        data = _parse_json(msg.content[0].text)
        if data and "options" in data:
            return [o for o in data["options"] if isinstance(o, str)]
    except Exception:
        pass
    return []


def build_user_prompt(
    topic: str,
    niche: str = "",
    n_slides: int = 8,
    objective: str = "Educar e gerar engajamento",
    tone: str = "Direto e informativo",
    hook_style: str = "",
    required_topics: list[str] | None = None,
    chosen_title: str = "",
    chosen_caption: str = "",
) -> str:
    niche_section = f"Nicho/área do criador: {niche}\n" if niche else ""

    tone_instr = _TONE_INSTRUCTIONS.get(tone, "")
    tone_section = f"\n## TOM — INSTRUÇÕES ESPECÍFICAS\n\n{tone_instr}\n" if tone_instr else ""

    hook_instr = HOOK_STYLES.get(hook_style, "")
    hook_section = f"\n## ESTILO DO HOOK (COVER)\n\n{hook_instr}\n" if hook_instr else ""

    title_section = (
        f"\n## TÍTULO DO COVER — JÁ DEFINIDO PELO CRIADOR\n\n"
        f"Use EXATAMENTE este título no slide 1: {chosen_title}\n"
        f"Mantenha o title_highlight consistente com o título.\n"
        if chosen_title else ""
    )

    caption_section = (
        f"\n## LEGENDA DO POST — JÁ DEFINIDA PELO CRIADOR\n\n"
        f"Use EXATAMENTE esta legenda no campo 'caption': {chosen_caption}\n"
        if chosen_caption else ""
    )

    required_section = ""
    if required_topics:
        items = "\n".join(f"- {t}" for t in required_topics if t.strip())
        if items:
            required_section = (
                f"\n## TÓPICOS OBRIGATÓRIOS\n\n"
                f"Os slides devem cobrir obrigatoriamente os seguintes pontos "
                f"(distribua-os naturalmente ao longo do carrossel):\n{items}\n"
            )

    return (
        f"{niche_section}"
        f"## CONFIGURAÇÃO DO CARROSSEL\n\n"
        f"Data atual: {date.today().strftime('%d/%m/%Y')}\n"
        f"Tema: {topic}\n"
        f"Objetivo: {objective}\n"
        f"Tom: {tone}\n"
        f"Número de slides: {n_slides}\n"
        f"{tone_section}"
        f"{hook_section}"
        f"{title_section}"
        f"{caption_section}"
        f"{required_section}\n"
        f"Crie um carrossel com exatamente {n_slides} slides sobre este tema."
    )


def generate_carousel_script(
    topic: str,
    anthropic_api_key: str,
    model: str = "claude-sonnet-4-6",
    niche: str = "",
    n_slides: int = 8,
    objective: str = "Educar e gerar engajamento",
    tone: str = "Direto e informativo",
    hook_style: str = "",
    required_topics: list[str] | None = None,
    chosen_title: str = "",
    chosen_caption: str = "",
) -> dict | None:
    """
    Gera roteiro de carrossel via Claude.

    Returns:
        dict com 'slides', 'caption', 'hashtags' ou None em caso de erro.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    user_prompt = build_user_prompt(
        topic, niche, n_slides, objective, tone,
        hook_style, required_topics, chosen_title, chosen_caption,
    )

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
