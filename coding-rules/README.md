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


