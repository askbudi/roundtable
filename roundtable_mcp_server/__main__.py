#!/usr/bin/env python3
"""Roundtable AI MCP Server - Main entry point for module execution."""

import sys
from pathlib import Path

try:
    from .server import main
except ImportError:
    # Add current directory to path for direct execution
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    from server import main

if __name__ == "__main__":
    main()