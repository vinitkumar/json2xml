from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

import benchmark_security_hardening as benchmark


# @lat: [[tests#Performance benchmarks#Security benchmark payloads stay deterministic]]
def test_security_benchmark_payloads_stay_deterministic() -> None:
    assert benchmark.make_payload(0) == {
        "name": "John",
        "age": 30,
        "city": "New York",
    }

    payload = benchmark.make_payload(2)

    assert isinstance(payload, list)
    assert payload == benchmark.make_payload(2)
    assert payload[1] == {
        "id": 1,
        "name": "customer-00000001-namenamenamenamename",
        "email": "user-00000001@example.com",
        "active": False,
        "score": 1 / 17.0,
        "tags": ["tag-1", "region-1", "xml-safe"],
        "metadata": {
            "created": "2026-08-12T10:30:00Z",
            "version": 1,
            "nested": {"level1": {"value": "value-00000001"}},
        },
    }


# @lat: [[tests#Performance benchmarks#Security benchmark schedule yields 68 samples]]
def test_security_benchmark_schedule_yields_68_balanced_samples() -> None:
    flattened_orders = [label for order in benchmark.WORKER_ORDERS for label in order]

    assert benchmark.WORKER_ORDERS == (
        (benchmark.BEFORE, benchmark.AFTER, benchmark.AFTER, benchmark.BEFORE),
        (benchmark.AFTER, benchmark.BEFORE, benchmark.BEFORE, benchmark.AFTER),
    )
    assert Counter(flattened_orders) == {benchmark.BEFORE: 4, benchmark.AFTER: 4}
    assert benchmark.WORKERS_PER_REVISION * benchmark.SAMPLES_PER_WORKER == 68


# @lat: [[tests#Performance benchmarks#Security benchmark covers every published cell]]
def test_security_benchmark_covers_every_published_cell() -> None:
    assert benchmark.CASES == (
        ("Small", 0, 1000),
        ("100 records", 100, 10),
        ("1,000 records", 1000, 1),
    )
    assert benchmark.MODES == ("default", "compact", "pretty")
    assert benchmark._mode_kwargs("default") == {}
    assert benchmark._mode_kwargs("compact") == {"pretty": False}
    assert benchmark._mode_kwargs("pretty") == {"pretty": True}


# @lat: [[tests#Performance benchmarks#Security benchmark subprocess commands stay structured]]
def test_security_benchmark_subprocess_commands_stay_structured() -> None:
    source = Path(benchmark.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    subprocess_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]

    assert subprocess_calls
    for call in subprocess_calls:
        assert call.args and isinstance(call.args[0], ast.List)
        shell_keyword = next((keyword for keyword in call.keywords if keyword.arg == "shell"), None)
        assert shell_keyword is not None
        assert isinstance(shell_keyword.value, ast.Constant)
        assert shell_keyword.value.value is False
