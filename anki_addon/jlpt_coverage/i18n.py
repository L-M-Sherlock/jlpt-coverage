from __future__ import annotations

import sys
from pathlib import Path

from aqt import mw

try:
    from .python_i18n import i18n
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from python_i18n import i18n


ADDON_DIR = Path(__file__).resolve().parent
SUPPORTED_LOCALES = {"en_US", "zh_CN"}
FALLBACK_LOCALE = "en_US"


def normalize_locale(value: str | None) -> str:
    locale = (value or "").replace("-", "_")
    if locale in SUPPORTED_LOCALES:
        return locale
    if locale.lower().startswith("zh"):
        return "zh_CN"
    return FALLBACK_LOCALE


def anki_locale() -> str:
    try:
        return normalize_locale(str(mw.pm.meta.get("defaultLang", "")))
    except Exception:
        return FALLBACK_LOCALE


locale = anki_locale()

i18n.load_path.append(ADDON_DIR / "locale")
i18n.set("filename_format", "{locale}.{format}")
i18n.set("file_format", "json")
i18n.set("locale", locale)
i18n.set("fallback", FALLBACK_LOCALE)


def t(*args, **kwargs) -> str:
    return i18n.t(*args, **kwargs)
