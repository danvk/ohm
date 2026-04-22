# Claude Code Instructions

## Coding guidelines

- Avoid abbrevs: `const startDate = r.tags['start_date']`, not `const sd = ...`.
  - Exceptions: single-letter variables are fine if they are short-lived. `i` is always fine as an index.
- Don't sweat access control. There's no need for `private` declarations or `_`-prefixed variables. Use `varname`, not `_varname`.
- Factor out helper functions where reasonable. Write at least a one-line documentation comment (`//` in TypeScript, `#` in Python) for internal-only functions, and full jsdoc/docstrings for exported functions.
- Write unit tests for all public functions.

## After every change

### Python files

Run ruff to format and lint after editing any `.py` file:

```
uv run ruff format <file>
uv run ruff check --fix <file>
```

### TypeScript / frontend files

Run prettier after editing any file under `app/`:

```
cd app && npx prettier --write <file>
```
