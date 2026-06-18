#!/usr/bin/env bash
# Convenience script: sets up a virtualenv, installs dependencies,
# generates the synthetic database, and starts the dev server.
#
# Usage: ./setup_and_run.sh

set -e

cd "$(dirname "$0")/backend"

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ ! -f "app/data/kavach.db" ]; then
  echo "Generating synthetic crime database..."
  python app/data/generate_data.py
fi

echo "Starting Kavach backend on http://localhost:8000 ..."
uvicorn app.main:app --reload --port 8000
