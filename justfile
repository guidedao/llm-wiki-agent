set shell := ["zsh", "-cu"]

setup:
  uv sync --frozen --extra dev

demo:
  uv run kb-agent --query-fixture fixtures/queries/m0_query.json --vault-root vault

test:
  uv run --with pytest python -m pytest
