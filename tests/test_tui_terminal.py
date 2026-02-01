#!/usr/bin/env python3
"""
Test script to diagnose TUI terminal compatibility issues.
Run this to check if your terminal supports the TUI properly.
"""

import os
import sys

print("=== LinuxMole TUI Terminal Compatibility Test ===\n")

# 1. Check Python version
print(f"1. Python version: {sys.version}")
if sys.version_info < (3, 8):
    print("   ⚠️  WARNING: Python 3.8+ required")
else:
    print("   ✅ Python version OK")

# 2. Check Textual installation
print("\n2. Textual library:")
try:
    import textual
    print(f"   ✅ Textual installed: {textual.__version__}")
except ImportError as e:
    print(f"   ❌ Textual NOT installed: {e}")
    print("   Run: pip install textual>=0.47.0")
    sys.exit(1)

# 3. Check terminal info
print("\n3. Terminal information:")
term = os.environ.get('TERM', 'NOT SET')
term_program = os.environ.get('TERM_PROGRAM', 'NOT SET')
colorterm = os.environ.get('COLORTERM', 'NOT SET')
print(f"   TERM: {term}")
print(f"   TERM_PROGRAM: {term_program}")
print(f"   COLORTERM: {colorterm}")

# 4. Check if terminal supports required features
print("\n4. Terminal capabilities:")
if term == 'NOT SET':
    print("   ⚠️  TERM not set - terminal may not work correctly")
elif 'xterm' in term or 'screen' in term or 'tmux' in term:
    print(f"   ✅ Terminal type '{term}' should work")
else:
    print(f"   ⚠️  Terminal type '{term}' - compatibility unknown")

# 5. Simple TUI test
print("\n5. Running simple TUI test...")
try:
    from textual.app import App
    from textual.widgets import Label

    class TestApp(App):
        def compose(self):
            yield Label("If you see this, your terminal supports Textual!")
            yield Label("Press Q to quit")

        def on_mount(self):
            self.set_timer(2, self.exit)

    app = TestApp()
    print("   Starting test app (will auto-close in 2 seconds)...")
    app.run()
    print("   ✅ TUI test successful!")

except Exception as e:
    print(f"   ❌ TUI test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
print("\nIf you see issues:")
print("1. Try updating Textual: pip install --upgrade textual")
print("2. Check terminal: echo $TERM")
print("3. Try a different terminal (kitty, alacritty, iterm2)")
print("4. Run with verbose logging: lm analyze --tui --verbose")
