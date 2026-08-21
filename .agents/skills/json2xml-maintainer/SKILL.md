---
name: json2xml-maintainer
description: Develop, test, review, or document the json2xml Python package and its optional Rust backend in this repository. Use for json2xml implementation, CLI, security, performance, release, and maintenance tasks.
---

# json2xml maintainer

Work from the repository root and treat `AGENTS.md`, `pyproject.toml`, the `Makefile`, and `lat.md/` as the current sources of truth. Preserve unrelated worktree changes.

## Ground the task

Before changing files:

1. Run `lat search` with the task's intent and read the relevant sections.
2. Run `lat expand` on the user's exact prompt so any `[[refs]]` resolve.
3. Inspect the affected implementation and tests before deciding the change.

If semantic search lacks a configured key, report the supported `LAT_LLM_KEY`, `LAT_LLM_KEY_FILE`, or `LAT_LLM_KEY_HELPER` options and use `lat locate` for direct lookups.

## Follow the execution paths

- Public library calls enter through `json2xml/json2xml.py` and serialize through `json2xml/dicttoxml_fast.py`.
- Pure-Python conversion rules live in `json2xml/dicttoxml.py`; input and URL safety live in `json2xml/utils.py`.
- CLI behavior lives in `json2xml/cli.py` and should preserve library semantics.
- Optional acceleration spans `json2xml/backend_selector.py`, `json2xml/dicttoxml_fast.py`, `json2xml_rs.pyi`, and `rust/`. Unsupported features must fall back without changing Python behavior.
- Observable behavior, architecture decisions, and anchored test intent belong in `lat.md/`.

Prefer narrow changes with regression tests. Preserve public Python behavior unless the user explicitly requests a breaking change, and check Python/Rust parity whenever backend selection or serialization changes.

## Validate proportionately

Use the locked repository environment instead of global Python tools.

- Focused Python test: `uv run --locked --extra dev pytest -o addopts='' <test-path> -vv`
- Python lint: `make lint`
- Python type check: `make typecheck`
- Full Python gate: `make check-all`
- Rust unit tests: `make test-rust`
- Rust formatting and lint when Rust changes: run `cargo fmt --check` and `cargo clippy --all-targets --all-features -- -D warnings` from `rust/`
- Python/Rust integration when the extension changes: build the local extension with the repository's Rust environment, then run `tests/test_rust_dicttoxml.py`

Choose focused checks while iterating, then run every gate affected by the final diff. Treat infrastructure or toolchain failures as blockers, not passing evidence.

For benchmark work, keep payloads deterministic, compare identical output bytes, isolate revisions, and interleave samples to reduce ordering bias. Record the interpreter, toolchain, machine, and exact command with results.

## Keep project knowledge synchronized

When functionality, architecture, tests, or behavior changes, update the relevant `lat.md/` section and place exactly one nearby `# @lat:` reference on each test that anchors a required test-spec leaf.

Before every final response, run `lat check`. Do not report the task complete until it passes, or clearly identify the unresolved validation blocker.

For reviews, establish an explicit commit, branch, tag, or merge base and verify that its diff to `HEAD` is nonempty. A clean `lat check` is repository-health evidence, not a substitute for reviewing a defined change set.


## MAINTAINENCE WORK

Check the existings PR to the repo. Merge those BRANCHES into a single branch
made from latest master and then create a PR and then merge that branch into
master using gh CLI.
