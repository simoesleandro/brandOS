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

def validate_or_retry_generation(generation_func, filename: str, max_retries: int = 1) -> str:
    """Gera o conteúdo, valida e tenta novamente se estiver cortado."""
    logger.info(f"[BrandOS] Gerando {filename}...")
    
    content = generation_func()
    
    logger.info(f"[BrandOS] Validando {filename}...")
    
    if is_output_complete(content):
        return content
        
    logger.warning(f"[BrandOS] Saída incompleta detectada em {filename}. Tentando gerar novamente...")
    
    for attempt in range(max_retries):
        content = generation_func()
        if is_output_complete(content):
            logger.info(f"[BrandOS] Validação bem-sucedida na tentativa {attempt + 1} para {filename}.")
            return content
            
    # Se falhou em todos os retries
    warning_header = "> [!WARNING]\n> Aviso do BrandOS: A geração deste arquivo pode estar incompleta ou ter sido cortada pela API.\n\n"
    logger.error(f"[BrandOS] Falha definitiva na validação de {filename} após {max_retries} retries. Salvando com aviso.")
    return warning_header + content
