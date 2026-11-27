#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install it from https://brew.sh, then rerun this script."
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  brew install ffmpeg
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Install Ollama from https://ollama.com/download/mac, then rerun this script."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
  echo "Python 3.10 or newer is required."
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
".venv/bin/python" -m pip install --upgrade pip
".venv/bin/pip" install -r requirements.txt
if ! ".venv/bin/python" -c 'import faster_whisper, ctranslate2'; then
  echo "faster-whisper/CTranslate2 could not load in this Python environment."
  echo "Try installing Python 3.12 and rerunning: PYTHON_BIN=python3.12 ./setup-macos.sh"
  exit 1
fi

if ! ollama list | grep -q 'qwen2.5:3b'; then
  echo "Pulling the default local model (this download can be several GB)..."
  ollama pull qwen2.5:3b
fi

echo
echo "Setup complete. Start Ollama, then run:"
echo "  .venv/bin/streamlit run app.py --server.address 127.0.0.1"
