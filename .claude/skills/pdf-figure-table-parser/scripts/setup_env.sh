#!/usr/bin/env bash
# Create (or reuse) a venv with the dependencies this skill's scripts need.
# All three packages are pure-Python/C-extension wheels from PyPI -- no
# model weights to download, so this works even when huggingface.co is
# blocked by an environment's egress policy (that's the whole reason this
# skill exists instead of just using docling).
#
# Usage:
#   bash setup_env.sh [venv_dir]
# Then:
#   source <venv_dir>/bin/activate

set -euo pipefail
VENV_DIR="${1:-.venv-pdf-parser}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "Ready. Activate with: source $VENV_DIR/bin/activate"
echo "Scripts live in: $SCRIPT_DIR"
