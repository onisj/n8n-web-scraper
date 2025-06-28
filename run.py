#!/usr/bin/env python3
"""Convenience wrapper for the main start_system script.

This script maintains backward compatibility by allowing users to run
the system startup from the project root directory.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run the main start_system script from src/scripts."""
    script_path = Path(__file__).parent / "src" / "scripts" / "start_system.py"
    
    if not script_path.exists():
        print(f"Error: Could not find {script_path}")
        sys.exit(1)
    
    # Pass all arguments to the actual script
    cmd = [sys.executable, str(script_path)] + sys.argv[1:]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()