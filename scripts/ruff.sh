#!/bin/sh
# Run Ruff over the files lint-staged hands us.
#
# Ruff is a Python tool, so it is not installed by `pnpm install`. This script
# resolves it from the project virtualenv first (the common case after
# `make install`), then from PATH. If neither works it fails loudly: a
# pre-commit hook that silently skips is worse than no hook at all.
set -e

if [ -x "backend/.venv/bin/ruff" ]; then
  RUFF="backend/.venv/bin/ruff"
elif [ -x "backend/.venv/Scripts/ruff.exe" ]; then
  RUFF="backend/.venv/Scripts/ruff.exe"
elif command -v ruff >/dev/null 2>&1; then
  RUFF="ruff"
else
  echo "ruff not found." >&2
  echo "Install it with:  cd backend && pip install -e \".[dev]\"" >&2
  echo "           or:    pip install ruff" >&2
  exit 1
fi

# --force-exclude makes Ruff honour pyproject's exclude list even though the
# files are passed explicitly, so generated migrations are not reformatted.
"$RUFF" check --fix --force-exclude "$@"
"$RUFF" format --force-exclude "$@"
