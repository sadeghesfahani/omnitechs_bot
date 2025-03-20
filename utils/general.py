
from babel import Locale
def get_language_name(language_code):
    """Return the language of this locale."""
    locale = Locale.parse(language_code)
    return locale.get_language_name()