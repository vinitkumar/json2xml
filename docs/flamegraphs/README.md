# CPython 3.15 serializer flamegraphs

These profiles compare the pure-Python serializer before and after native JSON type fast paths on CPython 3.15.0b3.

The workload serializes a deterministic 5,000-record nested payload 20 times with type attributes enabled. Python 3.15's tracing profiler captured the call tree, and FlameProf rendered the SVGs.

| Profile | Traced time | Function calls | `isinstance` calls |
| --- | ---: | ---: | ---: |
| Before | 8.311 s | 48.17 million | 11.70 million |
| After | 5.782 s | 30.13 million | 2.80 million |

## Before

[![Serializer flamegraph before optimization](python315-before.svg)](python315-before.svg)

## After

[![Serializer flamegraph after optimization](python315-after.svg)](python315-after.svg)
