#!/usr/bin/env python3
"""Reproduce the public-wrapper benchmark for the security-hardening change."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

BEFORE = "before"
AFTER = "after"
DEFAULT_BEFORE_REVISION = "826439f"
DEFAULT_AFTER_REVISION = "48dfd38"
SAMPLES_PER_WORKER = 17
WARMUPS_PER_WORKER = 5
WORKERS_PER_REVISION = 4

# The mirrored order gives each revision every position in the four-process sequence.
WORKER_ORDERS = (
    (BEFORE, AFTER, AFTER, BEFORE),
    (AFTER, BEFORE, BEFORE, AFTER),
)

# (display name, number of records, conversions per timed sample)
CASES = (
    ("Small", 0, 1000),
    ("100 records", 100, 10),
    ("1,000 records", 1000, 1),
)
MODES = ("default", "compact", "pretty")


def make_payload(records: int) -> dict[str, Any] | list[dict[str, Any]]:
    """Return the exact deterministic payload used by every benchmark worker."""
    if records == 0:
        return {"name": "John", "age": 30, "city": "New York"}

    return [
        {
            "id": index,
            "name": f"customer-{index:08d}-" + "name" * 5,
            "email": f"user-{index:08d}@example.com",
            "active": index % 2 == 0,
            "score": (index % 10000) / 17.0,
            "tags": [f"tag-{index % 17}", f"region-{index % 23}", "xml-safe"],
            "metadata": {
                "created": "2026-08-12T10:30:00Z",
                "version": index % 101,
                "nested": {"level1": {"value": f"value-{index:08d}"}},
            },
        }
        for index in range(records)
    ]


def _mode_kwargs(mode: str) -> dict[str, Any]:
    if mode == "default":
        return {}
    if mode == "compact":
        return {"pretty": False}
    if mode == "pretty":
        return {"pretty": True}
    raise ValueError(f"unknown benchmark mode: {mode}")


def _worker(source: Path, mode: str, records: int, loops: int) -> None:
    os.chdir(source)
    sys.path.insert(0, str(source))

    from json2xml.json2xml import Json2xml

    payload = make_payload(records)
    kwargs = _mode_kwargs(mode)

    def convert() -> bytes | str | None:
        return Json2xml(payload, **kwargs).to_xml()

    for _ in range(WARMUPS_PER_WORKER):
        for _ in range(loops):
            convert()

    samples_ns: list[float] = []
    for _ in range(SAMPLES_PER_WORKER):
        started_ns = time.perf_counter_ns()
        for _ in range(loops):
            result = convert()
        samples_ns.append((time.perf_counter_ns() - started_ns) / loops)

    if result is None:
        raise RuntimeError("benchmark conversion unexpectedly returned None")
    encoded = result if isinstance(result, bytes) else result.encode("utf-8")
    print(
        json.dumps(
            {
                "samples_ns": samples_ns,
                "output": {
                    "type": type(result).__name__,
                    "utf8_bytes": len(encoded),
                    "sha256": hashlib.sha256(encoded).hexdigest(),
                },
            },
            sort_keys=True,
        )
    )


def _resolve_revision(repo: Path, revision: str) -> str:
    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{revision}^{{commit}}",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    return result.stdout.strip()


def _invoke_worker(
    script: Path,
    repo: Path,
    source: Path,
    mode: str,
    records: int,
    loops: int,
) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--worker",
            "--source",
            str(source),
            "--mode",
            mode,
            "--records",
            str(records),
            "--loops",
            str(loops),
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    return json.loads(result.stdout)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _summarize(samples_ns: list[float], output: dict[str, Any]) -> dict[str, Any]:
    return {
        "samples_ns": samples_ns,
        "median_ns": statistics.median(samples_ns),
        "p25_ns": _percentile(samples_ns, 0.25),
        "p75_ns": _percentile(samples_ns, 0.75),
        "output": output,
    }


def _benchmark_cell(
    script: Path,
    repo: Path,
    sources: dict[str, Path],
    workload: str,
    records: int,
    loops: int,
    mode: str,
) -> dict[str, Any]:
    samples: dict[str, list[float]] = {BEFORE: [], AFTER: []}
    outputs: dict[str, dict[str, Any]] = {}

    for order in WORKER_ORDERS:
        for label in order:
            worker_result = _invoke_worker(
                script, repo, sources[label], mode, records, loops
            )
            samples[label].extend(worker_result["samples_ns"])
            output = worker_result["output"]
            if label in outputs and output != outputs[label]:
                raise RuntimeError(f"{label} workers produced different output")
            outputs[label] = output

    before = _summarize(samples[BEFORE], outputs[BEFORE])
    after = _summarize(samples[AFTER], outputs[AFTER])
    if len(samples[BEFORE]) != 68 or len(samples[AFTER]) != 68:
        raise RuntimeError("benchmark schedule did not produce 68 samples per revision")

    change_percent = (
        (after["median_ns"] - before["median_ns"]) / before["median_ns"] * 100
    )
    return {
        "workload": workload,
        "records": records,
        "loops_per_sample": loops,
        "mode": mode,
        "workers_per_revision": WORKERS_PER_REVISION,
        "warmups_per_worker": WARMUPS_PER_WORKER,
        "samples_per_worker": SAMPLES_PER_WORKER,
        "before": before,
        "after": after,
        "change_percent": change_percent,
        "outputs_identical": outputs[BEFORE] == outputs[AFTER],
    }


def _format_duration(nanoseconds: float) -> str:
    if nanoseconds < 1000:
        return f"{nanoseconds:.1f}ns"
    if nanoseconds < 1_000_000:
        return f"{nanoseconds / 1000:.1f}us"
    return f"{nanoseconds / 1_000_000:.2f}ms"


def _print_report(report: dict[str, Any]) -> None:
    print(f"Python: {report['environment']['python'].splitlines()[0]}")
    print(f"Executable: {report['environment']['executable']}")
    print(f"Platform: {report['environment']['platform']}")
    print(
        "Revisions: "
        f"{report['revisions']['before']} (before) -> "
        f"{report['revisions']['after']} (after)"
    )
    print()
    print("| Workload | Mode | Before median [p25, p75] | After median [p25, p75] | Change |")
    print("|---|---|---:|---:|---:|")
    for cell in report["cells"]:
        before = cell["before"]
        after = cell["after"]
        print(
            f"| {cell['workload']} | {cell['mode']} | "
            f"{_format_duration(before['median_ns'])} "
            f"[{_format_duration(before['p25_ns'])}, {_format_duration(before['p75_ns'])}] | "
            f"{_format_duration(after['median_ns'])} "
            f"[{_format_duration(after['p25_ns'])}, {_format_duration(after['p75_ns'])}] | "
            f"{cell['change_percent']:+.1f}% |"
        )
    print()
    print("| Workload | Mode | Before type/bytes/SHA-256 | After type/bytes/SHA-256 | Identical |")
    print("|---|---|---|---|---:|")
    for cell in report["cells"]:
        before = cell["before"]["output"]
        after = cell["after"]["output"]
        print(
            f"| {cell['workload']} | {cell['mode']} | "
            f"{before['type']}/{before['utf8_bytes']}/{before['sha256']} | "
            f"{after['type']}/{after['utf8_bytes']}/{after['sha256']} | "
            f"{str(cell['outputs_identical']).lower()} |"
        )


def run_benchmark(before_revision: str, after_revision: str) -> dict[str, Any]:
    script = Path(__file__).resolve()
    repo_result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=script.parent,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    repo = Path(repo_result.stdout.strip())
    revisions = {
        BEFORE: _resolve_revision(repo, before_revision),
        AFTER: _resolve_revision(repo, after_revision),
    }

    with tempfile.TemporaryDirectory(prefix="json2xml-security-benchmark-") as temp:
        temp_path = Path(temp)
        sources = {BEFORE: temp_path / BEFORE, AFTER: temp_path / AFTER}
        added: list[Path] = []
        try:
            for label in (BEFORE, AFTER):
                subprocess.run(
                    [
                        "git",
                        "worktree",
                        "add",
                        "--detach",
                        str(sources[label]),
                        revisions[label],
                    ],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                    shell=False,
                )
                added.append(sources[label])

            cells = [
                _benchmark_cell(
                    script, repo, sources, workload, records, loops, mode
                )
                for workload, records, loops in CASES
                for mode in MODES
            ]
        finally:
            for source in reversed(added):
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(source)],
                    cwd=repo,
                    check=False,
                    capture_output=True,
                    text=True,
                    shell=False,
                )

    return {
        "schema_version": 1,
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
        },
        "revisions": {
            "before": revisions[BEFORE],
            "after": revisions[AFTER],
        },
        "schedule": {
            "orders": WORKER_ORDERS,
            "workers_per_revision": WORKERS_PER_REVISION,
            "warmups_per_worker": WARMUPS_PER_WORKER,
            "samples_per_worker": SAMPLES_PER_WORKER,
            "samples_per_revision_and_cell": WORKERS_PER_REVISION
            * SAMPLES_PER_WORKER,
        },
        "cells": cells,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", default=DEFAULT_BEFORE_REVISION)
    parser.add_argument("--after", default=DEFAULT_AFTER_REVISION)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--source", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--mode", choices=MODES, help=argparse.SUPPRESS)
    parser.add_argument("--records", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--loops", type=int, help=argparse.SUPPRESS)
    return parser


# @lat: [[architecture#Performance benchmarks]]
def main() -> None:
    args = _parser().parse_args()
    if args.worker:
        if args.source is None or args.mode is None or args.records is None or args.loops is None:
            raise SystemExit("worker mode requires source, mode, records, and loops")
        _worker(args.source, args.mode, args.records, args.loops)
        return

    report = run_benchmark(args.before, args.after)
    _print_report(report)
    if args.output_json is not None:
        args.output_json.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"\nRaw samples written to {args.output_json}")


if __name__ == "__main__":
    main()
