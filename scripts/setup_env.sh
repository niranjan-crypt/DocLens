#!/usr/bin/env bash
# DocLens Environment Setup Script
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "=== Setting up DocLens Environment ==="

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment at .venv..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel

echo "Installing project dependencies from requirements.txt..."
pip install -r requirements.txt

export PYTHONPATH="$REPO_DIR:$PYTHONPATH"

echo "=== DocLens environment is ready! ==="
