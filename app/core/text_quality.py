import re


_MISSING_ACCENT_PATTERNS = {
    "analise": "análise",
    "atencao": "atenção",
    "ate": "até",
    "construcao": "construção",
    "consultavel": "consultável",
    "conteudo": "conteúdo",
    "decisao": "decisão",
    "descricao": "descrição",
    "distribuicao": "distribuição",
    "informacoes": "informações",
    "interacao": "interação",
    "interacoes": "interações",
    "interpretacao": "interpretação",
    "maquina": "máquina",
    "padroes": "padrões",
    "pratica": "prática",
    "pratico": "prático",
    "proximo": "próximo",
    "publica": "pública",
    "publico": "público",
    "publicos": "públicos",
    "reacoes": "reações",
    "responsavel": "responsável",
    "revisao": "revisão",
    "sentencas": "sentenças",
    "tecnica": "técnica",
    "tecnico": "técnico",
    "ultima": "última",
}


def find_missing_portuguese_accents(text: str) -> list[str]:
    """Return likely Portuguese words that should be accented outside hashtags."""
    if not text:
        return []

    text_without_hashtags = re.sub(r"#\w+", "", text.lower())
    found = []
    for plain_word in _MISSING_ACCENT_PATTERNS:
        if re.search(rf"\b{re.escape(plain_word)}\b", text_without_hashtags):
            found.append(plain_word)
    return sorted(found)


def is_linkedin_post_text_quality_ok(text: str) -> bool:
    """Block obvious LinkedIn post drafts with missing Brazilian Portuguese accents."""
    return len(find_missing_portuguese_accents(text)) == 0
