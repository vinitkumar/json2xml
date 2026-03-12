# json2xml Benchmark Results

Comprehensive performance comparison between all json2xml implementations.

## Test Environment

- **Machine**: Apple Silicon (M-series, aarch64)
- **OS**: macOS
- **Date**: March 12, 2026

### Implementations Tested

| Implementation | Type | Notes |
|----------------|------|-------|
| Python | Library | Pure Python (json2xml) |
| Rust | Library | Native extension via PyO3 (json2xml-rs) |
| Go | CLI | Standalone binary (json2xml-go v1.0.0) |
| Zig | CLI | Standalone binary (json2xml-zig) |

## Test Data

| Size | Description | Bytes |
|------|-------------|-------|
| Small | Simple object `{"name": "John", "age": 30, "city": "New York"}` | 47 |
| Medium | 10 generated records with nested structures | ~3,211 |
| bigexample.json | Real-world patent data | 2,018 |
| Large | 100 generated records with nested structures | ~32,220 |
| Very Large | 1,000 generated records with nested structures | ~323,114 |

## Results

### Performance Summary

| Test Case | Python | Rust | Go | Zig |
|-----------|--------|------|-----|-----|
| Small (47B) | 78.39µs | 1.05µs | 4.31ms | 1.96ms |
| Medium (3.2KB) | 2.15ms | 15.47µs | 5.03ms | 2.34ms |
| bigexample (2KB) | 862.12µs | 6.44µs | 4.47ms | 2.38ms |
| Large (32KB) | 22.08ms | 150.91µs | 4.80ms | 2.89ms |
| Very Large (323KB) | 218.63ms | 1.47ms | 4.75ms | 5.38ms |

### Speedup vs Pure Python

| Test Case | Rust | Go | Zig |
|-----------|------|-----|-----|
| Small (47B) | **74.9x** | 0.0x* | 0.0x* |
| Medium (3.2KB) | **139.1x** | 0.4x* | 0.9x* |
| bigexample (2KB) | **133.9x** | 0.2x* | 0.4x* |
| Large (32KB) | **146.3x** | 4.6x | **7.6x** |
| Very Large (323KB) | **149.2x** | **46.1x** | **40.6x** |

*CLI tools have process spawn overhead (~2-4ms) which dominates for small inputs

## Key Observations

### 1. Rust Extension is the Best Choice for Python Users 🦀

The Rust extension (json2xml-rs) provides:
- **~75-149x faster** than pure Python consistently across all input sizes
- **Zero process overhead** - called directly from Python
- **Automatic fallback** - pure Python used if Rust unavailable
- **Easy install**: `pip install json2xml[fast]`

### 2. Go Excels for Very Large CLI Workloads 🚀

For very large inputs (323KB+):
- **46.1x faster** than Python
- But ~4ms startup overhead hurts small file performance
- Best for batch processing or large file conversions

### 3. Zig is Now Highly Competitive ⚡

After recent optimizations:
- **40.6x faster** than Python for very large files
- **7.6x faster** for large files (32KB)
- Faster startup than Go (~2ms vs ~4ms)
- Best balance of startup time and throughput

### 4. Process Spawn Overhead Matters

CLI tools (Go, Zig) have process spawn overhead:
- Go: ~4ms startup overhead
- Zig: ~2ms startup overhead
- Dominates for small inputs (makes them appear slower than Python!)
- Negligible for large inputs where actual work dominates
- Rust extension avoids this entirely by being a native Python module

## When to Use Each Implementation

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Python library calls | **Rust** (`pip install json2xml[fast]`) | 75-149x faster, no overhead |
| Small files via CLI | **Zig** (json2xml-zig) | Fastest startup (~2ms) |
| Large files via CLI | **Go** or **Zig** | Both excellent (Go slightly faster) |
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
