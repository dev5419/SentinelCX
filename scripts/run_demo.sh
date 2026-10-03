#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT_DIR="$(dirname "$DIR")"

echo "==================================================================="
echo "    STARTING ENTERPRISE MULTI-AGENT DEMO (BACKEND + FRONTEND)"
echo "==================================================================="
echo ""

# Start FastAPI backend
echo "[1/2] Starting FastAPI Backend on http://localhost:8000 ..."
cd "$ROOT_DIR"
./venv/bin/python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload --reload-dir api --reload-dir core --reload-dir agents &
BACKEND_PID=$!

# Wait 3 seconds
sleep 3

# Start React Vite frontend
echo "[2/2] Starting React + Vite Frontend on http://localhost:5173 ..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "==================================================================="
echo "Both services launched!"
echo "- API Backend:  http://localhost:8000"
echo "- Swagger Docs: http://localhost:8000/docs"
echo "- Frontend UI:  http://localhost:5173"
echo "Press Ctrl+C to terminate both servers."
echo "==================================================================="

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
