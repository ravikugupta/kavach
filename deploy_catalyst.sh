#!/usr/bin/env bash
# =============================================================================
# Kavach — Zoho Catalyst Deployment Script (Placeholder)
# =============================================================================
#
# This script documents the steps to deploy Kavach on Zoho Catalyst.
# Reference: https://catalyst.zoho.com/help/
#
# Architecture on Catalyst:
#   - Backend (FastAPI)  → Catalyst Advanced I/O Function
#   - Frontend (HTML/JS) → Catalyst Static Hosting (Web Client)
#   - Database (SQLite)  → Embedded in the function package (prototype)
#                          In production: replace with Catalyst DataStore or
#                          a managed database (Zoho Catalyst Cloud Scale DB)
#
# Prerequisites:
#   1. Install Catalyst CLI:  npm install -g zoho-catalyst-cli
#   2. Login:                 catalyst login
#   3. Initialize project:    catalyst init  (choose "Advanced I/O Function")
#
# =============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# ── Step 1: Run tests ─────────────────────────────────────────────────────────
echo "▶ Running unit tests..."
cd "$BACKEND_DIR"
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install -q -r requirements.txt
python -m pytest tests/ -v
echo "✓ All tests passed"

# ── Step 2: Generate DB if not present ───────────────────────────────────────
if [ ! -f "$BACKEND_DIR/app/data/kavach.db" ]; then
  echo "▶ Generating synthetic database..."
  python app/data/generate_data.py
fi

# ── Step 3: Package backend as a Catalyst Advanced I/O Function ──────────────
echo "▶ Packaging backend for Catalyst Advanced I/O Function..."
PACKAGE_DIR="$PROJECT_ROOT/.catalyst_package"
rm -rf "$PACKAGE_DIR" && mkdir -p "$PACKAGE_DIR/function"

# Copy backend source
cp -r "$BACKEND_DIR/app"            "$PACKAGE_DIR/function/"
cp    "$BACKEND_DIR/requirements.txt" "$PACKAGE_DIR/function/"

# Catalyst requires a catalyst-config.json at function root
cat > "$PACKAGE_DIR/function/catalyst-config.json" <<EOF
{
  "type": "Advanced IO",
  "name": "kavach-api",
  "stack": "python3.9",
  "entry_point": "app.main:app",
  "memory": 256,
  "timeout": 30
}
EOF

echo "✓ Function package ready at $PACKAGE_DIR/function"

# ── Step 4: Package frontend as a Catalyst Web Client ────────────────────────
echo "▶ Copying frontend for Catalyst Static Hosting..."
cp -r "$FRONTEND_DIR" "$PACKAGE_DIR/frontend"
echo "✓ Frontend package ready at $PACKAGE_DIR/frontend"

# ── Step 5: Deploy via Catalyst CLI ──────────────────────────────────────────
# NOTE: Uncomment the lines below once you have `catalyst init` run and
# have set up your Catalyst project + credentials.
#
# echo "▶ Deploying to Zoho Catalyst..."
# cd "$PACKAGE_DIR"
# catalyst deploy --function kavach-api --client kavach-frontend
# echo "✓ Deployment complete!"
# catalyst describe app  # prints the deployed URL

echo ""
echo "==================================================================="
echo " Deployment package ready."
echo " To deploy:"
echo "   1.  cd $PACKAGE_DIR"
echo "   2.  catalyst init   (if not already done)"
echo "   3.  catalyst deploy"
echo "==================================================================="
