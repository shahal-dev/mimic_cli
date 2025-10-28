#!/usr/bin/env python3
"""
ClusterPyXT CLI - Main Wrapper Script
This script runs the ClusterPyXT CLI from the finder directory.

author: @shahal-dev
"""

import sys
import os
from pathlib import Path

# Add the finder directory to Python path
finder_dir = Path(__file__).parent / "finder"
sys.path.insert(0, str(finder_dir))

# Change working directory to finder for proper imports
original_cwd = os.getcwd()
os.chdir(finder_dir)

try:
    # Import and run the main CLI
    import main_cli
    if __name__ == "__main__":
        main_func = getattr(main_cli, 'main', None)
        if main_func:
            main_func()
        else:
            print("Error: main function not found in clusterpyxt_cli module")
            sys.exit(1)
finally:
    # Restore original working directory
    os.chdir(original_cwd) 