from app.utils.logger import get_logger

logger = get_logger(__name__)

def is_output_complete(text: str) -> bool:
    """Verifica se o texto gerado parece completo."""
    if not text or not text.strip():
        return False
        
    text = text.strip()
    
    # Se for muito pequeno, desconfiar (menos de 20 caracteres é irreal pra um post ou diagnóstico)
    if len(text) < 20:
        return False
        
    # Verifica conectivos pendentes no final
    bad_endings = [" e", " para", " com", " que", " de", " da", " do", " em", " na", " no", " fortalece a", " ajuda a", " permite"]
    lower_text = text.lower()
    for ending in bad_endings:
        if lower_text.endswith(ending):
            return False
            
    # Deve terminar com uma pontuação final, uma letra/número (numa hashtag ou link) ou algo válido, mas não cortado no meio.
    # Ex: pode terminar com `.` `!` `?` `"` `'` `>` (fechamento html) ou no meio de markdown como `**`.
    
    return True

def validate_or_retry_generation(generation_func, filename: str, max_retries: int = 1, quality_validator=None, warning_message: str | None = None) -> str:
    """Gera o conteúdo, valida e tenta novamente se estiver cortado."""
    logger.info(f"[BrandOS] Gerando {filename}...")
    
    content = generation_func()
    
    logger.info(f"[BrandOS] Validando {filename}...")
    
    def is_valid(value: str) -> bool:
        if not is_output_complete(value):
            return False
        if quality_validator and not quality_validator(value):
            return False
        return True

    if is_valid(content):
        return content
        
    logger.warning(f"[BrandOS] Saída inválida detectada em {filename}. Tentando gerar novamente...")
    
    for attempt in range(max_retries):
        content = generation_func()
        if is_valid(content):
            logger.info(f"[BrandOS] Validação bem-sucedida na tentativa {attempt + 1} para {filename}.")
            return content
            
    # Se falhou em todos os retries
    message = warning_message or "A geração deste arquivo pode estar incompleta, ter sido cortada pela API ou falhar em critérios de qualidade."
    warning_header = f"> [!WARNING]\n> Aviso do BrandOS: {message}\n\n"
    logger.error(f"[BrandOS] Falha definitiva na validação de {filename} após {max_retries} retries. Salvando com aviso.")
    return warning_header + content
