#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "[TTS] Kiem tra Python..."
python3 --version

if [ ! -d ".venv" ]; then
  echo "[TTS] Tao virtual environment..."
  python3 -m venv .venv
fi

echo "[TTS] Kich hoat venv..."
source .venv/bin/activate

echo "[TTS] Cai dat dependencies..."
pip install -r backend/requirements.txt --quiet

echo ""
echo "[TTS] Khoi dong server tai http://localhost:8000"
echo "[TTS] Nhan Ctrl+C de dung."
echo ""

python backend/app.py
