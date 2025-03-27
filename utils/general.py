
from babel import Locale

def get_language_name(language_code):
    """Return the language name for the given locale code."""
    if not language_code:
        return "Unknown"
    try:
        locale = Locale.parse(language_code)
        return locale.language_name
    except Exception:
        return "Unknown"