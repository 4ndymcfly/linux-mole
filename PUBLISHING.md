# Publishing

This document describes the release flow for PyPI + pipx.

## 1) Bump version

Update the version in:
- `pyproject.toml`
- `lm.py` (`VERSION = "X.Y.Z"`)

## 2) Build

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip build twine
python -m build
twine check dist/*
```

## 3) Upload to PyPI

```bash
twine upload dist/*
```

## 4) Tag and push

```bash
git tag vX.Y.Z
git push --tags
```

## 5) GitHub release

Create a release with notes. Example:

```bash
gh release create vX.Y.Z -t "LinuxMole X.Y.Z" -n "Highlights..."
```

## 6) Verify pipx install

```bash
pipx install linuxmole
lm --version
```

## 7) Upgrade users

```bash
pipx upgrade linuxmole
```
