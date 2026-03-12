"""
GitQuickTool — Main entry point.
Auto-detects GUI/CLI mode based on arguments and environment.
"""

import sys
import os


def main():
    # CLI mode if arguments provided
    if len(sys.argv) > 1:
        from cli.commands import run_cli
        run_cli()
        return

    # GUI mode
    try:
        from ui.app import run_gui
        run_gui()
    except ImportError as e:
        print(f"GUI not available ({e}). Use CLI mode: python main.py --help")
        sys.exit(1)
    except Exception as e:
        # Fallback: if no display available (headless Linux), suggest CLI
        if "display" in str(e).lower() or "no display" in str(e).lower():
            print("No display detected. Use CLI mode: python main.py --help")
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
