#!/usr/bin/env bash
# DEPRECATED: This script is no longer maintained
# Use pipx instead: https://github.com/4ndymcfly/linux-mole#installation

set -euo pipefail

cat <<'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  WARNING: This installation script is DEPRECATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This script is no longer maintained and may not work correctly
with the current version of LinuxMole.

✅ RECOMMENDED: Use pipx instead

    1. Install pipx:
       sudo apt update && sudo apt install -y pipx
       pipx ensurepath

    2. Install LinuxMole:
       pipx install linuxmole

    3. Run:
       lm status

Why pipx?
  ✓ Isolated environment (no conflicts)
  ✓ Easy updates (pipx upgrade linuxmole)
  ✓ Automatic PATH management
  ✓ Clean uninstall (pipx uninstall linuxmole)

More info: https://github.com/4ndymcfly/linux-mole#installation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

echo ""
read -p "Do you want to continue with this deprecated script anyway? [y/N]: " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled. Please use pipx instead."
    exit 1
fi

echo ""
echo "Continuing with deprecated installation..."
echo ""

APP_DIR="/opt/linuxmole"
VENV_DIR="$APP_DIR/venv"
BIN_LINK="/usr/local/bin/lm"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo $0"
  exit 1
fi

echo "[1/6] Base packages..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip

echo "[2/6] Create directories..."
mkdir -p "$APP_DIR"

echo "[3/6] Create venv..."
python3 -m venv "$VENV_DIR"

echo "[4/6] Install LinuxMole from PyPI..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install linuxmole

echo "[5/6] Create wrapper /usr/local/bin/lm..."
cat > "$BIN_LINK" <<'EOF'
#!/usr/bin/env bash
exec /opt/linuxmole/venv/bin/python -m linuxmole "$@"
EOF
chmod 0755 "$BIN_LINK"

echo ""
echo "✓ Installation complete"
echo ""
echo "Try: lm status"
echo ""
echo "⚠️  IMPORTANT: This is a deprecated installation method."
echo "    Consider migrating to pipx for better dependency management."
