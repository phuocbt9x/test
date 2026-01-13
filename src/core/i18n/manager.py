import json
from pathlib import Path
from typing import Any
from contextvars import ContextVar
from fastapi import Request

current_language: ContextVar[str] = ContextVar("current_language", default="en")


class TranslationManager:
    def __init__(self, locales_dir: Path | None = None):
        self.locales_dir = (
            locales_dir or Path(__file__).parent.parent.parent / "locales"
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._flat_cache: dict[str, dict[str, str]] = {}
        self._languages = self._discover_languages()

    __slots__ = ("locales_dir", "_cache", "_flat_cache", "_languages")

    def _discover_languages(self) -> list[str]:
        if not self.locales_dir.exists():
            return ["en"]
        return [
            d.name
            for d in self.locales_dir.iterdir()
            if d.is_dir() and any(d.glob("*.json"))
        ] or ["en"]

    def _load_language(self, lang: str) -> dict[str, Any]:
        lang_dir = self.locales_dir / lang
        if not lang_dir.exists():
            lang_dir = self.locales_dir / "en"

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
        lang = current_language.get()
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

    def ntranslate(self, singular: str, plural: str, n: int, **kwargs) -> str:
        plural_data = self._get_value(
            self._get_translation(current_language.get()), singular
        )

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
        lang = lang or current_language.get()
        translations = self._get_translation(lang)
        return self._get_value(
            translations, key
        ) is not None or key in self._flat_cache.get(lang, {})

    @property
    def current_lang(self) -> str:
        return current_language.get()

    @property
    def supported_languages(self) -> list[str]:
        return self._languages


translation_manager = TranslationManager()


async def get_language_from_request(request: Request) -> str:
    lang = (
        request.headers.get("Accept-Language", "en").split(",")[0].split("-")[0].strip()
    )
    lang = request.query_params.get("lang", lang)
    lang = request.query_params.get("locale", lang)
    lang = request.cookies.get("language", lang)

    if lang not in translation_manager.supported_languages:
        lang = "en"

    current_language.set(lang)
    return lang


def __(message: str, **kwargs) -> str:
    return translation_manager.translate(message, **kwargs)


def n__(singular: str, plural: str, n: int, **kwargs) -> str:
    return translation_manager.ntranslate(singular, plural, n, **kwargs)
