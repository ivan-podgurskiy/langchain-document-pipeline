#!/usr/bin/env bash
# Create a reproducible dev venv (Python 3.11 recommended; matches CI and requirements.lock).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v python3.11 >/dev/null 2>&1; then
  PYTHON=python3.11
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
  ver="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$ver" != "3.11" ]]; then
    echo "Warning: Python $ver detected. CI uses 3.11; install python3.11 for a matching environment." >&2
  fi
else
  echo "Error: python3.11 or python3 not found." >&2
  exit 1
fi

echo "Using $($PYTHON --version) at $(command -v "$PYTHON")"
rm -rf .venv
"$PYTHON" -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -e ".[dev]"

echo ""
echo "Done. Activate with: source .venv/bin/activate"
echo "Run checks:  ruff check src/ scripts/ tests/ && mypy src/"
