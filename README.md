# LinuxMole

*Safe maintenance for Linux + Docker, inspired by [Mole for macOS](https://github.com/tw93/mole), a wonderful project.*

[![PyPI version](https://img.shields.io/pypi/v/linuxmole?style=flat-square&cacheSeconds=300)](https://pypi.org/project/linuxmole/)
[![Python](https://img.shields.io/pypi/pyversions/linuxmole?style=flat-square&cacheSeconds=300)](https://pypi.org/project/linuxmole/)
[![Downloads](https://img.shields.io/pypi/dm/linuxmole?style=flat-square&cacheSeconds=300)](https://pypi.org/project/linuxmole/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/4ndymcfly/linux-mole?style=flat-square&cacheSeconds=300)](https://github.com/4ndymcfly/linux-mole/stargazers)
[![CI](https://img.shields.io/github/actions/workflow/status/4ndymcfly/linux-mole/ci.yml?branch=main&label=tests&style=flat-square&cacheSeconds=300)](https://github.com/4ndymcfly/linux-mole/actions/workflows/ci.yml)

## Overview

LinuxMole is a Mole-inspired CLI for Linux servers with Docker. It focuses on safe, transparent maintenance with previews, structured output, and explicit confirmation.

## Project Status

> **Note:** LinuxMole is under active development. Core functionality is complete and tested, with additional features being implemented.

| Aspect | Status |
|--------|--------|
| **Version** | 1.3.0 |
| **Tests** | 142 passing (100%) |
| **Coverage** | 19.82% |
| **Architecture** | Modular (28 modules) |
| **CI/CD** | ✅ GitHub Actions (Python 3.8-3.12) |
| **Completion** | 10/11 tasks (90.9%) |

### Implemented Features ✅

- ✅ **Interactive menu with all 14 commands** (redesigned in v1.2.0)
- ✅ **ncdu-style Disk Analyzer TUI** (new in v1.3.0) - flat list navigation with Enter/Backspace
- ✅ Complete system and Docker status monitoring
- ✅ Safe cleanup operations (system + Docker)
- ✅ Application uninstaller (apt/snap/flatpak)
- ✅ System optimization (databases, network, services)
- ✅ Whitelist management and config file support
- ✅ Automated testing and CI/CD pipeline
- ✅ Python 3.8-3.12 compatibility
- ✅ Logging and error handling
- ✅ Modular architecture

### In Progress 🚧

- TUI launcher integration (low priority)

### Coming Soon 🔜

- Comprehensive documentation (commands, configuration, examples)
- Additional test coverage
- Performance optimizations

## Features

### 🎯 Interactive Menu (Redesigned in v1.2.0)

Run `lm` without arguments to access a **modernized interactive menu** with all 14 commands organized in 5 color-coded categories:

#### Execution Modes

Choose your preferred execution mode at startup:

- **🟢 Normal Mode** - Execute without root permissions (limited features)
- **🔴 Root Mode** - Execute with full system access (all features)
- **🟡 Dry-Run Mode** - Preview commands without executing (safe testing)

#### Color-Coded Categories

Menu items use intuitive color coding for quick identification:

- **🔵 Blue** - Monitoring & Analysis (status checks, disk usage)
- **🟢 Green** - Cleanup & Maintenance (safe operations)
- **🟡 Yellow** - System Operations (requires caution)
- **🟠 Orange** - Configuration (settings management)
- **🔴 Red** - LinuxMole System (updates, self-uninstall)

**Benefits:**
- ✅ No need to memorize CLI commands
- ✅ Clear visual hierarchy with color coding
- ✅ Mode selection prevents accidental privilege escalation
- ✅ Interactive wizards with smart defaults
- ✅ Return to mode selection with 'm' (Normal Mode only)

### Core Features

- Mole-like console UX with structured sections and previews
- Safe-by-default cleanup with explicit confirmation
- Docker-aware maintenance (images, networks, volumes, logs)
- System maintenance (journald, tmpfiles, apt, caches)
- Whitelist support and detailed preview logs

### 📊 Disk Analyzer TUI (New in v1.3.0)

The `lm analyze --tui` command now features a complete **ncdu-style redesign** for better disk usage analysis:

**Key Features:**
- **Flat List Navigation** - View and navigate one directory level at a time (like ncdu)
- **Intuitive Controls** - `Enter` to dive into directories, `Backspace` to go back
- **Smart Sorting** - Items automatically sorted by size (largest first)
- **Visual Bars** - Proportional usage bars relative to the largest item in current view
- **Better Performance** - Loads only current directory (not entire tree)
- **Improved Diagnostics** - Clear error messages if Textual library is missing

**Keybindings:**
- `↑/↓` - Navigate items
- `Enter/→` - Enter directory
- `Backspace/←/Esc` - Go to parent
- `R` - Refresh view
- `Q` - Quit

**Usage:**
```bash
lm analyze --tui           # Interactive TUI in current directory
lm analyze /var --tui      # Interactive TUI for specific path
```

## Screenshots

### Mode Selection
<p align="center">
  <img src="https://raw.githubusercontent.com/4ndymcfly/linux-mole/main/screenshots/main-menu.png" alt="Mode selection" width="600">
</p>

### Interactive Menus
<table align="center">
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/4ndymcfly/linux-mole/main/screenshots/normal-mode-main-menu.png" alt="Normal Mode" height="280">
      <br><b>Normal Mode</b>
    </td>
    <td width="20"></td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/4ndymcfly/linux-mole/main/screenshots/root-mode-main-menu.png" alt="Root Mode" height="280">
      <br><b>Root Mode</b>
    </td>
    <td width="20"></td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/4ndymcfly/linux-mole/main/screenshots/dry-run-main-menu.png" alt="Dry-Run Mode" height="280">
      <br><b>Dry-Run Mode</b>
    </td>
  </tr>
</table>

### Status & Monitoring
<table align="center">
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/4ndymcfly/linux-mole/main/screenshots/system-status-root-mode.png" alt="System Status" height="300">
      <br><b>System Status</b>
    </td>
    <td width="24"></td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/4ndymcfly/linux-mole/main/screenshots/status-docker-only.png" alt="Docker Status" height="300">
      <br><b>Docker Status</b>
    </td>
  </tr>
</table>

## Help Output

```text
 _      _                     __  __       _
| |    (_)                   |  \/  |     | |
| |     _ _ __  _   ___  __  | \  / | ___ | | ___
| |    | | '_ \| | | \ \/ /  | |\/| |/ _ \| |/ _ \
| |____| | | | | |_| |>  <   | |  | | (_) | |  __/
|______|_|_| |_|\__,_/_/\_\  |_|  |_|\___/|_|\___|

https://github.com/4ndymcfly/linux-mole

Safe maintenance for Linux + Docker.


COMMANDS
lm                      Main menu
lm status               Full status (system + docker)
lm status system        System status only
lm status docker        Docker status only
lm clean                Full cleanup (system + docker)
lm clean system         System cleanup only
lm clean docker         Docker cleanup only
lm uninstall            Uninstall apps (APT/Snap/Flatpak)
lm optimize             Optimize system (DBs, network, services)
lm analyze              Analyze disk usage
lm purge                Clean project build artifacts
lm installer            Find and remove installer files
lm whitelist            Manage whitelist (add/remove/test/edit)
lm config               Manage configuration
lm self-uninstall       Remove LinuxMole from this system
lm --version            Show version
lm update               Update LinuxMole (pipx)


OPTIONS
--dry-run               Preview only (clean, uninstall, optimize)
--yes                   Assume 'yes' for confirmations (clean, uninstall, optimize)
-v, --verbose           Enable verbose logging
--log-file PATH         Write logs to file
-h, --help              Show help


EXAMPLES
  lm status
  lm status --paths
  lm status docker --top-logs 50
  lm clean --containers --networks --images dangling --dry-run
  lm clean docker --images unused --yes
  lm clean docker --truncate-logs-mb 500 --dry-run
  lm clean system --journal --tmpfiles --apt --dry-run
  lm clean system --logs --logs-days 14 --dry-run
  lm clean system --kernels --kernels-keep 2 --dry-run
  lm uninstall firefox --purge --dry-run
  lm uninstall --list-orphans
  lm optimize --all --dry-run
  lm optimize --database --network
  lm analyze --path /var --top 15
  lm analyze --tui
  lm purge
  lm installer
  lm whitelist --add "/home/*/projects/*"
  lm whitelist --edit
  lm config --edit
  lm --version
  lm update
```

## Installation

### ✅ Recommended: pipx (Isolated Installation)

**pipx** is the recommended way to install LinuxMole. It provides:
- ✅ **Isolated environment** - No dependency conflicts
- ✅ **Clean installation** - Doesn't pollute system Python
- ✅ **Easy updates** - `pipx upgrade linuxmole`
- ✅ **Automatic PATH** - Command available globally

**Install pipx:**
```bash
sudo apt update && sudo apt install -y pipx
pipx ensurepath
```

**Install LinuxMole:**
```bash
pipx install linuxmole
```

**Run:**
```bash
lm status
```

**Development version (latest from main):**
```bash
pipx install "git+https://github.com/4ndymcfly/linux-mole.git"
```

---

### ⚠️ Alternative: pip (Not Recommended)

Using `pip` directly can cause dependency conflicts with system packages:

```bash
# NOT recommended - can conflict with system packages
pip install --user linuxmole

# If you must use pip, at least use a virtual environment
python3 -m venv ~/linuxmole-env
source ~/linuxmole-env/bin/activate
pip install linuxmole
```

**Why pipx is better:**
- pip installs in user/system Python → conflicts possible
- pipx creates isolated environments → no conflicts
- pipx manages PATH automatically → easier to use

---

### 🗂️ Alternative: Manual Installation Script

The `install-linuxmole.sh` script provides a **manual installation option** for systems without pipx. However, **pipx is still strongly recommended** for better dependency management and easier updates.

**When to use the script:**
- Systems where pipx is not available or cannot be installed
- Offline installations or restricted environments
- Manual control over installation location

**Note:** The script installs to `/opt/linuxmole` and requires root access. Updates must be done manually by re-running the script.

## Commands

- `lm status` Full status (system + docker)
- `lm status system` System status only
- `lm status docker` Docker status only
- `lm clean` Full cleanup (system + docker)
- `lm clean system` System cleanup only
- `lm clean docker` Docker cleanup only
- `lm uninstall` Uninstall apps (APT/Snap/Flatpak)
- `lm optimize` Optimize system (DBs, network, services)
- `lm analyze` Analyze disk usage
- `lm purge` Clean project build artifacts
- `lm installer` Find and remove installer files
- `lm whitelist` Manage whitelist (add/remove/test/edit)
- `lm config` Manage configuration
- `lm self-uninstall` Remove LinuxMole from this system
- `lm --version` Show version
- `lm update` Update LinuxMole (pipx)

## Clean Examples

```bash
lm clean --containers --networks --images dangling --dry-run
lm clean system --journal --tmpfiles --apt --dry-run
lm clean system --logs --logs-days 14 --dry-run
lm clean system --pip-cache --npm-cache --cargo-cache --go-cache --dry-run
lm clean system --snap --flatpak --logrotate --dry-run
lm clean system --kernels --kernels-keep 2 --dry-run
```

## Analyze / Purge / Installer

```bash
lm analyze --path /var --top 15
lm analyze --tui
lm purge
lm installer
```

## Uninstall / Optimize / Config

```bash
# Uninstall apps with all configs
lm uninstall firefox --purge --dry-run
lm uninstall docker-compose --yes
lm uninstall --list-orphans
lm uninstall --autoremove

# Optimize system
lm optimize --all --dry-run
lm optimize --database --network
lm optimize --services

# Manage configuration
lm config --edit
lm config --reset
```

## Whitelist / Config

- Whitelist file: `~/.config/linuxmole/whitelist.txt`
- Purge paths file: `~/.config/linuxmole/purge_paths`
- Edit whitelist: `lm whitelist --edit`

## Contributing

See `CONTRIBUTING.md` for guidelines.

## Release

See `PUBLISHING.md` for the PyPI/pipx release workflow.

1) Update version in `pyproject.toml` and `lm.py`
2) Tag and push: `git tag vX.Y.Z && git push --tags`
3) Users upgrade: `pipx upgrade linuxmole`

## Acknowledgements

Thanks to the original Mole project for inspiration: https://github.com/tw93/mole
