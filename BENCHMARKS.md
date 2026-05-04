# json2xml Benchmark Results

Comprehensive performance comparison between all json2xml implementations.

## Test Environment

- **Machine**: Apple Silicon (arm64)
- **OS**: macOS 26.4.1 (Darwin 25.4.0)
- **Python**: 3.14.4
- **Date**: April 24, 2026

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
| Medium | 10 generated records with nested structures | 3,212 |
| bigexample.json | Real-world patent data | 2,018 |
| Large | 100 generated records with nested structures | 32,207 |
| Very Large | 1,000 generated records with nested structures | 323,148 |

## Results

### Performance Summary

| Test Case | Python | Rust | Go | Zig |
|-----------|--------|------|-----|-----|
| Small (47B) | 31.49µs | 0.55µs | 4.09ms | 2.02ms |
| Medium (3.2KB) | 1.69ms | 16.15µs | 4.07ms | 2.09ms |
| bigexample (2KB) | 819.86µs | 6.44µs | 4.37ms | 2.11ms |
| Large (32KB) | 17.97ms | 168.21µs | 4.10ms | 2.42ms |
| Very Large (323KB) | 183.33ms | 1.42ms | 4.20ms | 5.12ms |

### Speedup vs Pure Python

| Test Case | Rust | Go | Zig |
|-----------|------|-----|-----|
| Small (47B) | **56.8x** | 0.0x* | 0.0x* |
| Medium (3.2KB) | **105.0x** | 0.4x* | 0.8x* |
| bigexample (2KB) | **127.2x** | 0.2x* | 0.4x* |
| Large (32KB) | **106.8x** | 4.4x | **7.4x** |
| Very Large (323KB) | **129.0x** | **43.6x** | **35.8x** |

*CLI tools have process spawn overhead (~2-4ms) which dominates for small inputs.

## Key Observations

### 1. Rust Extension is the Best Choice for Python Users 🦀

The Rust extension (json2xml-rs) provides:
- **~57-129x faster** conversion than pure Python in this run
- **Zero process overhead** - called directly from Python
- **Automatic fallback** - pure Python used if Rust is unavailable or a feature requires it
- **Easy install**: `pip install json2xml[fast]`

### 2. Go Excels for Very Large CLI Workloads 🚀

For very large inputs (323KB+):
- **43.6x faster** than Python
- But ~4ms startup overhead hurts small file performance
- Best for batch processing or large file conversions from shell scripts

### 3. Zig is Highly Competitive for CLI Use ⚡

In this run:
- **35.8x faster** than Python for very large files
- **7.4x faster** for large files (32KB)
- Faster startup than Go (~2ms vs ~4ms)
- Best balance of startup time and throughput for mixed CLI workloads

### 4. Process Spawn Overhead Matters

CLI tools (Go, Zig) have process spawn overhead:
- Go: ~4ms startup overhead
- Zig: ~2ms startup overhead
- Dominates for small inputs (makes them appear slower than Python)
- Negligible for large inputs where actual work dominates
- Rust extension avoids this entirely by being a native Python module

## When to Use Each Implementation

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Python library calls | **Rust** (`pip install json2xml[fast]`) | 57-129x faster, no process overhead |
| Small files via CLI | **Zig** (json2xml-zig) | Fastest startup among native CLIs (~2ms) |
| Large files via CLI | **Go** or **Zig** | Both excellent; Zig wins at 32KB, Go wins at 323KB in this run |
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
compares the hard-coded Python paths in `benchmark_multi_python.py`. Edit
`PYTHON_VERSIONS` in that script or install the listed interpreters before
running it. Set `JSON2XML_GO_CLI=/path/to/json2xml-go` if the Go binary is not
named `json2xml-go` on `PATH`.

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
