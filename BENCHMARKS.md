# json2xml Benchmark Results

Comprehensive performance comparison between all json2xml implementations.

## Test Environment

- **Machine**: Apple Silicon (arm64)
- **OS**: macOS 26.4.1 (Darwin 25.4.0)
- **Python**: 3.14.4
- **Date**: April 24, 2026

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

### Comprehensive Benchmark (All Implementations)

```bash
python benchmark_all.py
```

### Rust vs Python Only

```bash
python benchmark_rust.py
```

### Multi-Python Version Benchmark

```bash
python benchmark_multi_python.py
```

## Related Projects

- **Go version**: [github.com/vinitkumar/json2xml-go](https://github.com/vinitkumar/json2xml-go)
- **Zig version**: [github.com/vinitkumar/json2xml-zig](https://github.com/vinitkumar/json2xml-zig)
