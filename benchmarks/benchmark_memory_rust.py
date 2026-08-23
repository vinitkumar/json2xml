#!/usr/bin/env python3
"""Measure peak RSS for the Rust json2xml extension on a large payload."""
from __future__ import annotations

import argparse
import gc
import json
import platform
import resource
import sys
import time
from typing import Any

from json2xml_rs import dicttoxml


def max_rss_bytes() -> int:
    """Return current process max RSS in bytes on macOS/Linux."""
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(value)
    return int(value) * 1024


def make_payload(records: int) -> list[dict[str, Any]]:
    """Build deterministic nested data that stays on the Rust fast path."""
    payload: list[dict[str, Any]] = []
    for i in range(records):
        suffix = f"{i:08d}"
        payload.append(
            {
                "id": i,
                "name": f"customer-{suffix}-" + ("name" * 8),
                "email": f"user-{suffix}@example.com",
                "active": i % 2 == 0,
                "score": (i % 10_000) / 17.0,
                "tags": [
                    f"tag-{i % 17}",
                    f"region-{i % 23}",
                    f"cohort-{i % 31}",
                    "xml-safe",
                    "memory-benchmark",
                ],
                "metadata": {
                    "created": "2026-06-05T10:30:00Z",
                    "updated": "2026-06-05T12:45:00Z",
                    "version": i % 101,
                    "nested": {
                        "level1": {
                            "level2": {
                                "value": f"value-{suffix}-" + ("payload" * 6),
                                "checksum": f"{(i * 2654435761) & 0xFFFFFFFF:08x}",
                            }
                        }
                    },
                },
            }
        )
    return payload


def mib(value: int) -> float:
    return value / (1024 * 1024)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=100_000)
    parser.add_argument("--label", default="unknown")
    args = parser.parse_args()

    # Load and initialize the extension before the baseline payload RSS.
    dicttoxml([{"warmup": "ok"}], attr_type=True)

    payload = make_payload(args.records)
    gc.collect()
    baseline_rss = max_rss_bytes()

    start = time.perf_counter()
    xml = dicttoxml(payload, attr_type=True)
    elapsed = time.perf_counter() - start
    peak_rss = max_rss_bytes()

    result = {
        "label": args.label,
        "records": args.records,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "baseline_rss_mib": round(mib(baseline_rss), 2),
        "peak_rss_mib": round(mib(peak_rss), 2),
        "serializer_delta_mib": round(mib(max(0, peak_rss - baseline_rss)), 2),
        "xml_size_mib": round(mib(len(xml)), 2),
        "elapsed_seconds": round(elapsed, 3),
        "output_type": type(xml).__name__,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
