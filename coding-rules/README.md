# Coding Rules

## Best practices & code style (Python)

- **Follow PEP 8 guidelines**
  - Keep code formatted and readable.
  - Prefer automated formatting/linting in CI and pre-commit.

- **Use type hints for all functions**
  - Add type annotations for parameters and return values.
  - Avoid `Any` unless there is a strong reason.

- **Write docstrings for public APIs**
  - Public modules, classes, methods, and functions must have docstrings.
  - Docstrings must describe behavior, inputs, outputs, and raised errors when relevant.

- **Keep functions focused and small**
  - Single responsibility per function.
  - Prefer early returns and shallow nesting.

- **Use meaningful variable names**
  - Prefer descriptive full words over abbreviations.
  - Name variables by what they represent, not how they’re used.

- **Add tests for new features**
  - New features must include tests covering success and failure paths.
  - Bug fixes must include regression tests.

## Commit convention (Conventional Commits)

Use **Conventional Commits 1.0.0**: `https://www.conventionalcommits.org/en/v1.0.0/`.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Common types

- **feat**: new feature
- **fix**: bug fix
- **docs**: documentation only
- **refactor**: code change that neither fixes a bug nor adds a feature
- **test**: adding/updating tests
- **chore**: maintenance tasks (tooling, deps, non-product code changes)

### Breaking changes

Indicate breaking changes with:

- `!` after type/scope (e.g. `feat(api)!: ...`), or
- Footer `BREAKING CHANGE: ...`

## FastAPI conventions (reference)

Primary reference: `https://github.com/zhanymkanov/fastapi-best-practices`.

- **Project structure**
  - Prefer a domain/module-based structure (group by business area), not by file type.

- **Async**
  - Use `async` endpoints for I/O-bound work.
  - Do not block the event loop with CPU-heavy work; offload when needed.

- **Pydantic**
  - Use Pydantic models extensively for request/response validation.
  - Separate schemas (Pydantic) from DB models; keep them in `schemas.py` per module.

- **Dependencies**
  - Decouple, reuse, and chain dependencies where it improves clarity.
  - Prefer async dependencies when they do I/O.

- **Docs**
  - Document routes with `response_model`, `status_code`, `description`, `responses`, etc.
  - Hide OpenAPI docs by default unless explicitly enabled per environment.

- **Database & migrations**
  - Use consistent DB naming conventions (snake_case, consistent suffixes like `_at`).
  - Keep Alembic migrations static and reversible; use descriptive names.

- **Testing**
  - Add tests for every new feature and bug fix.
  - Prefer async test clients from day 0 when you have async routes/DB.

- **Linting/formatting**
  - Keep formatting and linting automated; prefer fast, consistent tooling (e.g. ruff).

## Internationalization (i18n)

### System Overview

JSON-based translation system with per-language directories. Supports nested keys, flat keys, placeholders, and pluralization.

**Structure:**
```
src/locales/
├── en/
│   ├── validation.json
│   ├── messages.json
└── ja/
    └── validation.json
```

### Basic Usage

**Import the translation function:**
```python
from src.core import _
```

**Use translation keys with parameters:**
```python
# Nested keys (preferred)
_("validation.required", attribute="Email")  # → "Email is required."
_("validation.min.string", attribute="Password", min=8)  # → "Password must be at least 8 characters."
_("messages.greeting", name="John")  # → "Hello, John!"

# Flat keys (also supported)
_("Welcome")  # → "Welcome!"
_("Hello, {name}!", name="John")  # → "Hello, John!"
```

**In Pydantic models:**
```python
from pydantic import BaseModel, validator
from src.core import _

class UserCreate(BaseModel):
    username: str
    email: str
    age: int
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError(_("validation.min.string", attribute="username", min=3))
        if not v.isalnum():
            raise ValueError(_("validation.alpha_num", attribute="username"))
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError(_("validation.email", attribute="email"))
        return v
    
    @validator('age')
    def validate_age(cls, v):
        if not (18 <= v <= 100):
            raise ValueError(_("validation.between.numeric", attribute="age", min=18, max=100))
        return v
```

**In FastAPI routes:**
```python
from fastapi import APIRouter, Depends, HTTPException
from src.core import get_language_from_request, _

router = APIRouter()

@router.post("/users")
async def create_user(
    user: UserCreate,
    lang: str = Depends(get_language_from_request)
):
    # Check uniqueness
    if await user_exists(user.username):
        raise HTTPException(
            status_code=400,
            detail=_("validation.unique", attribute="username")
        )
    
    # Create user
    created_user = await create_user_service(user)
    return {
        "message": _("messages.success"),
        "data": created_user
    }
```

### Adding New Languages

**1. Create language directory:**
```bash
mkdir -p src/locales/ja
```

**2. Create JSON files (copy from `en` as template):**
```bash
cp src/locales/en/validation.json src/locales/ja/validation.json
cp src/locales/en/messages.json src/locales/ja/messages.json
```

**3. Translate the content:**
```json
// src/locales/ja/validation.json
{
  "validation": {
    "required": "{attribute}は必須です。",
    "min": {
      "string": "{attribute}は{min}文字以上である必要があります。",
      "numeric": "{attribute}は{min}以上である必要があります。"
    },
    "email": "{attribute}は有効なメールアドレスである必要があります。"
  }
}
```

**4. Restart the app** — translations load automatically!

### Translation Patterns

**Nested structure (recommended for complex namespaces):**
```json
{
  "validation": {
    "required": "{attribute} is required.",
    "min": {
      "string": "{attribute} must be at least {min} characters.",
      "numeric": "{attribute} must be at least {min}.",
      "file": "{attribute} must be at least {min} kilobytes."
    }
  }
}
```

**Flat structure (for simple messages):**
```json
{
  "messages": {
    "Welcome": "ようこそ",
    "Goodbye": "さようなら",
    "Hello, {name}!": "こんにちは、{name}さん！"
  }
}
```

**Pluralization:**
```json
{
  "messages": {
    "items_count": {
      "one": "{count} item",
      "other": "{count} items"
    }
  }
}
```
Usage: `from src.core import n_; n_("messages.items_count", "items", 5, count=5)`

### Testing

```bash
# Via Accept-Language header
curl -H "Accept-Language: en" http://localhost:8000/api/users
curl -H "Accept-Language: ja" http://localhost:8000/api/users

# Via query parameter
curl "http://localhost:8000/api/users?lang=ja"
curl "http://localhost:8000/api/users?locale=en"

# Via cookie
curl -b "language=ja" http://localhost:8000/api/users
```

### Quick Reference

**✅ Do:**
- Use `_("namespace.key", param=value)` for all user-facing messages
- Group by namespace: `validation.*`, `messages.*`
- Use descriptive placeholders: `{attribute}`, `{min}`, `{max}`, `{name}`, `{value}`
- Keep one concern per JSON file (validation rules, UI messages, etc.)
- Provide fallback to English for missing translations
- Test all languages during feature development

**❌ Don't:**
- Hardcode strings: ~~`"Username is required"`~~
- Concatenate translations: ~~`_("Hello") + " " + _("World")`~~
- Use f-strings with translation keys: ~~`_(f"User {name} not found")`~~
- Mix multiple languages in one file
- Use abbreviations in placeholder names: ~~`{usr}`, `{attr}`~~
- Forget to handle pluralization for count-based messages