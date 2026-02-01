# Release Notes - v1.3.1

## 🐛 Bug Fixes - TUI Terminal Compatibility

### Fixed Issues

- **Fixed TUI not opening in Kitty terminal**
  - Corrected incorrect Binding syntax for up/down arrow keys
  - Changed from tuple format to proper `Binding()` objects
  - Resolves black screen issue in certain terminals

- **Fixed Enter key not working in Termius and other terminals**
  - Added `on_data_table_row_selected()` event handler as fallback
  - Provides alternative method for directory navigation
  - Ensures Enter key works across different terminal implementations

- **Improved navigation controls**
  - Added right arrow (`→`) as alternative to Enter for entering directories
  - Added left arrow (`←`) as alternative to Backspace for going to parent
  - More intuitive and flexible navigation options

- **Better path extraction from table rows**
  - Improved markup cleanup logic
  - Fixed issue with paths containing special characters
  - Better fallback mechanism when row metadata is unavailable
  - Correctly handles parent directory navigation

- **Terminal detection and logging**
  - Added terminal environment detection (`$TERM`, `$TERM_PROGRAM`)
  - Improved debugging output for troubleshooting terminal issues
  - Helps identify terminal compatibility problems

### Technical Changes

- Fixed `Binding()` objects in `BINDINGS` list (previously used tuples)
- Enhanced `action_enter_directory()` with better error handling
- Improved markup stripping in path name extraction
- Added comprehensive terminal compatibility test script

### New Navigation Keys

| Action | Keys (all work) |
|--------|-----------------|
| Enter directory | `Enter`, `→` (right arrow) |
| Parent directory | `Backspace`, `←` (left arrow), `Esc` |
| Move cursor | `↑`, `↓` |
| Refresh | `R` |
| Delete | `D` (placeholder) |
| Quit | `Q` |

### Testing

- Verified on Kitty terminal ✅
- Verified on Termius terminal ✅
- Added `test_tui_terminal.py` script for compatibility testing

---

**Previous Release**: [v1.3.0 - ncdu-style TUI Disk Analyzer](https://github.com/4ndymcfly/linux-mole/releases/tag/v1.3.0)

**Full Changelog**: https://github.com/4ndymcfly/linux-mole/compare/v1.3.0...v1.3.1
