# Release Notes - v1.2.0

## 🎨 Major UX Redesign

### New Features

- **Mode Selection Menu** - Choose execution mode at startup (Normal/Root/Dry-Run)
- **Color-Coded Interface** - Intuitive color system for quick category identification:
  - 🔵 Blue: Monitoring & Analysis
  - 🟢 Green: Cleanup & Maintenance
  - 🟡 Yellow: System Operations
  - 🟠 Orange: Configuration
  - 🔴 Red: LinuxMole System
- **Modern Menu Layout** - Redesigned all submenus with consistent colored dot styling
- **Smart Mode Switching** - Return to mode selection with 'm' option (Normal Mode only)
- **Context-Aware Menus** - Options dynamically shown/hidden based on current mode

### Improvements

- **Better Visual Hierarchy** - Clear separation between categories
- **Privilege Management** - Cannot escalate/downgrade privileges without restart
- **Vertical Alignment** - Fixed menu number alignment for 1-14 options
- **Consistent Styling** - All interactive wizards use unified color scheme
- **Root Detection** - Automatic mode detection when re-executed with sudo

### Bug Fixes

- Fixed indentation errors in interactive menu structure
- Fixed environment variable persistence through sudo re-execution
- Fixed banner priority (Dry-Run Mode > Root Mode > Normal Mode)
- Fixed Update/Self-Uninstall commands in Root Mode (pipx user detection)
- Fixed redundant dry-run confirmation prompts in submenus

### Technical Changes

- Refactored interactive menu with outer loop for mode re-selection
- Improved code organization in `linuxmole/interactive.py`
- Added `--interactive-dry-run` internal flag to avoid CLI conflicts
- Enhanced `maybe_reexec_with_sudo()` to support dry-run mode
- Updated all submenu headers with `print_submenu_header()` function

---

**Full Changelog**: https://github.com/4ndymcfly/linux-mole/compare/v1.1.1...v1.2.0
