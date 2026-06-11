#!/usr/bin/env bash
# Launch the v2 backend under gunicorn for production.
# Expects:
#   - venv activated OR full path to gunicorn passed in via $GUNICORN_BIN
#   - .env present in this repo's root (auto-loaded by app.py via load_dotenv)
#   - PYTHONPATH must include the parent of hca_backend so `import hca_backend.app` resolves
set -euo pipefail

# Resolve repo root and its parent.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT_DIR="$(dirname "$REPO_DIR")"
export PYTHONPATH="$PARENT_DIR:$REPO_DIR${PYTHONPATH:+:$PYTHONPATH}"

cd "$PARENT_DIR"

# One worker — the in-process APScheduler that runs the daily backup
# would otherwise duplicate jobs across workers. Single-client load is tiny.
exec "${GUNICORN_BIN:-gunicorn}" \
  --workers 1 \
  --bind 127.0.0.1:5050 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  hca_backend.app:app
