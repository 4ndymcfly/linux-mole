# LinuxMole

*Safe maintenance for Linux + Docker, inspired by [Mole for macOS](https://github.com/tw93/mole), a wonderful project.*

[![PyPI version](https://img.shields.io/pypi/v/linuxmole?style=flat-square)](https://pypi.org/project/linuxmole/)
[![Python](https://img.shields.io/pypi/pyversions/linuxmole?style=flat-square)](https://pypi.org/project/linuxmole/)
[![Downloads](https://img.shields.io/pypi/dm/linuxmole?style=flat-square)](https://pypi.org/project/linuxmole/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/4ndymcfly/linux-mole?style=flat-square)](https://github.com/4ndymcfly/linux-mole/stargazers)
[![CI](https://img.shields.io/github/actions/workflow/status/4ndymcfly/linux-mole/ci.yml?branch=main&label=tests&style=flat-square)](https://github.com/4ndymcfly/linux-mole/actions/workflows/ci.yml)

## Overview

LinuxMole is a Mole-inspired CLI for Linux servers with Docker. It focuses on safe, transparent maintenance with previews, structured output, and explicit confirmation.

## Project Status

> **Note:** LinuxMole is under active development. Core functionality is complete and tested, with additional features being implemented.

| Aspect | Status |
|--------|--------|
| **Version** | 1.0.10 |
| **Tests** | 120 passing (100%) |
| **Coverage** | 14.98% |
| **Architecture** | Modular (28 modules) |
| **CI/CD** | ✅ GitHub Actions (Python 3.8-3.12) |
| **Completion** | 9/11 tasks (81.8%) |

### Implemented Features ✅

- ✅ Complete system and Docker status monitoring
- ✅ Safe cleanup operations (system + Docker)
- ✅ Disk usage analyzer with interactive TUI
- ✅ Application uninstaller (apt/snap/flatpak)
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

- Mole-like console UX with structured sections and previews
- Safe-by-default cleanup with explicit confirmation
- Docker-aware maintenance (images, networks, volumes, logs)
- System maintenance (journald, tmpfiles, apt, caches)
- Whitelist support and detailed preview logs

## Screenshots
<table align="center">
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/4ndymcfly/linux-mole/main/screenshots/linux-mole-system-status-002.png" alt="System status" height="300"></td>
    <td width="24"></td>
    <td align="center"><img src="https://raw.githubusercontent.com/4ndymcfly/linux-mole/main/screenshots/linux-mole-kernel-001.png" alt="Kernel" height="300"></td>
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

### 🗂️ Legacy Script (Deprecated)

The `install-linuxmole.sh` script is **deprecated** and no longer maintained. Use **pipx** instead.

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
