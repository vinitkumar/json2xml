#!/usr/bin/env python3
"""
Multi-Python Benchmark: Compare json2xml performance across Python implementations.

Compares:
- CPython 3.14.2 (homebrew)
- CPython 3.15.0a4 (latest alpha)
- PyPy 3.10.16
- Go (json2xml-go)

Each Python version gets its own virtual environment with json2xml installed.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import string
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).resolve().parent
VENVS_DIR = BASE_DIR / ".benchmark_venvs"
GO_CLI = Path(os.environ.get("JSON2XML_GO_CLI", "json2xml-go"))

# Python implementations to benchmark
PYTHON_VERSIONS = [
    {
        "name": "CPython 3.14.2",
        "python": "/opt/homebrew/bin/python3.14",
        "venv_name": "venv_cpython314_2",
    },
    {
        "name": "CPython 3.15.0a4",
        "python": str(Path.home() / ".local/share/uv/python/cpython-3.15.0a4-macos-aarch64-none/bin/python3.15"),
        "venv_name": "venv_cpython315a4",
    },
    {
        "name": "PyPy 3.10.16",
        "python": str(Path.home() / ".local/share/uv/python/pypy-3.10.19-macos-aarch64-none/bin/pypy3.10"),
        "venv_name": "venv_pypy310",
    },
]


# Colors for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    BOLD = "\033[1m"
    NC = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Wrap text in color codes."""
    return f"{color}{text}{Colors.NC}"


def random_string(length: int = 10) -> str:
    """Generate a random string."""
    return "".join(random.choices(string.ascii_letters, k=length))


def generate_test_json(num_records: int = 1000) -> str:
    """Generate a JSON file for benchmarking."""
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


@dataclass
class BenchmarkResult:
    """Holds benchmark timing results."""
    name: str
    avg_ms: float
    min_ms: float
    max_ms: float
    success: bool
    error: str = ""


def setup_venv(python_path: str, venv_path: Path) -> bool:
    """Create a virtual environment and install json2xml."""
    if not Path(python_path).exists():
        print(f"  {colorize('✗', Colors.RED)} Python not found: {python_path}")
        return False

    # Create venv if it doesn't exist or is broken
    venv_python = venv_path / "bin" / "python"
    if not venv_python.exists():
        print(f"  Creating venv at {venv_path}...")
        result = subprocess.run(
            [python_path, "-m", "venv", str(venv_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  {colorize('✗', Colors.RED)} Failed to create venv: {result.stderr}")
            return False

        # Install json2xml in the venv
        print(f"  Installing json2xml...")
        pip_path = venv_path / "bin" / "pip"
        result = subprocess.run(
            [str(pip_path), "install", "-e", str(BASE_DIR), "-q"],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
        )
        if result.returncode != 0:
            print(f"  {colorize('✗', Colors.RED)} Failed to install json2xml: {result.stderr}")
            return False

    return True


def run_benchmark(
    cmd: list[str],
    iterations: int = 10,
    warmup: int = 2,
) -> BenchmarkResult:
    """Run a benchmark for the given command."""
    times = []

    # Check if command exists
    if not Path(cmd[0]).exists() and not shutil.which(cmd[0]):
        return BenchmarkResult(
            name="",
            avg_ms=0,
            min_ms=0,
            max_ms=0,
            success=False,
            error=f"Command not found: {cmd[0]}",
        )

    # Warmup runs
    for _ in range(warmup):
        result = subprocess.run(cmd, capture_output=True, check=False)
        if result.returncode != 0:
            return BenchmarkResult(
                name="",
                avg_ms=0,
                min_ms=0,
                max_ms=0,
                success=False,
                error=result.stderr.decode()[:100],
            )

    # Timed runs
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, check=False)
        end = time.perf_counter()

        if result.returncode != 0:
            return BenchmarkResult(
                name="",
                avg_ms=0,
                min_ms=0,
                max_ms=0,
                success=False,
                error=result.stderr.decode()[:100],
            )

        duration_ms = (end - start) * 1000
        times.append(duration_ms)

    return BenchmarkResult(
        name="",
        avg_ms=sum(times) / len(times),
        min_ms=min(times),
        max_ms=max(times),
        success=True,
    )


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
    print(colorize("=" * 70, Colors.BLUE))
    print(colorize(f"  {title}", Colors.BOLD))
    print(colorize("=" * 70, Colors.BLUE))


def print_table_row(name: str, result: BenchmarkResult, baseline_ms: float | None = None) -> None:
    """Print a formatted table row."""
    if not result.success:
        print(f"  {name:<35} {colorize('FAILED', Colors.RED)}: {result.error}")
        return

    speedup_str = ""
    if baseline_ms and result.avg_ms > 0:
        speedup = baseline_ms / result.avg_ms
        if speedup > 1:
            speedup_str = colorize(f" ({speedup:.1f}x faster)", Colors.GREEN)
        else:
            speedup_str = f" ({1/speedup:.1f}x slower)"

    print(f"  {name:<35} {format_time(result.avg_ms):>12} "
          f"(min: {format_time(result.min_ms)}, max: {format_time(result.max_ms)}){speedup_str}")


def main() -> int:
    """Run the multi-Python benchmark suite."""
    print_header("Multi-Python Benchmark: json2xml Performance")
    print()

    # Create venvs directory
    VENVS_DIR.mkdir(exist_ok=True)

    # Setup phase
    print(colorize("Setting up Python environments...", Colors.YELLOW))
    print()

    active_pythons = []
    for py_config in PYTHON_VERSIONS:
        name = py_config["name"]
        python_path = py_config["python"]
        venv_name = py_config["venv_name"]
        venv_path = VENVS_DIR / venv_name

        print(f"  {name}:")
        if setup_venv(python_path, venv_path):
            print(f"    {colorize('✓', Colors.GREEN)} Ready")
            active_pythons.append({
                **py_config,
                "venv_path": venv_path,
                "cli_python": str(venv_path / "bin" / "python"),
            })
        else:
            print(f"    {colorize('✗', Colors.RED)} Skipped")
        print()

    # Check Go CLI
    go_available = shutil.which(str(GO_CLI)) is not None or Path(GO_CLI).exists()
    if go_available:
        print(f"  Go (json2xml-go): {colorize('✓', Colors.GREEN)} Ready")
    else:
        print(f"  Go (json2xml-go): {colorize('✗', Colors.RED)} Not found at {GO_CLI}")
        print(f"    Set JSON2XML_GO_CLI env var or ensure json2xml-go is in PATH")
    print()

    if not active_pythons:
        print(colorize("Error: No Python environments available!", Colors.RED))
        return 1

    # Generate test files
    print(colorize("Generating test data...", Colors.YELLOW))

    with tempfile.TemporaryDirectory() as tmpdir:
        # Small JSON
        small_json = '{"name": "John", "age": 30, "city": "New York"}'

        # Medium JSON (existing file)
        medium_json_file = BASE_DIR / "examples" / "bigexample.json"

        # Large JSON
        large_json = generate_test_json(1000)
        large_json_file = Path(tmpdir) / "large.json"
        large_json_file.write_text(large_json)

        # Very large JSON
        very_large_json = generate_test_json(5000)
        very_large_json_file = Path(tmpdir) / "very_large.json"
        very_large_json_file.write_text(very_large_json)

        print(f"  Small:      {len(small_json):,} bytes")
        print(f"  Medium:     {medium_json_file.stat().st_size:,} bytes")
        print(f"  Large:      {large_json_file.stat().st_size:,} bytes (1000 records)")
        print(f"  Very Large: {very_large_json_file.stat().st_size:,} bytes (5000 records)")
        print()

        iterations = 10
        all_results: dict[str, dict[str, BenchmarkResult]] = {}

        # Benchmark each test case
        test_cases = [
            ("Small JSON", ["-s", small_json]),
            ("Medium JSON", [str(medium_json_file)]),
            ("Large JSON (1K)", [str(large_json_file)]),
            ("Very Large JSON (5K)", [str(very_large_json_file)]),
        ]

        for test_name, args in test_cases:
            print_header(f"Benchmark: {test_name}")
            print()

            results: dict[str, BenchmarkResult] = {}

            # Benchmark each Python version
            for py_config in active_pythons:
                name = py_config["name"]
                cli_python = py_config["cli_python"]
                cmd = [cli_python, "-m", "json2xml.cli"] + args

                result = run_benchmark(cmd, iterations=iterations)
                result.name = name
                results[name] = result

            # Benchmark Go
            if go_available:
                go_cmd = [str(GO_CLI)] + args
                go_result = run_benchmark(go_cmd, iterations=iterations)
                go_result.name = "Go (json2xml-go)"
                results["Go"] = go_result

            all_results[test_name] = results

            # Find baseline (first successful Python result)
            baseline_ms = None
            for py_config in active_pythons:
                if results.get(py_config["name"], BenchmarkResult("", 0, 0, 0, False)).success:
                    baseline_ms = results[py_config["name"]].avg_ms
                    break

            # Print results
            for py_config in active_pythons:
                name = py_config["name"]
                if name in results:
                    print_table_row(name, results[name], baseline_ms)

            if go_available and "Go" in results:
                print_table_row("Go (json2xml-go)", results["Go"], baseline_ms)

            print()

        # Summary
        print_header("SUMMARY: Average Times Across All Tests")
        print()

        # Calculate averages
        avg_times: dict[str, list[float]] = {}
        for test_name, results in all_results.items():
            for name, result in results.items():
                if result.success:
                    if name not in avg_times:
                        avg_times[name] = []
                    avg_times[name].append(result.avg_ms)

        # Print summary table
        print(f"  {'Implementation':<35} {'Avg Time':>12} {'vs CPython 3.14.2':>20}")
        print(f"  {'-' * 35} {'-' * 12} {'-' * 20}")

        baseline_name = "CPython 3.14.2"
        baseline_avg = sum(avg_times.get(baseline_name, [0])) / len(avg_times.get(baseline_name, [1]))

        sorted_impls = sorted(avg_times.items(), key=lambda x: sum(x[1]) / len(x[1]))

        for name, times in sorted_impls:
            avg = sum(times) / len(times)
            if baseline_avg > 0 and name != baseline_name:
                speedup = baseline_avg / avg
                if speedup > 1:
                    vs_baseline = colorize(f"{speedup:.2f}x faster", Colors.GREEN)
                else:
                    vs_baseline = f"{1/speedup:.2f}x slower"
            else:
                vs_baseline = "baseline"

            print(f"  {name:<35} {format_time(avg):>12} {vs_baseline:>20}")

        print()
        print(colorize("=" * 70, Colors.BLUE))
        print(colorize("Benchmark complete!", Colors.GREEN))
        print(colorize("=" * 70, Colors.BLUE))

    return 0


if __name__ == "__main__":
    sys.exit(main())
