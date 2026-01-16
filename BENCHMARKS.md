# json2xml Benchmark Results

Comprehensive performance comparison between all json2xml implementations.

## Test Environment

- **Machine**: Apple Silicon (M-series, aarch64)
- **OS**: macOS
- **Date**: January 16, 2026

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
| Large | 100 generated records with nested structures | 32,226 |
| Very Large | 1,000 generated records with nested structures | 323,126 |

## Results

### Performance Summary

| Test Case | Python | Rust | Go | Zig |
|-----------|--------|------|-----|-----|
| Small (47B) | 40.12µs | 1.45µs | 4.65ms | 3.74ms |
| Medium (3.2KB) | 2.14ms | 71.28µs | 4.07ms | 3.28ms |
| bigexample (2KB) | 819.46µs | 32.88µs | 4.02ms | 2.96ms |
| Large (32KB) | 21.08ms | 739.89µs | 4.05ms | 6.11ms |
| Very Large (323KB) | 212.61ms | 7.55ms | 4.38ms | 33.24ms |

### Speedup vs Pure Python

| Test Case | Rust | Go | Zig |
|-----------|------|-----|-----|
| Small (47B) | **27.6x** | 0.0x* | 0.0x* |
| Medium (3.2KB) | **30.0x** | 0.5x* | 0.7x* |
| bigexample (2KB) | **24.9x** | 0.2x* | 0.3x* |
| Large (32KB) | **28.5x** | 5.2x | 3.5x |
| Very Large (323KB) | **28.2x** | **48.5x** | 6.4x |

*CLI tools have process spawn overhead (~3-4ms) which dominates for small inputs

## Key Observations

### 1. Rust Extension is the Best Choice for Python Users 🦀

The Rust extension (json2xml-rs) provides:
- **~28x faster** than pure Python consistently across all input sizes
- **Zero process overhead** - called directly from Python
- **Automatic fallback** - pure Python used if Rust unavailable
- **Easy install**: `pip install json2xml[fast]`

### 2. Go Excels for Large CLI Workloads 🚀

For very large inputs (323KB+):
- **48.5x faster** than Python
- But ~3-4ms startup overhead hurts small file performance
- Best for batch processing or large file conversions

### 3. Zig is Competitive but Has Trade-offs

- Consistent ~3ms startup overhead
- Good for medium-large files (3-6x faster than Python)
- Less optimized than Go for very large inputs

### 4. Process Spawn Overhead Matters

CLI tools (Go, Zig) have ~3-4ms process spawn overhead:
- Dominates for small inputs (makes them appear slower than Python!)
- Negligible for large inputs where actual work dominates
- Rust extension avoids this entirely by being a native Python module

## When to Use Each Implementation

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Python library calls | **Rust** (`pip install json2xml[fast]`) | 28x faster, no overhead |
| Small files via CLI | **Rust** via Python | CLI overhead dominates |
| Large files via CLI | **Go** (json2xml-go) | 48x faster for 300KB+ |
| Batch processing | **Go** or **Rust** | Both excellent |
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
# See: github.com/nicholasgriffintn/json2xml-zig
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
- **Zig version**: [github.com/nicholasgriffintn/json2xml-zig](https://github.com/nicholasgriffintn/json2xml-zig)
