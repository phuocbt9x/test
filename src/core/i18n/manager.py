import json
from pathlib import Path
from typing import Any
from contextvars import ContextVar
from threading import Lock
from fastapi import Request
from src.core.configs import settings
from src.core.configs.setting import Environment

current_language: ContextVar[str] = ContextVar("current_language", default="en")
_default_locale: str | None = None
_locale_lock = Lock()


def get_default_locale() -> str:
    global _default_locale
    if _default_locale is not None:
        return _default_locale
    with _locale_lock:
        if _default_locale is None:
            try:
                _default_locale = settings.APP_LOCALE
            except Exception:
                _default_locale = "en"
        return _default_locale


class TranslationManager:
    __slots__ = ("locales_dir", "_cache", "_flat_cache", "_cache_lock", "_languages")

    def __init__(self, locales_dir: Path | None = None):
        self.locales_dir = (
            locales_dir or Path(__file__).parent.parent.parent / "locales"
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._flat_cache: dict[str, dict[str, str]] = {}
        self._cache_lock = Lock()
        self._languages = self._discover_languages()

    def _discover_languages(self) -> list[str]:
        if not self.locales_dir.exists():
            return [get_default_locale()]
        langs = [
            d.name
            for d in self.locales_dir.iterdir()
            if d.is_dir() and any(d.rglob("*.json"))
        ]
        return langs or [get_default_locale()]

    def _load_language(self, lang: str) -> dict[str, Any]:
        lang_dir = self.locales_dir / lang
        if not lang_dir.exists():
            lang_dir = self.locales_dir / get_default_locale()
        translations: dict[str, Any] = {}
        for json_file in sorted(lang_dir.rglob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                rel_path = json_file.relative_to(lang_dir)
                parts = [*rel_path.parts[:-1], json_file.stem]
                if len(parts) == 1:
                    ns = parts[0]
                    translations[ns] = (
                        data[ns]
                        if isinstance(data, dict)
                        and ns in data
                        and isinstance(data[ns], dict)
                        else data
                    )
                else:
                    translations[".".join(parts)] = data
                    parent = translations.setdefault(parts[0], {})
                    if isinstance(parent, dict):
                        for p in parts[1:-1]:
                            parent = parent.setdefault(p, {})
                        parent[parts[-1]] = data
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        flat: dict[str, str] = {}
        for ns_data in translations.values():
            if isinstance(ns_data, dict):
                flat.update({k: v for k, v in ns_data.items() if isinstance(v, str)})
        self._flat_cache[lang] = flat
        return translations

    def _get_translation(self, lang: str) -> dict[str, Any]:
        if settings.APP_ENV == Environment.DEVELOPMENT:
            return self._load_language(lang)
        if lang in self._cache:
            return self._cache[lang]
        with self._cache_lock:
            if lang not in self._cache:
                self._cache[lang] = self._load_language(lang)
            return self._cache[lang]

    @staticmethod
    def _traverse(obj: Any, parts: list[str]) -> str | None:
        for p in parts:
            if isinstance(obj, dict) and p in obj:
                obj = obj[p]
            else:
                return None
        return obj if isinstance(obj, str) else None

    def _get_value(self, data: dict[str, Any], key: str) -> str | None:
        parts = key.split(".")
        for i in range(len(parts), 0, -1):
            ns_key = ".".join(parts[:i])
            if ns_key in data:
                remaining = parts[i:]
                if not remaining:
                    return data[ns_key] if isinstance(data[ns_key], str) else None
                if result := self._traverse(data[ns_key], remaining):
                    return result
        if parts[0] in data and isinstance(data[parts[0]], dict):
            if result := self._traverse(data[parts[0]], parts[1:]):
                return result
        for root in data.values():
            if isinstance(root, dict) and (found := self._traverse(root, parts)):
                return found
        return None

    def _resolve_language(self) -> str:
        try:
            lang = current_language.get()
        except LookupError:
            lang = get_default_locale()
            current_language.set(lang)
            return lang
        if lang == "en":
            default = get_default_locale()
            if default != "en":
                lang = default
                current_language.set(lang)
        return lang

    def translate(self, message: str, **kwargs: Any) -> str:
        lang = self._resolve_language()
        translations = self._get_translation(lang)
        text = (
            self._get_value(translations, message)
            or self._flat_cache.get(lang, {}).get(message)
            or message
        )
        if kwargs and "{" in text and "}" in text:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError, IndexError):
                pass
        return text

    def ntranslate(self, singular: str, plural: str, n: int, **kwargs: Any) -> str:
        lang = self._resolve_language()
        plural_data = self._get_value(self._get_translation(lang), singular)
        text = (
            plural_data.get("one" if n == 1 else "other", plural)
            if isinstance(plural_data, dict)
            else (singular if n == 1 else plural)
        )
        if kwargs or n:
            params = {"count": n, **kwargs}
            if "{" in text and "}" in text:
                try:
                    return text.format(**params)
                except (KeyError, ValueError, IndexError):
                    pass
        return text

    def has_key(self, key: str, lang: str | None = None) -> bool:
        lang = lang or self._resolve_language()
        return self._get_value(
            self._get_translation(lang), key
        ) is not None or key in self._flat_cache.get(lang, {})

    @property
    def current_lang(self) -> str:
        return self._resolve_language()

    @property
    def supported_languages(self) -> list[str]:
        return self._languages


translation_manager = TranslationManager()


async def get_language_from_request(request: Request) -> str:
    lang = (
        request.query_params.get("locale")
        or request.query_params.get("lang")
        or request.cookies.get("language")
        or request.headers.get("Accept-Language", "")
        .split(",")[0]
        .split("-")[0]
        .strip()
    )
    if not lang or lang not in translation_manager.supported_languages:
        lang = get_default_locale()
    current_language.set(lang)
    return lang


def __(message: str, **kwargs: Any) -> str:
    return translation_manager.translate(message, **kwargs)


def n__(singular: str, plural: str, n: int, **kwargs: Any) -> str:
    return translation_manager.ntranslate(singular, plural, n, **kwargs)
