"""
Locale system - Simple dict-based i18n
"""

_strings = {}


def load_locale(lang: str = "zh"):
    """Load locale strings. Call once at startup."""
    global _strings
    if lang == "en":
        from src.locale.en import STRINGS
    else:
        from src.locale.zh import STRINGS
    _strings = STRINGS


def t(key: str, **kwargs) -> str:
    """Translate a key. Supports {var} formatting."""
    text = _strings.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
