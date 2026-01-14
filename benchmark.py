#!/usr/bin/env python3
"""
Benchmark script for json2xml-py vs json2xml-go.

Compares performance of Python and Go implementations across
different JSON sizes.
"""
from __future__ import annotations

import json
import os
import random
import string
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Paths
PYTHON_CLI = [sys.executable, "-m", "json2xml.cli"]
GO_CLI = Path("/Users/vinitkumar/projects/go/json2xml-go/json2xml-go")
EXAMPLES_DIR = Path("/Users/vinitkumar/projects/python/json2xml/examples")

# Colors for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    NC = "\033[0m"  # No Color


def colorize(text: str, color: str) -> str:
    """Wrap text in color codes."""
    return f"{color}{text}{Colors.NC}"


def random_string(length: int = 10) -> str:
    """Generate a random string."""
    return "".join(random.choices(string.ascii_letters, k=length))


def generate_large_json(num_records: int = 1000) -> str:
    """Generate a large JSON file for benchmarking."""
    data = []
    for i in range(num_records):
        item = {
            "id": i,
            "name": random_string(20),
            "email": f"{random_string(8)}@example.com",
            "active": random.choice([True, False]),
            "score": round(random.uniform(0, 100), 2),
            "tags": [random_string(5) for _ in range(5)],
            "metadata": {
                "created": "2024-01-15T10:30:00Z",
                "updated": "2024-01-15T12:45:00Z",
                "version": random.randint(1, 100),
                "nested": {
                    "level1": {
                        "level2": {"value": random_string(10)}
                    }
                },
            },
        }
        data.append(item)
    return json.dumps(data)


def run_benchmark(
    cmd: list[str],
    iterations: int = 10,
    warmup: int = 2
) -> dict[str, float]:
    """
    Run a benchmark for the given command.

    Returns dict with avg, min, max times in milliseconds.

    Note: cmd is always a list constructed internally by this script,
    not from external/user input. The subprocess calls are safe.
    """
    times = []

    # Warmup runs
    # Security: cmd is a list constructed internally, not from user input
    for _ in range(warmup):
        subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603

    # Timed runs
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603
        end = time.perf_counter()

        if result.returncode != 0:
            print(f"Error: {result.stderr.decode()}")
            continue

        duration_ms = (end - start) * 1000
        times.append(duration_ms)

    if not times:
        return {"avg": 0, "min": 0, "max": 0}

    return {
        "avg": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
    }


def format_time(ms: float) -> str:
    """Format time in milliseconds."""
    if ms < 1:
        return f"{ms * 1000:.2f}µs"
    elif ms < 1000:
        return f"{ms:.2f}ms"
    else:
        return f"{ms / 1000:.2f}s"


def print_header(title: str) -> None:
    """Print a section header."""
    print(colorize("=" * 50, Colors.BLUE))
    print(colorize(f"  {title}", Colors.BOLD))
    print(colorize("=" * 50, Colors.BLUE))


def print_result(name: str, result: dict[str, float]) -> None:
    """Print benchmark result."""
    print(f"  {name}:")
    print(f"    Avg: {format_time(result['avg'])} | "
          f"Min: {format_time(result['min'])} | "
          f"Max: {format_time(result['max'])}")


def main() -> int:
    """Run the benchmark suite."""
    print_header("json2xml Benchmark: Python vs Go")
    print()

    # Check prerequisites
    print(colorize("Checking prerequisites...", Colors.YELLOW))

    if not GO_CLI.exists():
        print(colorize(f"Error: Go binary not found at {GO_CLI}", Colors.RED))
        print("Please build it first: cd json2xml-go && go build -o json2xml-go ./cmd/json2xml-go")
        return 1

    print(colorize("✓ Prerequisites met", Colors.GREEN))
    print()

    # Test configurations
    iterations = 10
    results = {}

    # Create temp files for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Small JSON - inline string
        small_json = '{"name": "John", "age": 30, "city": "New York"}'

        # Medium JSON - existing file
        medium_json_file = EXAMPLES_DIR / "bigexample.json"

        # Large JSON - generated
        large_json = generate_large_json(1000)
        large_json_file = Path(tmpdir) / "large.json"
        large_json_file.write_text(large_json)

        # Very large JSON
        very_large_json = generate_large_json(5000)
        very_large_json_file = Path(tmpdir) / "very_large.json"
        very_large_json_file.write_text(very_large_json)

        print(colorize("Test file sizes:", Colors.CYAN))
        print(f"  Small:      {len(small_json)} bytes (inline)")
        print(f"  Medium:     {medium_json_file.stat().st_size:,} bytes")
        print(f"  Large:      {large_json_file.stat().st_size:,} bytes (1000 records)")
        print(f"  Very Large: {very_large_json_file.stat().st_size:,} bytes (5000 records)")
        print()

        # Benchmark: Small JSON (inline string)
        print(colorize("--- Small JSON (inline string) ---", Colors.BLUE))
        py_small = run_benchmark(PYTHON_CLI + ["-s", small_json], iterations)
        go_small = run_benchmark([str(GO_CLI), "-s", small_json], iterations)
        print_result("Python", py_small)
        print_result("Go", go_small)
        results["small"] = {"python": py_small, "go": go_small}
        print()

        # Benchmark: Medium JSON (file)
        print(colorize("--- Medium JSON (bigexample.json) ---", Colors.BLUE))
        py_medium = run_benchmark(PYTHON_CLI + [str(medium_json_file)], iterations)
        go_medium = run_benchmark([str(GO_CLI), str(medium_json_file)], iterations)
        print_result("Python", py_medium)
        print_result("Go", go_medium)
        results["medium"] = {"python": py_medium, "go": go_medium}
        print()

        # Benchmark: Large JSON (file)
        print(colorize("--- Large JSON (1000 records) ---", Colors.BLUE))
        py_large = run_benchmark(PYTHON_CLI + [str(large_json_file)], iterations)
        go_large = run_benchmark([str(GO_CLI), str(large_json_file)], iterations)
        print_result("Python", py_large)
        print_result("Go", go_large)
        results["large"] = {"python": py_large, "go": go_large}
        print()

        # Benchmark: Very Large JSON (file)
        print(colorize("--- Very Large JSON (5000 records) ---", Colors.BLUE))
        py_vlarge = run_benchmark(PYTHON_CLI + [str(very_large_json_file)], iterations)
        go_vlarge = run_benchmark([str(GO_CLI), str(very_large_json_file)], iterations)
        print_result("Python", py_vlarge)
        print_result("Go", go_vlarge)
        results["very_large"] = {"python": py_vlarge, "go": go_vlarge}
        print()

    # Summary
    print_header("SUMMARY")
    print()

    for size, data in results.items():
        py_avg = data["python"]["avg"]
        go_avg = data["go"]["avg"]

        if go_avg > 0:
            speedup = py_avg / go_avg
            speedup_str = colorize(f"{speedup:.1f}x faster", Colors.GREEN)
        else:
            speedup_str = "N/A"

        print(colorize(f"{size.replace('_', ' ').title()} JSON:", Colors.BOLD))
        print(f"  Python: {format_time(py_avg)}")
        print(f"  Go:     {format_time(go_avg)}")
        print(f"  Go is {speedup_str}")
        print()

    # Overall average speedup
    total_py = sum(r["python"]["avg"] for r in results.values())
    total_go = sum(r["go"]["avg"] for r in results.values())
    if total_go > 0:
        overall_speedup = total_py / total_go
        print(colorize(f"Overall: Go is {overall_speedup:.1f}x faster than Python", Colors.GREEN + Colors.BOLD))

    print()
    print(colorize("=" * 50, Colors.BLUE))
    print(colorize("Benchmark complete!", Colors.GREEN))
    print(colorize("=" * 50, Colors.BLUE))

    return 0


if __name__ == "__main__":
    sys.exit(main())
