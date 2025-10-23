"""Benchmark script for comparing parallel vs serial performance."""
import sys
import time
from json2xml.json2xml import Json2xml
from json2xml.parallel import is_free_threaded


def generate_test_data(size: str) -> dict:
    """Generate test data of various sizes."""
    if size == "small":
        return {f"key{i}": f"value{i}" for i in range(10)}
    elif size == "medium":
        return {f"key{i}": {"nested": f"value{i}", "list": [1, 2, 3]} for i in range(100)}
    elif size == "large":
        return {
            "users": [
                {
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "active": i % 2 == 0,
                    "roles": ["admin", "user"] if i % 3 == 0 else ["user"],
                    "metadata": {
                        "created": "2024-01-01",
                        "updated": "2024-01-02",
                        "tags": [f"tag{j}" for j in range(5)]
                    }
                }
                for i in range(1000)
            ]
        }
    elif size == "xlarge":
        return {
            "data": [
                {
                    f"field{j}": f"value{i}_{j}"
                    for j in range(20)
                }
                for i in range(5000)
            ]
        }
    return {}


def benchmark_conversion(data: dict, parallel: bool, workers: int = 4, chunk_size: int = 100, iterations: int = 5) -> float:
    """Benchmark a single conversion configuration."""
    times = []
    
    for _ in range(iterations):
        converter = Json2xml(data, parallel=parallel, workers=workers, chunk_size=chunk_size)
        start = time.perf_counter()
        result = converter.to_xml()
        end = time.perf_counter()
        times.append(end - start)
    
    return sum(times) / len(times)


def run_benchmarks():
    """Run comprehensive benchmarks."""
    print("=" * 80)
    print("json2xml Performance Benchmark")
    print("=" * 80)
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Free-threaded: {'Yes' if is_free_threaded() else 'No'}")
    gil_status = "Disabled (Free-threaded)" if is_free_threaded() else "Enabled (Standard GIL)"
    print(f"GIL Status: {gil_status}")
    print("=" * 80)
    print()
    
    sizes = ["small", "medium", "large", "xlarge"]
    
    for size in sizes:
        print(f"\n{size.upper()} Dataset:")
        print("-" * 80)
        
        data = generate_test_data(size)
        
        # Count items
        if "users" in data:
            item_count = len(data["users"])
        elif "data" in data:
            item_count = len(data["data"])
        else:
            item_count = len(data)
        print(f"Items: {item_count}")
        
        # Serial benchmark
        serial_time = benchmark_conversion(data, parallel=False)
        print(f"Serial:     {serial_time*1000:.2f} ms")
        
        # Parallel benchmarks with different worker counts
        for workers in [2, 4, 8]:
            parallel_time = benchmark_conversion(data, parallel=True, workers=workers, chunk_size=100)
            speedup = serial_time / parallel_time
            print(f"Parallel ({workers}w): {parallel_time*1000:.2f} ms (speedup: {speedup:.2f}x)")
        
        print()
    
    print("=" * 80)
    print("Benchmark complete!")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmarks()
