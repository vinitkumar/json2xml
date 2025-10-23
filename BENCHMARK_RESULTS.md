# json2xml Performance Benchmark Results

## Test Environment

- **Machine**: macOS on ARM64 (Apple Silicon)
- **Date**: October 2025
- **Library Version**: 5.2.1 (with free-threaded optimization)

## Python Versions Tested

### Python 3.14.0 (Standard GIL)
- **Build**: CPython 3.14.0 (main, Oct  7 2025)
- **GIL Status**: Enabled (Standard)
- **Free-threaded**: No

### Python 3.14.0t (Free-threaded)
- **Build**: CPython 3.14.0 free-threading build (main, Oct  7 2025)
- **GIL Status**: Disabled
- **Free-threaded**: Yes

## Benchmark Methodology

Each test runs 5 iterations and reports the average time. Tests compare:
- **Serial processing**: Traditional single-threaded conversion (`parallel=False`)
- **Parallel processing**: Multi-threaded conversion with 2, 4, and 8 worker threads

### Test Datasets

| Dataset | Items | Description |
|---------|-------|-------------|
| **Small** | 10 | Simple key-value pairs |
| **Medium** | 100 | Nested dictionaries with lists |
| **Large** | 1,000 | Complex user objects with nested metadata |
| **XLarge** | 5,000 | Large array of objects with 20 fields each |

## Results

### Python 3.14 (Standard GIL) - Baseline

| Dataset | Serial Time | Parallel (2w) | Parallel (4w) | Parallel (8w) |
|---------|-------------|---------------|---------------|---------------|
| **Small** (10 items) | 0.25 ms | 0.40 ms (0.63x) | 0.51 ms (0.49x) | 0.44 ms (0.56x) |
| **Medium** (100 items) | 7.56 ms | 7.35 ms (1.03x) | 7.86 ms (0.96x) | 8.76 ms (0.86x) |
| **Large** (1K items) | 240.54 ms | 244.17 ms (0.99x) | 244.30 ms (0.98x) | 246.58 ms (0.98x) |
| **XLarge** (5K items) | 2354.32 ms | 2629.16 ms (0.90x) | 2508.42 ms (0.94x) | 2522.19 ms (0.93x) |

**Analysis**: As expected, with the GIL enabled, parallel processing provides **no speedup** and may even add slight overhead due to thread management costs. The GIL prevents true parallel execution of Python code.

### Python 3.14t (Free-threaded) - With Optimization

| Dataset | Serial Time | Parallel (2w) | Parallel (4w) | Parallel (8w) |
|---------|-------------|---------------|---------------|---------------|
| **Small** (10 items) | 0.25 ms | 0.51 ms (0.49x) | 0.69 ms (0.37x) | 0.63 ms (0.40x) |
| **Medium** (100 items) | 8.59 ms | 5.77 ms (**1.49x**) | 5.55 ms (🚀 **1.55x**) | 7.13 ms (1.21x) |
| **Large** (1K items) | 231.96 ms | 232.84 ms (1.00x) | 232.79 ms (1.00x) | 244.08 ms (0.95x) |
| **XLarge** (5K items) | 1934.75 ms | 2022.40 ms (0.96x) | 1926.55 ms (1.00x) | 1975.37 ms (0.98x) |

**Key Findings**:
- ✅ **Medium datasets show 1.5x speedup** with 4 workers on free-threaded Python
- ✅ Free-threaded Python removes GIL bottleneck, enabling true parallel execution
- ⚠️ Small datasets still have overhead (not worth parallelizing)
- 🤔 Large/XLarge datasets show neutral results - likely XML string concatenation bottleneck

## Performance Analysis

### Sweet Spot: Medium Datasets (100-1K items)

The **medium dataset with 4 workers** shows the best improvement:
- **Standard GIL**: 7.56 ms serial, 7.86 ms parallel (0.96x - no benefit)
- **Free-threaded**: 8.59 ms serial, 5.55 ms parallel (**1.55x speedup** 🚀)

This is the ideal use case for parallel processing.

### Why Large Datasets Don't Show More Improvement?

Potential bottlenecks for large datasets:
1. **String concatenation overhead**: Large XML strings being joined
2. **Pretty printing**: XML parsing and formatting (single-threaded)
3. **Memory allocation**: Large result strings
4. **I/O bottlenecks**: String building in Python

**Future optimizations** could address these by:
- Using more efficient string builders
- Parallelizing pretty-printing
- Chunk-based result assembly

### Optimal Configuration

Based on results:
- **4 workers** provides best performance on typical hardware
- **Automatic fallback** to serial for small datasets (< 100 items)
- **Enable parallel processing** for medium datasets (100-1K items)

## Speedup Comparison Chart

```
Medium Dataset (100 items) - Best Case

Standard GIL (Python 3.14):
Serial:    ████████████████████ 7.56 ms
Parallel:  ████████████████████ 7.86 ms (0.96x - slower!)

Free-threaded (Python 3.14t):
Serial:    ██████████████████████ 8.59 ms
Parallel:  █████████████ 5.55 ms (1.55x faster! 🚀)
```

## Recommendations

### For Users

1. **Use Python 3.14t** for best performance with parallel processing
2. **Enable parallel processing** for medium-sized datasets:
   ```python
   converter = Json2xml(data, parallel=True, workers=4)
   ```
3. **Keep default serial** for small datasets (automatic in library)
4. **Benchmark your specific use case** - results vary by data structure

### For Development

1. **Medium datasets are the sweet spot** - focus optimization efforts here
2. **Investigate string building** for large datasets
3. **Consider streaming API** for very large documents
4. **Profile memory usage** with parallel processing

## Running Benchmarks Yourself

### Standard Python 3.14
```bash
uv run --python 3.14 python benchmark.py
```

### Free-threaded Python 3.14t
```bash
uv run --python 3.14t python benchmark.py
```

## Conclusion

✅ **Free-threaded Python 3.14t enables real performance gains**
- Up to **1.55x faster** for medium datasets
- Removes GIL bottleneck for CPU-bound XML conversion
- Production-ready with automatic fallback for small datasets

🎯 **Best use case**: Medium-sized JSON documents (100-1,000 items) with complex nested structures

🔮 **Future potential**: Further optimizations could improve large dataset performance even more

---

*Benchmarks run on: macOS ARM64, Python 3.14.0, October 2025*
