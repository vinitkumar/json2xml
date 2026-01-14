#!/bin/bash
#
# Benchmark script for json2xml-py vs json2xml-go
# Compares performance of Python and Go implementations
#
# Environment variables:
#   GO_CLI: Path to json2xml-go binary (default: json2xml-go in PATH)
#   MEDIUM_JSON_FILE: Path to medium JSON test file (default: ./examples/bigexample.json)
#

set -e

# Resolve repository-relative paths based on this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  json2xml Benchmark: Python vs Go${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration - can be overridden via environment variables
PYTHON_CLI="${PYTHON_CLI:-python -m json2xml.cli}"
GO_CLI="${GO_CLI:-json2xml-go}"
ITERATIONS=10
SMALL_JSON='{"name": "John", "age": 30, "city": "New York"}'
MEDIUM_JSON_FILE="${MEDIUM_JSON_FILE:-$SCRIPT_DIR/examples/bigexample.json}"
MEDIUM_JSON="$(cat "$MEDIUM_JSON_FILE")"
LARGE_JSON_FILE="/tmp/json2xml_benchmark_large.json"

# Generate a large JSON file for testing
generate_large_json() {
    echo -e "${YELLOW}Generating large JSON test file...${NC}"
    python3 << 'EOF'
import json
import random
import string

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))

data = []
for i in range(1000):
    item = {
        "id": i,
        "name": random_string(20),
        "email": f"{random_string(8)}@example.com",
        "active": random.choice([True, False]),
        "score": random.uniform(0, 100),
        "tags": [random_string(5) for _ in range(5)],
        "metadata": {
            "created": "2024-01-15T10:30:00Z",
            "updated": "2024-01-15T12:45:00Z",
            "version": random.randint(1, 100),
            "nested": {
                "level1": {
                    "level2": {
                        "value": random_string(10)
                    }
                }
            }
        }
    }
    data.append(item)

with open("/tmp/json2xml_benchmark_large.json", "w") as f:
    json.dump(data, f)

print(f"Generated large JSON with 1000 records")
EOF
}

# Benchmark function
benchmark() {
    local name="$1"
    local cmd="$2"
    local iterations="$3"
    
    echo -e "${YELLOW}Running: $name${NC}"
    
    # Warmup run
    eval "$cmd" > /dev/null 2>&1
    
    # Timed runs
    local total_time=0
    local times=()
    
    for ((i=1; i<=$iterations; i++)); do
        local start=$(python3 -c "import time; print(time.perf_counter())")
        eval "$cmd" > /dev/null 2>&1
        local end=$(python3 -c "import time; print(time.perf_counter())")
        local duration=$(python3 -c "print(round(($end - $start) * 1000, 2))")
        times+=($duration)
        total_time=$(python3 -c "print($total_time + $duration)")
    done
    
    # Calculate stats
    local avg=$(python3 -c "print(round($total_time / $iterations, 2))")
    local min=$(python3 -c "print(min([${times[*]}]))")
    local max=$(python3 -c "print(max([${times[*]}]))")
    
    echo "  Iterations: $iterations"
    echo "  Avg: ${avg}ms | Min: ${min}ms | Max: ${max}ms"
    echo ""
    
    # Return average time for comparison
    echo "$avg"
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

if [ ! -f "$GO_CLI" ]; then
    echo -e "${YELLOW}Building Go binary...${NC}"
    cd /Users/vinitkumar/projects/go/json2xml-go
    go build -o json2xml-go ./cmd/json2xml-go
fi

echo -e "${GREEN}✓ Prerequisites met${NC}"
echo ""

# Generate large test file
generate_large_json
echo ""

# Small JSON benchmark
echo -e "${BLUE}--- Small JSON (simple object) ---${NC}"
py_small=$(benchmark "Python (small)" "$PYTHON_CLI -s '$SMALL_JSON'" $ITERATIONS 2>&1 | tail -1)
go_small=$(benchmark "Go (small)" "$GO_CLI -s '$SMALL_JSON'" $ITERATIONS 2>&1 | tail -1)

# Medium JSON benchmark (using bigexample.json)
echo -e "${BLUE}--- Medium JSON (bigexample.json ~3KB) ---${NC}"
py_medium=$(benchmark "Python (medium)" "$PYTHON_CLI /Users/vinitkumar/projects/python/json2xml/examples/bigexample.json" $ITERATIONS 2>&1 | tail -1)
go_medium=$(benchmark "Go (medium)" "$GO_CLI /Users/vinitkumar/projects/go/json2xml-go/testdata/bigexample.json" $ITERATIONS 2>&1 | tail -1)

# Large JSON benchmark
echo -e "${BLUE}--- Large JSON (1000 records, ~250KB) ---${NC}"
py_large=$(benchmark "Python (large)" "$PYTHON_CLI $LARGE_JSON_FILE" $ITERATIONS 2>&1 | tail -1)
go_large=$(benchmark "Go (large)" "$GO_CLI $LARGE_JSON_FILE" $ITERATIONS 2>&1 | tail -1)

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}              SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

calculate_speedup() {
    python3 -c "
py = $1
go = $2
if go > 0:
    speedup = py / go
    print(f'{speedup:.1f}x faster')
else:
    print('N/A')
"
}

echo -e "${GREEN}Small JSON:${NC}"
echo "  Python: ${py_small}ms"
echo "  Go:     ${go_small}ms"
echo -e "  Go is $(calculate_speedup $py_small $go_small)"
echo ""

echo -e "${GREEN}Medium JSON:${NC}"
echo "  Python: ${py_medium}ms"
echo "  Go:     ${go_medium}ms"
echo -e "  Go is $(calculate_speedup $py_medium $go_medium)"
echo ""

echo -e "${GREEN}Large JSON:${NC}"
echo "  Python: ${py_large}ms"
echo "  Go:     ${go_large}ms"
echo -e "  Go is $(calculate_speedup $py_large $go_large)"
echo ""

# Cleanup
rm -f $LARGE_JSON_FILE

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Benchmark complete!${NC}"
echo -e "${BLUE}========================================${NC}"
