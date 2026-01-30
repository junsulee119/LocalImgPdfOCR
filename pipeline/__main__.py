# Pipeline package entry point
"""
OCR Pipeline Package
Provides both CLI and GUI interfaces for OCR processing
"""
import sys

def main():
    """Main entry point - routes to CLI or GUI based on arguments"""
    if len(sys.argv) > 1:
        # Has arguments - use CLI
        from pipeline.cli_module import main as cli_main
        return cli_main()
    else:
        # No arguments - launch GUI
        from pipeline.gui_module import main as gui_main
        return gui_main()

if __name__ == '__main__':
    sys.exit(main())
