"""Shared formatting helpers for the standalone benchmark scripts."""

from __future__ import annotations

import random
import string


class Colors:
    """ANSI colors used by benchmark output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    BOLD = "\033[1m"
    NC = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{Colors.NC}"


def random_string(length: int = 10) -> str:
    """Generate a random ASCII string for benchmark payloads."""
    return "".join(random.choices(string.ascii_letters, k=length))


def format_time(milliseconds: float) -> str:
    """Format elapsed milliseconds for human-readable benchmark output."""
    if milliseconds < 1:
        return f"{milliseconds * 1000:.2f}µs"
    if milliseconds < 1000:
        return f"{milliseconds:.2f}ms"
    return f"{milliseconds / 1000:.2f}s"
