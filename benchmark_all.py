#!/usr/bin/env python3
"""
Comprehensive benchmark comparing all json2xml implementations:
- Pure Python (json2xml)
- Rust-powered Python (json2xml-rs)
- Go CLI (json2xml-go)
- Zig CLI (json2xml-zig)

Run with: python benchmark_all.py
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
from pathlib import Path

# Add the json2xml module to path
sys.path.insert(0, str(Path(__file__).parent))

from json2xml import dicttoxml as py_dicttoxml

# Try to import Rust implementation
try:
    from json2xml_rs import dicttoxml as rust_dicttoxml
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

# Check for CLI tools
GO_AVAILABLE = shutil.which("json2xml-go") is not None
ZIG_AVAILABLE = shutil.which("json2xml-zig") is not None


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
    return f"{color}{text}{Colors.NC}"


def random_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters, k=length))


def generate_test_data(num_records: int) -> list[dict]:
    """Generate test data with various types."""
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
    return data


def benchmark_python(data, iterations: int = 10, warmup: int = 2) -> dict:
    """Benchmark pure Python implementation."""
    # Warmup
    for _ in range(warmup):
        py_dicttoxml.dicttoxml(data, attr_type=True)

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = py_dicttoxml.dicttoxml(data, attr_type=True)
        end = time.perf_counter()
        times.append((end - start) * 1000)

    return {
        "avg": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "result_size": len(result),
    }


def benchmark_rust(data, iterations: int = 10, warmup: int = 2) -> dict | None:
    """Benchmark Rust implementation."""
    if not RUST_AVAILABLE:
        return None

    # Warmup
    for _ in range(warmup):
        rust_dicttoxml(data, attr_type=True)

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = rust_dicttoxml(data, attr_type=True)
        end = time.perf_counter()
        times.append((end - start) * 1000)

    return {
        "avg": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "result_size": len(result),
    }


def benchmark_cli(cmd: str, json_file: str, iterations: int = 10, warmup: int = 2) -> dict | None:
    """Benchmark CLI tool (Go or Zig)."""
    # Warmup
    for _ in range(warmup):
        subprocess.run([cmd, "-f", json_file], capture_output=True)

    times = []
    result_size = 0
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run([cmd, "-f", json_file], capture_output=True)
        end = time.perf_counter()
        times.append((end - start) * 1000)
        result_size = len(result.stdout)

    return {
        "avg": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "result_size": result_size,
    }


def format_time(ms: float) -> str:
    if ms < 1:
        return f"{ms * 1000:.2f}µs"
    elif ms < 1000:
        return f"{ms:.2f}ms"
    else:
        return f"{ms / 1000:.2f}s"


def run_benchmark(name: str, data: dict | list, iterations: int = 10):
    """Run benchmark for all implementations."""
    print(colorize(f"\n{'=' * 70}", Colors.BLUE))
    print(colorize(f"  {name}", Colors.BOLD))
    print(colorize(f"{'=' * 70}", Colors.BLUE))

    results = {}

    # Create temp file for CLI tools
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        json_file = f.name

    try:
        # Python implementation
        py_result = benchmark_python(data, iterations)
        results["python"] = py_result
        print(f"  {colorize('Python:', Colors.YELLOW):20} {format_time(py_result['avg']):>12} avg "
              f"(min: {format_time(py_result['min'])}, max: {format_time(py_result['max'])})")

        # Rust implementation
        if RUST_AVAILABLE:
            rust_result = benchmark_rust(data, iterations)
            results["rust"] = rust_result
            speedup = py_result["avg"] / rust_result["avg"]
            print(f"  {colorize('Rust:', Colors.GREEN):20} {format_time(rust_result['avg']):>12} avg "
                  f"(min: {format_time(rust_result['min'])}, max: {format_time(rust_result['max'])}) "
                  f"[{colorize(f'{speedup:.1f}x faster', Colors.GREEN)}]")
        else:
            print(f"  {colorize('Rust:', Colors.RED):20} NOT AVAILABLE")

        # Go implementation
        if GO_AVAILABLE:
            go_result = benchmark_cli("json2xml-go", json_file, iterations)
            results["go"] = go_result
            speedup = py_result["avg"] / go_result["avg"]
            color = Colors.GREEN if speedup > 1 else Colors.RED
            print(f"  {colorize('Go:', Colors.CYAN):20} {format_time(go_result['avg']):>12} avg "
                  f"(min: {format_time(go_result['min'])}, max: {format_time(go_result['max'])}) "
                  f"[{colorize(f'{speedup:.1f}x vs Python', color)}]")
        else:
            print(f"  {colorize('Go:', Colors.RED):20} NOT AVAILABLE")

        # Zig implementation
        if ZIG_AVAILABLE:
            zig_result = benchmark_cli("json2xml-zig", json_file, iterations)
            results["zig"] = zig_result
            speedup = py_result["avg"] / zig_result["avg"]
            color = Colors.GREEN if speedup > 1 else Colors.RED
            print(f"  {colorize('Zig:', Colors.MAGENTA):20} {format_time(zig_result['avg']):>12} avg "
                  f"(min: {format_time(zig_result['min'])}, max: {format_time(zig_result['max'])}) "
                  f"[{colorize(f'{speedup:.1f}x vs Python', color)}]")
        else:
            print(f"  {colorize('Zig:', Colors.RED):20} NOT AVAILABLE")

    finally:
        os.unlink(json_file)

    return results


def main():
    print(colorize("=" * 70, Colors.BLUE))
    print(colorize("  COMPREHENSIVE JSON2XML BENCHMARK", Colors.BOLD))
    print(colorize("  Python vs Rust vs Go vs Zig", Colors.BOLD))
    print(colorize("=" * 70, Colors.BLUE))

    print(colorize("\nAvailable implementations:", Colors.YELLOW))
    print(f"  • Python:  {colorize('✓', Colors.GREEN)} (pure Python)")
    print(f"  • Rust:    {colorize('✓', Colors.GREEN) if RUST_AVAILABLE else colorize('✗', Colors.RED)} (json2xml-rs)")
    print(f"  • Go:      {colorize('✓', Colors.GREEN) if GO_AVAILABLE else colorize('✗', Colors.RED)} (json2xml-go CLI)")
    print(f"  • Zig:     {colorize('✓', Colors.GREEN) if ZIG_AVAILABLE else colorize('✗', Colors.RED)} (json2xml-zig CLI)")

    # Test data
    small_data = {"name": "John", "age": 30, "city": "New York"}
    medium_data = generate_test_data(10)
    large_data = generate_test_data(100)
    very_large_data = generate_test_data(1000)

    # Load bigexample.json if available
    examples_dir = Path(__file__).parent / "examples"
    bigexample_file = examples_dir / "bigexample.json"
    if bigexample_file.exists():
        with open(bigexample_file) as f:
            bigexample_data = json.load(f)
    else:
        bigexample_data = None

    # Run benchmarks
    all_results = {}

    all_results["small"] = run_benchmark(
        f"Small JSON ({len(json.dumps(small_data))} bytes)",
        small_data,
        iterations=50,
    )

    all_results["medium"] = run_benchmark(
        f"Medium JSON ({len(json.dumps(medium_data))} bytes, 10 records)",
        medium_data,
        iterations=30,
    )

    if bigexample_data:
        all_results["bigexample"] = run_benchmark(
            f"bigexample.json ({len(json.dumps(bigexample_data))} bytes)",
            bigexample_data,
            iterations=20,
        )

    all_results["large"] = run_benchmark(
        f"Large JSON ({len(json.dumps(large_data))} bytes, 100 records)",
        large_data,
        iterations=15,
    )

    all_results["very_large"] = run_benchmark(
        f"Very Large JSON ({len(json.dumps(very_large_data))} bytes, 1000 records)",
        very_large_data,
        iterations=10,
    )

    # Summary table
    print(colorize("\n" + "=" * 70, Colors.BLUE))
    print(colorize("  SUMMARY TABLE", Colors.BOLD))
    print(colorize("=" * 70, Colors.BLUE))

    print(f"\n{'Test Case':<25} {'Python':>12} {'Rust':>12} {'Go':>12} {'Zig':>12}")
    print("-" * 73)

    for name, results in all_results.items():
        py_time = format_time(results.get("python", {}).get("avg", 0))
        rust_time = format_time(results.get("rust", {}).get("avg", 0)) if results.get("rust") else "N/A"
        go_time = format_time(results.get("go", {}).get("avg", 0)) if results.get("go") else "N/A"
        zig_time = format_time(results.get("zig", {}).get("avg", 0)) if results.get("zig") else "N/A"
        print(f"{name:<25} {py_time:>12} {rust_time:>12} {go_time:>12} {zig_time:>12}")

    # Speedup comparison
    print(colorize("\n" + "=" * 70, Colors.BLUE))
    print(colorize("  SPEEDUP vs PYTHON", Colors.BOLD))
    print(colorize("=" * 70, Colors.BLUE))

    print(f"\n{'Test Case':<25} {'Rust':>12} {'Go':>12} {'Zig':>12}")
    print("-" * 61)

    for name, results in all_results.items():
        py_avg = results.get("python", {}).get("avg", 1)
        rust_speedup = f"{py_avg / results['rust']['avg']:.1f}x" if results.get("rust") else "N/A"
        go_speedup = f"{py_avg / results['go']['avg']:.1f}x" if results.get("go") else "N/A"
        zig_speedup = f"{py_avg / results['zig']['avg']:.1f}x" if results.get("zig") else "N/A"
        print(f"{name:<25} {rust_speedup:>12} {go_speedup:>12} {zig_speedup:>12}")

    # Overall winner
    print(colorize("\n" + "=" * 70, Colors.BLUE))
    print(colorize("  NOTES", Colors.BOLD))
    print(colorize("=" * 70, Colors.BLUE))
    print("""
  • Python: Pure Python implementation (always available)
  • Rust:   Native extension via PyO3 (library call, no process overhead)
  • Go:     CLI tool (includes process spawn overhead)
  • Zig:    CLI tool (includes process spawn overhead)

  Note: CLI tools (Go, Zig) include process spawning overhead which makes
  them appear slower for small inputs. For larger data, this overhead
  becomes negligible. Rust extension has no such overhead since it's
  called directly from Python.
""")

    print(colorize("=" * 70, Colors.BLUE))
    print(colorize("  Benchmark complete!", Colors.GREEN))
    print(colorize("=" * 70, Colors.BLUE))


if __name__ == "__main__":
    main()
