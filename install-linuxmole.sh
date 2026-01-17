#!/usr/bin/env bash
set -euo pipefail

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

echo "[4/6] Install Python dependencies (rich)..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install rich

echo "[5/6] Install lm.py..."
# Assumes lm.py is in the current directory
install -m 0755 ./lm.py "$APP_DIR/lm.py"

echo "[6/6] Create wrapper /usr/local/bin/lm..."
cat > "$BIN_LINK" <<'EOF'
#!/usr/bin/env bash
exec /opt/linuxmole/venv/bin/python /opt/linuxmole/lm.py "$@"
EOF
chmod 0755 "$BIN_LINK"

echo "OK. Try: lm status"
