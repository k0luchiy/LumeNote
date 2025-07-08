import json
import os
from typing import Dict

# This will hold all our translations loaded from the JSON files.
_translations: Dict[str, Dict[str, str]] = {}
LOCALES_DIR = os.path.join(os.path.dirname(__file__), '..', 'locales')

def load_translations():
    """Loads all .json translation files from the locales directory."""
    global _translations
    for filename in os.listdir(LOCALES_DIR):
        if filename.endswith(".json"):
            lang_code = filename.split(".")[0]
            with open(os.path.join(LOCALES_DIR, filename), "r", encoding="utf-8") as f:
                _translations[lang_code] = json.load(f)
    print(f"Loaded translations for: {list(_translations.keys())}")


def get_text(key: str, lang_code: str = "en", **kwargs) -> str:
    """
    Gets a translated text by its key for a specific language.
    Falls back to English if the key is not found in the target language.
    Formats the string with any provided keyword arguments.
    """
    # Ensure we fall back to a supported language, default is 'en'
    if lang_code not in _translations:
        lang_code = "en"

    # Get the text template, defaulting to English if the key is missing
    template = _translations.get(lang_code, {}).get(key)
    if not template:
        template = _translations.get("en", {}).get(key, f"_{key}_") # Return key if not found at all

    # Format the string with placeholder values
    return template.format(**kwargs)