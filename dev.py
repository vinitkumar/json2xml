#!/usr/bin/env python3
"""Development script for running tests, linting, and type checking."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(cmd, check=True, cwd=Path(__file__).parent)
        print(f"✅ {description} passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main() -> None:
    """Run development checks."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "all"

    success = True

    if command in ("lint", "all"):
        success &= run_command(["ruff", "check", "json2xml", "tests"], "Linting")

    if command in ("test", "all"):
        success &= run_command([
            "pytest", "--cov=json2xml", "--cov-report=term", 
            "-xvs", "tests", "-n", "auto"
        ], "Tests")

    if command in ("typecheck", "all"):
        success &= run_command(["mypy", "json2xml", "tests"], "Type checking")

    if command == "help":
        print("Usage: python dev.py [command]")
        print("Commands:")
        print("  all       - Run all checks (default)")
        print("  lint      - Run linting only")
        print("  test      - Run tests only")
        print("  typecheck - Run type checking only")
        print("  help      - Show this help")
        return

    if not success:
        print(f"\n❌ Some checks failed!")
        sys.exit(1)
    else:
        print(f"\n🎉 All checks passed!")


if __name__ == "__main__":
    main() 