# json2xml Benchmark Results

Comprehensive performance comparison between all json2xml implementations.

## Test Environment

- **Machine**: Apple Silicon (arm64)
- **OS**: macOS 26.5 (Darwin 25.5.0)
- **Python**: 3.14.4
- **Date**: May 27, 2026
- **CLI tools**: `json2xml-go` and `json2xml-zig` on `PATH` (the published run used a local `~/.local/bin` install)

To make new runs comparable, record the same fields for your machine before
publishing results:

```bash
python --version
uname -a
sw_vers 2>/dev/null || true
which json2xml-go json2xml-zig 2>/dev/null || true
```

### Implementations Tested

| Implementation | Type | Notes |
|----------------|------|-------|
| Python | Library | Pure Python (json2xml) |
| Rust | Library | Native extension via PyO3 (json2xml-rs) |
| Go | CLI | Standalone binary (json2xml-go) |
| Zig | CLI | Standalone binary (json2xml-zig) |

## Test Data

| Size | Description | Bytes |
|------|-------------|-------|
| Small | Simple object `{"name": "John", "age": 30, "city": "New York"}` | 47 |
| Medium | 10 generated records with nested structures | 3,215 |
| bigexample.json | Real-world patent data | 2,018 |
| Large | 100 generated records with nested structures | 32,206 |
| Very Large | 1,000 generated records with nested structures | 323,131 |

## Results

### Performance Summary

| Test Case | Python | Rust | Go | Zig |
|-----------|--------|------|-----|-----|
| Small (47B) | 3.19µs | 0.86µs | 6.05ms | 3.08ms |
| Medium (3.2KB) | 214.83µs | 18.41µs | 5.85ms | 3.12ms |
| bigexample (2KB) | 91.20µs | 7.32µs | 5.76ms | 3.08ms |
| Large (32KB) | 2.07ms | 175.46µs | 5.89ms | 3.73ms |
| Very Large (323KB) | 21.20ms | 1.48ms | 6.82ms | 7.82ms |

### Speedup vs Pure Python

| Test Case | Rust | Go | Zig |
|-----------|------|-----|-----|
| Small (47B) | **3.7x** | 0.0x* | 0.0x* |
| Medium (3.2KB) | **11.7x** | 0.0x* | 0.1x* |
| bigexample (2KB) | **12.5x** | 0.0x* | 0.0x* |
| Large (32KB) | **11.8x** | 0.4x* | 0.6x* |
| Very Large (323KB) | **14.4x** | **3.1x** | **2.7x** |

*CLI tools have process spawn overhead (~3-6ms) which dominates for small inputs.

### Multi-Python CLI Benchmark (June 25, 2026)

This rerun compares the same CLI workload across uv-managed CPython 3.14.6, CPython 3.15.0b3, PyPy 3.11.15, and `json2xml-go`. The listed environment is the recorded machine for this run, not a requirement for contributors on other platforms.

#### Environment

- **Machine**: Apple Silicon (arm64)
- **OS**: macOS 26.5.1 (Darwin 25.5.0)
- **Interpreters**: CPython 3.14.6, CPython 3.15.0b3, PyPy 3.11.15
- **Date**: June 25, 2026
- **Go CLI**: `json2xml-go` on `PATH` (the recorded run used a local `~/.local/bin` install)

#### Results

| Test Case | CPython 3.14.6 | CPython 3.15.0b3 | PyPy 3.11.15 | Go |
|-----------|----------------|------------------|--------------|----|
| Small (47B) | 61.86ms | 47.61ms | 98.45ms | 4.46ms |
| Medium (2.6KB) | 62.85ms | 43.41ms | 97.96ms | 4.88ms |
| Large (323KB, 1K records) | 174.11ms | 146.74ms | 271.24ms | 62.23ms |
| Very Large (1.62MB, 5K records) | 759.26ms | 691.53ms | 526.96ms | 269.96ms |

#### Takeaways

- **CPython 3.15.0b3 beat CPython 3.14.6 in every test**, from **1.14x faster on average** across the four cases.
- **PyPy 3.11.15 still lagged on smaller inputs** because startup cost dominates, but it **overtook both CPython builds on the 5K-record case**.
- **Go remained the fastest CLI path overall**, mainly because the conversion work dominates process startup once the payload gets large.
- These numbers are **end-to-end subprocess timings**, not isolated serializer throughput, so interpreter startup and environment activation costs are part of the result by design.

## Key Observations

### 1. Rust Extension is the Best Choice for Python Users 🦀

The Rust extension (json2xml-rs) provides:
- **~4-14x faster** conversion than the optimized pure Python path in this run
- **Zero process overhead** - called directly from Python
- **Automatic fallback** - pure Python used if Rust is unavailable or a feature requires it
- **Easy install**: `pip install json2xml[fast]`

### 2. Python Optimizations Changed the Relative Speedups

Recent pure Python improvements substantially reduced conversion time:
- Small inputs dropped to microsecond-level library-call timings
- Medium and large inputs are roughly an order of magnitude faster than the April 2026 run
- Rust remains the fastest library backend, but its relative speedup is lower because the baseline improved

### 3. Go Excels for Very Large CLI Workloads 🚀

For very large inputs (323KB+):
- **3.1x faster** than optimized Python in this run
- But ~6ms startup overhead hurts small and medium file performance
- Best for batch processing or large file conversions from shell scripts

### 4. Zig is Highly Competitive for CLI Use ⚡

In this run:
- **2.7x faster** than optimized Python for very large files
- Slower than optimized Python for the 32KB library-call benchmark once process startup is included
- Faster startup than Go (~3ms vs ~6ms)
- Best balance of startup time and throughput for mixed CLI workloads

### 5. Process Spawn Overhead Matters

CLI tools (Go, Zig) have process spawn overhead:
- Go: ~6ms startup overhead
- Zig: ~3ms startup overhead
- Dominates for small inputs (makes them appear slower than Python)
- Negligible for large inputs where actual work dominates
- Rust extension avoids this entirely by being a native Python module

## When to Use Each Implementation

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Python library calls | **Rust** (`pip install json2xml[fast]`) | 4-14x faster, no process overhead |
| Small files via CLI | **Zig** (json2xml-zig) | Fastest startup among native CLIs (~3ms) |
| Large files via CLI | **Go** or **Zig** | Both excellent; Go wins at 323KB in this run |
| Batch processing | **Go** or **Rust** | Both excellent depending on shell vs Python integration |
| Pure Python required | **Python** (json2xml) | Always available |

## Installation

```bash
# Pure Python (always works)
pip install json2xml

# With Rust acceleration (recommended)
pip install json2xml[fast]

# Go CLI
go install github.com/vinitkumar/json2xml-go@latest

# Zig CLI
# See: github.com/vinitkumar/json2xml-zig
```

## Running the Benchmarks

Run benchmarks from a clean checkout with the project installed in an isolated
environment. The exact virtual environment tool does not matter; the commands
below use `uv` because it keeps Python setup reproducible.

### Required Tools

| Tool | Required for | Notes |
|------|--------------|-------|
| Python 3.10+ | Pure Python benchmarks | The published run used Python 3.14.4. |
| Rust toolchain | Rust extension benchmarks | Needed only when building `json2xml_rs` locally. |
| maturin | Rust extension benchmarks | Builds and installs the PyO3 extension. |
| json2xml-go | Go CLI benchmarks | Must be on `PATH` as `json2xml-go`. |
| json2xml-zig | Zig CLI benchmarks | Must be on `PATH` as `json2xml-zig`. |

### Environment Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

For Rust benchmarks, install the extension into the same environment:

```bash
uv pip install maturin
cd rust
maturin develop --release
cd ..
```

For native CLI benchmarks, install the external tools and verify that the
commands are visible:

```bash
go install github.com/vinitkumar/json2xml-go@latest
which json2xml-go
which json2xml-zig
```

### Comprehensive Benchmark (All Implementations)

Runs pure Python, Rust if `json2xml_rs` imports successfully, Go if
`json2xml-go` is on `PATH`, and Zig if `json2xml-zig` is on `PATH`.

```bash
python benchmark_all.py
```

### Rust vs Python Only

Runs the library-call benchmark for pure Python and the PyO3 Rust extension.
If the extension is not installed, the script prints a warning and reports
Python-only results for reference.

```bash
python benchmark_rust.py
```

### Multi-Python Version Benchmark

Creates per-interpreter virtual environments under `.benchmark_venvs/` and
compares the configured Python interpreter paths in `benchmark_multi_python.py`.
By default the script looks for uv-managed CPython 3.14.6, CPython 3.15.0b3,
and PyPy 3.11.15 under `JSON2XML_UV_PYTHON_DIR` (default:
`~/.local/share/uv/python`). Override individual interpreter paths with
`JSON2XML_PYTHON_CPYTHON_314_6`, `JSON2XML_PYTHON_CPYTHON_315_0B3`, or
`JSON2XML_PYTHON_PYPY_311_15` if your layout differs. Set
`JSON2XML_GO_CLI=/path/to/json2xml-go` if the Go binary is not named
`json2xml-go` on `PATH`.

```bash
python benchmark_multi_python.py
```

### Interpreting CLI Numbers

The Go and Zig rows measure full process startup plus conversion because
`benchmark_all.py` invokes those tools with `subprocess.run`. That is the right
measurement for shell workflows, but it is not directly comparable to Python or
Rust library calls for tiny inputs. For small JSON payloads, process startup can
dominate the result; for large payloads, conversion throughput matters more.

## Related Projects

- **Go version**: [github.com/vinitkumar/json2xml-go](https://github.com/vinitkumar/json2xml-go)
- **Zig version**: [github.com/vinitkumar/json2xml-zig](https://github.com/vinitkumar/json2xml-zig)
