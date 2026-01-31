#!/usr/bin/env bash
# LinuxMole Installation Script
# This script installs LinuxMole in /opt/linuxmole with isolated dependencies
# For a better experience, use pipx instead: https://github.com/4ndymcfly/linux-mole#installation

set -euo pipefail

# Configuration
APP_DIR="/opt/linuxmole"
VENV_DIR="$APP_DIR/venv"
BIN_LINK="/usr/local/bin/lm"
INSTALL_LOG="/tmp/linuxmole-install.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$INSTALL_LOG"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1" | tee -a "$INSTALL_LOG"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$INSTALL_LOG"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$INSTALL_LOG"
    exit 1
}

# Show header
cat <<'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   LinuxMole Installation Script
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This script will install LinuxMole in /opt/linuxmole

📌 RECOMMENDED: Use pipx for better dependency management

    1. Install pipx:
       sudo apt update && sudo apt install -y pipx
       pipx ensurepath

    2. Install LinuxMole:
       pipx install linuxmole

Why pipx is better:
  ✓ Automatic updates (pipx upgrade linuxmole)
  ✓ Easy uninstall (pipx uninstall linuxmole)
  ✓ Better isolation and PATH management

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

echo ""
read -p "Continue with manual installation? [y/N]: " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Installation cancelled. Use pipx for best experience."
    exit 0
fi

# Check root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root. Use: sudo $0"
fi

# Start installation
log "Starting LinuxMole installation..."
log "Installation log: $INSTALL_LOG"
echo ""

# Step 1: Check/Install dependencies
log "[1/7] Checking system dependencies..."
if ! command -v python3 &> /dev/null; then
    log "Installing Python3..."
    apt-get update -qq || error "Failed to update package lists"
    apt-get install -y python3 python3-venv python3-pip &>> "$INSTALL_LOG" || error "Failed to install Python3"
else
    success "Python3 already installed: $(python3 --version)"
fi

# Verify Python version
PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log "Python version: $PY_VERSION"
if [[ $(echo "$PY_VERSION < 3.8" | bc -l) -eq 1 ]]; then
    error "Python 3.8 or higher is required (found $PY_VERSION)"
fi

# Step 2: Remove old installation if exists
if [[ -d "$APP_DIR" ]]; then
    warn "Found existing installation at $APP_DIR"
    read -p "Remove old installation and continue? [y/N]: " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "[2/7] Removing old installation..."
        rm -rf "$APP_DIR" || error "Failed to remove old installation"
        success "Old installation removed"
    else
        error "Installation cancelled"
    fi
else
    log "[2/7] No previous installation found"
fi

# Step 3: Create directories
log "[3/7] Creating installation directory..."
mkdir -p "$APP_DIR" || error "Failed to create directory $APP_DIR"
success "Directory created: $APP_DIR"

# Step 4: Create virtual environment
log "[4/7] Creating virtual environment..."
python3 -m venv "$VENV_DIR" &>> "$INSTALL_LOG" || error "Failed to create virtual environment"
success "Virtual environment created"

# Step 5: Upgrade pip and install LinuxMole
log "[5/7] Installing LinuxMole from PyPI..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip &>> "$INSTALL_LOG" || error "Failed to upgrade pip"
"$VENV_DIR/bin/python" -m pip install linuxmole &>> "$INSTALL_LOG" || error "Failed to install LinuxMole"

# Verify installation
INSTALLED_VERSION=$("$VENV_DIR/bin/python" -c "import linuxmole.constants; print(linuxmole.constants.VERSION)" 2>/dev/null)
if [[ -z "$INSTALLED_VERSION" ]]; then
    error "Installation verification failed"
fi
success "LinuxMole $INSTALLED_VERSION installed successfully"

# Step 6: Create wrapper script
log "[6/7] Creating command wrapper..."
cat > "$BIN_LINK" <<'WRAPPER_EOF'
#!/usr/bin/env bash
# LinuxMole wrapper script
exec /opt/linuxmole/venv/bin/python -m linuxmole "$@"
WRAPPER_EOF
chmod 0755 "$BIN_LINK" || error "Failed to create wrapper script"
success "Command wrapper created: $BIN_LINK"

# Step 7: Verify PATH and installation
log "[7/7] Verifying installation..."

# Check if /usr/local/bin is in PATH
if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
    warn "/usr/local/bin is not in your PATH"
    warn "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "    export PATH=\"/usr/local/bin:\$PATH\""
    echo ""
fi

# Test command
if command -v lm &> /dev/null; then
    LM_VERSION=$(lm --version 2>&1 | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
    success "Command 'lm' is available (version: $LM_VERSION)"
else
    warn "Command 'lm' not found in PATH"
    warn "You may need to restart your shell or run: export PATH=\"/usr/local/bin:\$PATH\""
fi

# Installation complete
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Installation completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Installed version: LinuxMole $INSTALLED_VERSION"
echo "Installation path: $APP_DIR"
echo "Command: lm"
echo ""
echo "Try it now:"
echo "  lm --version"
echo "  lm status"
echo "  lm --help"
echo ""
echo "To uninstall:"
echo "  sudo rm -rf $APP_DIR $BIN_LINK"
echo ""
echo "📌 For easier updates and management, consider using pipx:"
echo "   https://github.com/4ndymcfly/linux-mole#installation"
echo ""
