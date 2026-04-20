# Claude Code Instructions

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
