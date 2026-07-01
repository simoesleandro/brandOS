import re

def slugify(text: str) -> str:
    """
    Convert a string into a slug.
    Removes special characters, converts spaces to hyphens, and lowercases.
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')
