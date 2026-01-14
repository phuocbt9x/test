import json
from pathlib import Path
from typing import Any
from contextvars import ContextVar
from threading import Lock
from fastapi import Request
from src.core.configs import settings

current_language: ContextVar[str] = ContextVar("current_language", default="en")

_default_locale: str | None = None
_locale_lock = Lock()


def get_default_locale() -> str:
    global _default_locale
    if _default_locale is not None:
        return _default_locale

    with _locale_lock:
        if _default_locale is not None:
            return _default_locale
        try:
            _default_locale = settings.APP_LOCALE
        except Exception:
            _default_locale = "en"
        return _default_locale


class TranslationManager:
    def __init__(self, locales_dir: Path | None = None):
        self.locales_dir = (
            locales_dir or Path(__file__).parent.parent.parent / "locales"
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._flat_cache: dict[str, dict[str, str]] = {}
        self._cache_lock = Lock()
        self._languages = self._discover_languages()

    __slots__ = ("locales_dir", "_cache", "_flat_cache", "_cache_lock", "_languages")

    def _discover_languages(self) -> list[str]:
        default_locale = get_default_locale()
        if not self.locales_dir.exists():
            return [default_locale]
        languages = [
            d.name
            for d in self.locales_dir.iterdir()
            if d.is_dir() and any(d.glob("*.json"))
        ]

        return languages or [default_locale]

    def _load_language(self, lang: str) -> dict[str, Any]:
        default_locale = get_default_locale()
        lang_dir = self.locales_dir / lang
        if not lang_dir.exists():
            lang_dir = self.locales_dir / default_locale

        translations = {}
        for json_file in sorted(lang_dir.glob("*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    ns = json_file.stem
                    if (
                        isinstance(data, dict)
                        and ns in data
                        and isinstance(data[ns], dict)
                    ):
                        translations[ns] = data[ns]
                    else:
                        translations[ns] = data
            except (FileNotFoundError, json.JSONDecodeError):
                continue

        self._build_flat_cache(lang, translations)
        return translations

    def _build_flat_cache(self, lang: str, translations: dict[str, Any]) -> None:
        flat = {}
        for ns_data in translations.values():
            if isinstance(ns_data, dict):
                flat.update({k: v for k, v in ns_data.items() if isinstance(v, str)})
        self._flat_cache[lang] = flat

    def _get_translation(self, lang: str) -> dict[str, Any]:
        if lang in self._cache:
            return self._cache[lang]

        with self._cache_lock:
            if lang not in self._cache:
                self._cache[lang] = self._load_language(lang)
            return self._cache[lang]

    def _get_value(self, data: dict[str, Any], key: str) -> str | None:
        namespace, *rest = key.split(".", 1)

        def traverse(obj: Any, parts: list[str]) -> str | None:
            curr = obj
            for p in parts:
                if isinstance(curr, dict) and p in curr:
                    curr = curr[p]
                else:
                    return None
            return curr if isinstance(curr, str) else None

        if namespace in data and isinstance(data[namespace], dict):
            if not rest:
                val = data[namespace]
                return val if isinstance(val, str) else None
            return traverse(data[namespace], rest[0].split("."))

        parts = key.split(".")
        for root in data.values():
            if isinstance(root, dict):
                found = traverse(root, parts)
                if found is not None:
                    return found
        return None

    def translate(self, message: str, **kwargs) -> str:
        lang = self._resolve_language()
        translations = self._get_translation(lang)

        text = (
            self._get_value(translations, message)
            or self._flat_cache.get(lang, {}).get(message)
            or message
        )
        if kwargs and ("{" in text and "}" in text):
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def _resolve_language(self) -> str:
        try:
            lang = current_language.get()
        except LookupError:
            lang = get_default_locale()
            current_language.set(lang)
            return lang

        if lang == "en":
            default_locale = get_default_locale()
            if default_locale != "en":
                lang = default_locale
                current_language.set(lang)
        return lang

    def ntranslate(self, singular: str, plural: str, n: int, **kwargs) -> str:
        lang = self._resolve_language()
        plural_data = self._get_value(self._get_translation(lang), singular)

        text = (
            plural_data.get("one" if n == 1 else "other", plural)
            if isinstance(plural_data, dict)
            else singular
            if n == 1
            else plural
        )

        if kwargs or "{count}" in text:
            data = {"count": n, **kwargs}
            if "{" in text and "}" in text:
                try:
                    return text.format(**data)
                except Exception:
                    return text
        return text

    def has_key(self, key: str, lang: str | None = None) -> bool:
        if lang is None:
            lang = self._resolve_language()
        translations = self._get_translation(lang)
        return self._get_value(
            translations, key
        ) is not None or key in self._flat_cache.get(lang, {})

    @property
    def current_lang(self) -> str:
        return self._resolve_language()

    @property
    def supported_languages(self) -> list[str]:
        return self._languages


translation_manager = TranslationManager()


async def get_language_from_request(request: Request) -> str:
    default_locale = get_default_locale()
    lang = (
        request.headers.get("Accept-Language", default_locale)
        .split(",")[0]
        .split("-")[0]
        .strip()
    )
    lang = request.query_params.get("lang", lang)
    lang = request.query_params.get("locale", lang)
    lang = request.cookies.get("language", lang)

    if lang not in translation_manager.supported_languages:
        lang = default_locale

    current_language.set(lang)
    return lang


def __(message: str, **kwargs) -> str:
    return translation_manager.translate(message, **kwargs)


def n__(singular: str, plural: str, n: int, **kwargs) -> str:
    return translation_manager.ntranslate(singular, plural, n, **kwargs)
