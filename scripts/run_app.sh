#!/usr/bin/env bash
# DocLens Application Launcher
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

source .venv/bin/activate
export PYTHONPATH="$REPO_DIR:$PYTHONPATH"

echo "========================================================"
echo "🚀 Starting DocLens Services"
echo "   - FastAPI Backend: http://localhost:8000 (Docs: /docs)"
echo "   - Streamlit UI:    http://localhost:8501"
echo "========================================================"

# Start FastAPI in background
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

trap "kill $API_PID 2>/dev/null || true" EXIT

# Wait for API to become ready
echo "Waiting for FastAPI to become ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "✓ FastAPI is ready!"
        break
    fi
    sleep 1
done

# Start Streamlit UI
streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
