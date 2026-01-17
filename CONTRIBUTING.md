# Contributing

Thanks for helping improve LinuxMole. Please keep changes focused and well-documented.

## Development setup

```bash
git clone git@github.com:4ndymcfly/linux-mole.git
cd linux-mole
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Running locally

```bash
lm --help
lm status
lm clean --dry-run
```

## Code style

- Keep output readable and aligned.
- All user-facing text should be in English.
- Prefer safe defaults and `--dry-run` previews.
- Avoid destructive actions without explicit confirmation.

## Reporting issues

Use the GitHub issue templates and include:
- Linux distro and version
- Shell and terminal
- Command used and full output
- Whether you used `sudo`

## Security

Please avoid sharing sensitive system details (tokens, private paths, hostnames).
