#!/bin/sh
# Resolve a Python interpreter that has the project's dev dependencies.
#
# Prefers the project virtualenv (the common case after `make install`), then
# an already-activated environment, then PATH. Fails loudly rather than
# skipping: a git hook that silently passes is worse than no hook.
set -e

# Resolve against the repository root, so this works from any directory.
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")

if [ -x "$ROOT/backend/.venv/bin/python" ]; then
  PYTHON="$ROOT/backend/.venv/bin/python"
elif [ -x "$ROOT/backend/.venv/Scripts/python.exe" ]; then
  PYTHON="$ROOT/backend/.venv/Scripts/python.exe"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PYTHON="$VIRTUAL_ENV/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/Scripts/python.exe" ]; then
  PYTHON="$VIRTUAL_ENV/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  echo "No Python interpreter found." >&2
  echo "Set one up with:  cd backend && python -m venv .venv && pip install -e \".[dev]\"" >&2
  exit 1
fi

if ! "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
  echo "The resolved interpreter ($PYTHON) has no dev dependencies." >&2
  echo "Install them with:  cd backend && pip install -e \".[dev]\"" >&2
  exit 1
fi

exec "$PYTHON" "$@"
