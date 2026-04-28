from __future__ import annotations

import locale as system_locale
import os
from pathlib import Path
from typing import Callable

from python_i18n import i18n


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCALE_DIR = PROJECT_ROOT / "anki_addon" / "jlpt_coverage" / "locale"
SUPPORTED_LOCALES = {"en_US", "zh_CN"}
FALLBACK_LOCALE = "en_US"


def normalize_locale(value: str | None) -> str:
    locale = (value or "").replace("-", "_")
    if locale in SUPPORTED_LOCALES:
        return locale
    if locale.lower().startswith("zh"):
        return "zh_CN"
    return FALLBACK_LOCALE


def detect_locale() -> str:
    lang = system_locale.getlocale()[0] or os.environ.get("LANG") or ""
    return normalize_locale(lang)


def configure_translations(language: str = "auto") -> Callable[..., str]:
    locale = detect_locale() if language == "auto" else normalize_locale(language)
    if LOCALE_DIR not in i18n.load_path:
        i18n.load_path.append(LOCALE_DIR)
    i18n.set("filename_format", "{locale}.{format}")
    i18n.set("file_format", "json")
    i18n.set("locale", locale)
    i18n.set("fallback", FALLBACK_LOCALE)
    return i18n.t
