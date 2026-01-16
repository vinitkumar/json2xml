#!/usr/bin/env python3
"""
Benchmark script comparing Rust vs Python dicttoxml implementations.

Run after building the Rust extension:
    cd rust && maturin develop --release && cd ..
    python benchmark_rust.py
"""
from __future__ import annotations

import json
import random
import string
import sys
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
    print("WARNING: Rust extension not built. Run 'cd rust && maturin develop --release'")


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
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


def benchmark(func, data, iterations: int = 10, warmup: int = 2) -> dict:
    """Run benchmark and return timing stats."""
    # Warmup
    for _ in range(warmup):
        func(data)

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = func(data)
        end = time.perf_counter()
        times.append((end - start) * 1000)

    return {
        "avg": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "result_size": len(result),
    }


def format_time(ms: float) -> str:
    if ms < 1:
        return f"{ms * 1000:.2f}µs"
    elif ms < 1000:
        return f"{ms:.2f}ms"
    else:
        return f"{ms / 1000:.2f}s"


def run_benchmark(name: str, data: dict | list, iterations: int = 10):
    """Run and print benchmark for both implementations."""
    print(colorize(f"\n--- {name} ---", Colors.BLUE))

    # Python implementation
    py_result = benchmark(
        lambda d: py_dicttoxml.dicttoxml(d, attr_type=True),
        data,
        iterations,
    )
    print(f"  Python: {format_time(py_result['avg'])} avg "
          f"(min: {format_time(py_result['min'])}, max: {format_time(py_result['max'])})")

    if RUST_AVAILABLE:
        # Rust implementation
        rust_result = benchmark(
            lambda d: rust_dicttoxml(d, attr_type=True),
            data,
            iterations,
        )
        print(f"  Rust:   {format_time(rust_result['avg'])} avg "
              f"(min: {format_time(rust_result['min'])}, max: {format_time(rust_result['max'])})")

        speedup = py_result["avg"] / rust_result["avg"]
        color = Colors.GREEN if speedup > 1 else Colors.RED
        print(colorize(f"  Speedup: {speedup:.2f}x", color))

        return py_result, rust_result
    else:
        print("  Rust: NOT AVAILABLE")
        return py_result, None


def verify_output_match(data: dict | list) -> bool:
    """Verify that Rust and Python produce equivalent output."""
    if not RUST_AVAILABLE:
        return True

    py_output = py_dicttoxml.dicttoxml(data, attr_type=True)
    rust_output = rust_dicttoxml(data, attr_type=True)

    # They should produce the same output
    if py_output == rust_output:
        return True

    # If not exactly equal, check if they're semantically equivalent
    # (different attribute ordering, etc.)
    print("WARNING: Outputs differ (may be attribute ordering)")
    print(f"  Python: {py_output[:200]}...")
    print(f"  Rust:   {rust_output[:200]}...")
    return False


def main():
    print(colorize("=" * 60, Colors.BLUE))
    print(colorize("  json2xml Benchmark: Rust vs Python", Colors.BOLD))
    print(colorize("=" * 60, Colors.BLUE))

    if not RUST_AVAILABLE:
        print(colorize("\nRust extension not available!", Colors.RED))
        print("Build it with: cd rust && maturin develop --release")
        print("\nRunning Python-only benchmarks for reference...\n")

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

    # Verify outputs match before benchmarking
    print(colorize("\nVerifying output equivalence...", Colors.YELLOW))
    if verify_output_match(small_data):
        print(colorize("✓ Small data matches", Colors.GREEN))
    if verify_output_match(medium_data):
        print(colorize("✓ Medium data matches", Colors.GREEN))

    # Run benchmarks
    results = {}

    results["small"] = run_benchmark(
        f"Small JSON ({len(json.dumps(small_data))} bytes)",
        small_data,
        iterations=100,
    )

    results["medium"] = run_benchmark(
        f"Medium JSON ({len(json.dumps(medium_data))} bytes, 10 records)",
        medium_data,
        iterations=50,
    )

    if bigexample_data:
        results["bigexample"] = run_benchmark(
            f"bigexample.json ({len(json.dumps(bigexample_data))} bytes)",
            bigexample_data,
            iterations=50,
        )

    results["large"] = run_benchmark(
        f"Large JSON ({len(json.dumps(large_data))} bytes, 100 records)",
        large_data,
        iterations=20,
    )

    results["very_large"] = run_benchmark(
        f"Very Large JSON ({len(json.dumps(very_large_data))} bytes, 1000 records)",
        very_large_data,
        iterations=10,
    )

    # Summary
    print(colorize("\n" + "=" * 60, Colors.BLUE))
    print(colorize("  SUMMARY", Colors.BOLD))
    print(colorize("=" * 60, Colors.BLUE))

    if RUST_AVAILABLE:
        total_py = sum(r[0]["avg"] for r in results.values() if r[0])
        total_rust = sum(r[1]["avg"] for r in results.values() if r[1])
        overall_speedup = total_py / total_rust

        print(f"\nPython total time: {format_time(total_py)}")
        print(f"Rust total time:   {format_time(total_rust)}")
        print(colorize(f"\nOverall: Rust is {overall_speedup:.2f}x faster than Python", Colors.GREEN + Colors.BOLD))
    else:
        print("\nRust extension not available for comparison.")
        print("Build with: cd rust && maturin develop --release")

    print(colorize("\n" + "=" * 60, Colors.BLUE))
    print(colorize("Benchmark complete!", Colors.GREEN))
    print(colorize("=" * 60, Colors.BLUE))


if __name__ == "__main__":
    main()
