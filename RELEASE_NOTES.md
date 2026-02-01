# Release Notes - v1.3.0

## 🖥️ TUI Disk Analyzer - ncdu-style Redesign

### New Features

- **ncdu-style Interface** - Complete redesign of the Disk Analyzer TUI (`lm analyze --tui`)
  - Flat list navigation instead of hierarchical tree
  - Enter/Backspace navigation similar to ncdu
  - Current directory focus with parent navigation (..)
  - Sorted by size (descending) for quick identification
  - Proportional bars relative to largest item in current level

- **New Architecture**
  - `DiskUsageHeader` widget - Display current path and statistics
  - `NcduApp` - Main application with DataTable (replaces DirectoryTree)
  - Navigation history stack - Smart back navigation

- **Improved Error Diagnostics**
  - `TEXTUAL_ERROR` variable captures specific import errors
  - Clear error messages when Textual library is unavailable
  - Automatic offer to install/upgrade textual if missing
  - Clean fallback to table view if TUI fails

### Improvements

- **Better Performance** - Loads only current directory level (not entire tree)
- **Intuitive Navigation** - Arrow keys + Enter/Backspace for directory traversal
- **Better Visualization** - Bars scaled to max item in each level for better contrast
- **Color Coding**:
  - Cyan: Directories
  - Yellow: Size values
  - Green: Usage bars
  - Dim: Parent directory marker

### Keybindings

| Key | Action |
|-----|--------|
| `↑/↓` | Move cursor |
| `Enter/→` | Enter directory |
| `Backspace/←/Esc` | Go to parent |
| `R` | Refresh current view |
| `D` | Delete item (placeholder) |
| `Q` | Quit TUI |

### Technical Changes

- Added `TEXTUAL_ERROR` to `linuxmole/constants.py` for better diagnostics
- Imported `DataTable` widget in constants
- Complete rewrite of `linuxmole/commands/analyze.py` with ncdu-style implementation
- New `DiskUsageHeader` reactive widget for path/stats display
- Navigation history using stack pattern
- Optimized directory scanning with `os.scandir()`

### Bug Fixes

- Fixed silent Textual import failures causing black screen
- Improved error handling in TUI initialization
- Better permission error handling during directory scanning

---

**Previous Release**: [v1.2.0 - Major UX Redesign](https://github.com/4ndymcfly/linux-mole/releases/tag/v1.2.0)

**Full Changelog**: https://github.com/4ndymcfly/linux-mole/compare/v1.2.0...v1.3.0
