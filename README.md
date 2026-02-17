# OHM Exploration

Scripts for exploring OpenHistoryMap.

## Development

- Create & sync the environment: `uv lock && uv sync`
- Run the app: `uv run main.py`
- Find elements by name: `uv run find_by_name.py <file.osm.pbf> <name>`
- Run ruff checks: `uv run ruff check .`
- Format/fix with ruff: `uv run ruff format .`

The workspace is configured to use `ruff` as the Python formatter/linter in VS Code (format on save).
