# LinuxMole

*Safe maintenance for Linux + Docker, inspired by Mole.*

## Overview

- Mole-like console UX with structured sections and previews
- Safe-by-default cleanup with explicit confirmation
- Docker-aware maintenance (images, networks, volumes, logs)
- System maintenance (journald, tmpfiles, apt, caches)
- Whitelist support and detailed preview logs

## Installation

### Recommended (pipx)

1) Install pipx:
```bash
sudo apt update && sudo apt install -y pipx
pipx ensurepath
```

2) Install LinuxMole:
```bash
pipx install "git+https://github.com/4ndymcfly/linux-mole.git"
```

3) Run:
```bash
lm status
```

### Legacy (optional)

```bash
sudo ./install-linuxmole.sh
```

## Quick Start

```bash
lm status
lm status system
lm status docker
lm clean --dry-run
lm clean system --dry-run
lm clean docker --dry-run
```

## Commands

- `lm status` Full status (system + docker)
- `lm status system` System status only
- `lm status docker` Docker status only
- `lm clean` Full cleanup (system + docker)
- `lm clean system` System cleanup only
- `lm clean docker` Docker cleanup only
- `lm analyze` Analyze disk usage
- `lm purge` Clean project build artifacts
- `lm installer` Find and remove installer files
- `lm whitelist` Show whitelist config
- `lm uninstall` Remove LinuxMole from this system
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
lm purge
lm installer
```

## Whitelist / Config

- Whitelist file: `~/.config/linuxmole/whitelist.txt`
- Purge paths file: `~/.config/linuxmole/purge_paths`
- Edit whitelist: `lm whitelist --edit`

## Screenshots

Add screenshots to a `./screenshots` folder and reference them here, for example:

![Status](screenshots/status.png)
![Clean](screenshots/clean.png)

## Release

1) Update version in `pyproject.toml` and `lm.py`
2) Tag and push: `git tag vX.Y.Z && git push --tags`
3) Users upgrade: `pipx upgrade linuxmole`
