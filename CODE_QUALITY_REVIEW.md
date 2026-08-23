# json2xml — Code Quality Review

**Date:** 2026-08-23
**Commit reviewed:** `ecfb1a4` (master, clean tree)
**Version:** 6.5.1

---

## Status: all findings addressed

This document is kept as the record of what the review found and why each change was
made. It describes the code as it was at `ecfb1a4`; the findings below no longer
reproduce.

| # | Finding | Resolution |
|---|---|---|
| 1 | `pytest.ini` disables the pyproject pytest config | `af16bb6` |
| 2 | Budget estimator rejects valid inputs | `af16bb6` |
| 3 | Triplicated type-dispatch ladder | `78ea9ea` |
| 4 | Five dead public wrappers | `c90daab` — kept, documented as a compatibility surface |
| 5 | `key_is_valid_xml_attr` has no fast path | `af16bb6` |
| 6 | Public converters mutate caller `attr` | `af16bb6` |
| 7 | Falsy unknown objects become `null` | `af16bb6` |
| 8 | `_pretty_xml` re-parses generated XML | `3e93994` |
| 9 | Pre-commit config contradicts the toolchain | `af16bb6`, `b158159`, `7b29472` |
| 10 | Repo root and documentation accumulation | `af16bb6` |
| 11 | Rust CI path filter gap | `af16bb6` |
| 12 | Dependencies declared in three places | `af16bb6` |

Follow-on work the review did not cover, found while acting on it:

- The Rust backend produced different XML from the Python serializer for payloads the
  selector routed to it — CDATA on numbers, nested list shapes, list member tag names,
  `type="dict"` under `list_headers`, and names beginning with `xml`. Fixed in `a650ccf`,
  with the payload gate made native in `977dc5b`.
- A rootless list of dictionaries under `list_headers` emitted the malformed empty tag
  `<>`. Fixed in `405ef94`.

---

## Verification baseline

All checks below were run locally against the reviewed commit and **passed**:

| Check | Command | Result |
|---|---|---|
| Tests | `.venv/bin/python -m pytest -q` | 420 passed, 102 skipped (Rust ext not installed) |
| Coverage | `pytest --cov=json2xml --cov-report=term` | **100%** on all 8 modules (1040 stmts, 0 missed) |
| Lint | `uvx ruff check json2xml tests` | All checks passed |
| Types | `uvx ty check json2xml tests` | All checks passed |

---

## Overall: B+ / strong

CI spans 9 Python versions x 4 OSes with SHA-pinned actions, CodeQL, Rust fuzz targets, and
real Python-vs-Rust differential parity tests (`tests/test_rust_dicttoxml.py::TestRustVsPythonCompatibility`).
That is well above the median PyPI library.

The weaknesses are concentrated in the core serializer's internal structure and in repo/config
hygiene — **not** in correctness or process.

| Dimension | Grade | Note |
|---|---|---|
| Test & CI infrastructure | A | 100% coverage enforced, broad matrix, fuzzing, parity tests |
| Security posture | A− | SSRF guards, decompression-bomb limits, XML 1.0 char validation, `defusedxml` |
| Type safety & lint | A | Both `ruff` and `ty` clean; thorough annotations |
| Core serializer design | C+ | 1408-line module, triplicated dispatch, dead public API |
| Public API consistency | C | Mutating helpers, two type vocabularies, silent-null path |
| Repo & config hygiene | C− | Duplicate pytest config that silently kills coverage; stale toolchain |

---

## Findings, highest value first

Items marked **[verified]** were reproduced locally; the reproduction command is included.

---

### 1. `pytest.ini` silently disables the `pyproject.toml` pytest config — [verified]

**Files:** `pytest.ini:1`, `pyproject.toml` (`[tool.pytest.ini_options]`), `setup.cfg`

Both `pytest.ini` and `pyproject.toml [tool.pytest.ini_options]` exist. pytest reads exactly
**one** ini source, and `pytest.ini` wins — so `testpaths`, `python_files`, and the `--cov`
`addopts` declared in `pyproject.toml` are **dead config**.

Reproduce:

```bash
.venv/bin/python -m pytest -q          # no coverage table at all
.venv/bin/python -m pytest -q --cov=json2xml --cov-report=term   # only now does coverage appear
```

CI happens to pass `--cov` flags explicitly on the command line, so this has been invisible.
Anyone running bare `pytest` locally silently gets no coverage enforcement.

**Fix:** delete `pytest.ini`, moving `log_cli`/`log_cli_level` into `pyproject.toml`.
Do the same for the `[flake8]` section in `setup.cfg` — flake8 is not used anywhere
(ruff replaced it). Keep `[coverage:run] relative_files = True` or move it to pyproject.

**Effort:** ~10 minutes. **Risk:** low.

---

### 2. The conversion budget estimator rejects valid inputs — [verified]

**File:** `json2xml/json2xml.py:19` (`_validate_conversion_budget`)

The estimator predicts output size with fixed constants (256 B per dict entry, 128 B per list
item, 6x value length). It over-estimates badly enough to refuse legitimate payloads.

Reproduce:

```bash
.venv/bin/python -c "
from json2xml.json2xml import Json2xml
from json2xml.dicttoxml_fast import dicttoxml
data = {'nums': list(range(60000))}
print('real output bytes:', len(dicttoxml(data)))
try:
    Json2xml(data).to_xml(); print('accepted')
except Exception as e:
    print('REJECTED:', type(e).__name__, e)
"
```

Output:

```
real output bytes: 1728967
REJECTED: InvalidDataError XML output size limit exceeded
```

A payload producing **1.7 MB** is refused against a **10 MB** default limit — roughly a **6x
over-estimate**. It is also a second full traversal of the data before conversion even starts,
so it costs time as well as false negatives.

**Fix:** drop the pre-walk size estimate entirely and enforce the byte limit *incrementally
inside `_XMLWriter.write`* (`json2xml/dicttoxml.py:22`), raising the moment real output crosses
the threshold. Keep the pre-walk only for `max_depth` and `max_items`, which it measures
**exactly** and cheaply. Net effect: faster *and* accurate.

Note the same limit is checked again after the fact at `json2xml/json2xml.py` in `to_xml()`
(`len(xml_data) > self.max_output_bytes`), so the accurate enforcement already exists — the
estimator is the only thing producing false rejections.

**Effort:** ~1-2 hours including tests. **Risk:** medium (changes rejection behavior — but
strictly in the direction of accepting things that were wrongly refused).

---

### 3. Collapse the triplicated type-dispatch ladder

**File:** `json2xml/dicttoxml.py`

| Function | Line | Lines | `if`/`elif` branches |
|---|---|---|---|
| `_append_convert` | 524 | 91 | 10 |
| `_append_rawitem` | 690 | 46 | 5 |
| `_append_convert_dict` | 785 | 100 | 9 |
| `_append_convert_list` | 885 | 135 | 16 |

That is ~370 lines and **40 branches** encoding the same type ordering four separate times:
exact-type fast path (`bool` → `str` → `int`/`float`/`complex` → `dict` → `list`/`tuple`), then
an `isinstance` fallback for subclasses, then `isoformat` for dates, then `TypeError`.

Adding or changing a supported type means four correct edits. Missing one is a silent behavior
divergence that the current tests would not necessarily catch.

**Fix:** introduce one classifier:

```python
def _classify(value: Any) -> Kind:
    """Exact-type dict lookup first, isinstance ladder as fallback."""
```

Then each `_append_*` becomes a small dispatch on `Kind`. The exact-type fast path (the reason
the ladder is written this way — see the comment at `dicttoxml.py:530`) is preserved by making
the first step a `type(value)` dict lookup, which is as fast as the current chain of
`is` comparisons.

This is the single highest-leverage maintainability change in the file.

**Effort:** ~half a day. **Risk:** medium — but 100% coverage plus the Rust parity tests make
this unusually safe to refactor.

---

### 4. Five public functions are dead code kept alive only by tests

**File:** `json2xml/dicttoxml.py`

| Function | Line |
|---|---|
| `convert` | 384 |
| `dict2xml_str` | 415 |
| `list2xml_str` | 447 |
| `convert_dict` | 472 |
| `convert_list` | 498 |

Each is a thin wrapper that calls the corresponding `_append_*` and decodes to `str`.

Reproduce:

```bash
grep -n "\bconvert(\|dict2xml_str(\|list2xml_str(\|convert_dict(\|convert_list(" json2xml/*.py | grep -v "_append"
grep -rn "dict2xml_str\|list2xml_str\|convert_dict\|convert_list" tests/
```

**No production code path calls any of them** — the only callers are `tests/test_dict2xml.py`.
They exist to satisfy the 100% coverage gate. That is ~145 lines of public API surface being
maintained for zero internal callers.

**Fix:** decide explicitly. If they are a back-compat promise for downstream users, document
that in each docstring and attach a `DeprecationWarning` naming a removal version. If not,
delete them along with the tests that exist only to cover them.

**Effort:** ~1 hour. **Risk:** low (deprecation path) / medium (deletion — it is public API).

---

### 5. `key_is_valid_xml_attr` has no fast path — [verified]

**File:** `json2xml/dicttoxml.py:242`

`key_is_valid_xml` (`:215`) short-circuits through `_is_fast_valid_xml_name` (`:204`).
`key_is_valid_xml_attr` does **not**, so every uncached attribute name spins up a full
`defusedxml.minidom` DOM parse.

Reproduce:

```bash
.venv/bin/python -c "
import timeit
from json2xml import dicttoxml as d
print('attr validate (uncached):', timeit.timeit(lambda: d.key_is_valid_xml_attr.__wrapped__('name'), number=2000))
print('elem validate (fast path):', timeit.timeit(lambda: d.key_is_valid_xml.__wrapped__('name'), number=2000))
"
```

Output (2000 iterations):

```
attr validate (uncached): 0.0262 s   ->  13.1 us/call
elem validate (fast path): 0.0006 s  ->   0.29 us/call
```

**45x slower.** This is on the `ids=` and `@attrs` code paths.

**Fix:** reuse `_is_fast_valid_xml_name` as the first check in `key_is_valid_xml_attr` (an XML
attribute name and an element name share the same `Name` production, so the fast path is
directly applicable).

Separately: both caches are `lru_cache(maxsize=4096)` keyed on **caller-supplied** strings.
That bound is the right call as anti-DoS, but it deserves a one-line comment saying so —
otherwise a future reader may "optimize" it to unbounded.

**Effort:** ~20 minutes. **Risk:** low.

---

### 6. Public converters mutate their caller's `attr` dict — [verified]

**File:** `json2xml/dicttoxml.py:1020` (`convert_kv`), `:1057` (`convert_bool`), `:1082` (`convert_none`)

Reproduce:

```bash
.venv/bin/python -c "
from json2xml.dicttoxml import convert_kv, convert_bool, convert_none
a = {'id': 'x'}; convert_kv('k', 'v', True, a); print('convert_kv   ->', a)
b = {'id': 'y'}; convert_bool('k', True, True, b); print('convert_bool ->', b)
c = {}; convert_none('123bad', True, c); print('convert_none ->', c)
"
```

Output:

```
convert_kv   -> {'id': 'x', 'type': 'str'}
convert_bool -> {'id': 'y', 'type': 'bool'}
convert_none -> {'name': '123bad', 'type': 'null'}
```

The mutation happens via `make_valid_xml_name(key, attr)` (`:264`, which does `attr["name"] = key`)
and the subsequent `attr["type"] = ...`.

Notably, `make_typed_attrstring` (`:196`) was clearly added to fix exactly this class of bug —
its docstring says "without mutating caller attrs" — and the `*_valid_name` variants
(`:1042`, `:1071`, `:1096`) correctly use it. The fix was just never applied to the three
legacy public entry points.

**Fix:** `attr = dict(attr) if attr else {}` at the top of each of the three functions.

**Effort:** ~20 minutes. **Risk:** low.

---

### 7. Falsy unknown objects silently become `null` — [verified]

**File:** `json2xml/dicttoxml.py:785` (`_append_convert_dict`, final `elif not val:` branch)

The catch-all `elif not val:` swallows *any* falsy object into a `null` element, while the
identical type with truthy contents raises.

Reproduce:

```bash
.venv/bin/python -c "
from json2xml.dicttoxml import dicttoxml
class Empty:
    def __len__(self): return 0
class Full:
    def __len__(self): return 1
print(dicttoxml({'a': Empty()}))
try:
    print(dicttoxml({'a': Full()}))
except TypeError as e:
    print('TypeError:', e)
"
```

Output:

```
b'<?xml version="1.0" encoding="UTF-8" ?><root><a type="null"></a></root>'
TypeError: Unsupported data type: <__main__.Full object at 0x...> (Full)
```

Same class, opposite outcomes, decided by truthiness. Data loss in the falsy case.

**Fix:** restrict that branch to `val is None` (plus genuinely empty `dict`/`Sequence` if that
behavior is intended and tested), and let everything else fall through to the `TypeError`.

**Effort:** ~30 minutes. **Risk:** low-medium (could change behavior for someone relying on the
accident — worth a HISTORY.rst note).

---

### 8. `_pretty_xml` re-parses XML the library just generated

**File:** `json2xml/json2xml.py:47`

~90 lines of hand-rolled tokenizer handling CDATA sections, comments, quoted attribute values,
and tag-balance tracking — parsing output that the serializer produced two function calls
earlier. Every `InvalidDataError("Malformed XML generated")` in it is an internal invariant
leaking to users as a *data* error.

It is also a genuine parser-shaped attack surface in a library whose whole security posture is
built on *not* parsing untrusted XML.

**Fix:** thread an `indent: int | None` parameter through `_XMLWriter` and the `_append_*`
functions, emitting indentation at generation time. That deletes the tokenizer entirely,
removes the attack surface, and makes `pretty=True` nearly free instead of a second full pass.

**Effort:** ~half a day. **Risk:** medium — but pretty-print output is well covered by existing
tests, so divergences will surface immediately.

---

### 9. Pre-commit config contradicts the actual toolchain

**File:** `.pre-commit-config.yaml`

| Hook configured | Problem |
|---|---|
| `black` | No `ruff format` configured; two formatters is one too many |
| `isort` | Duplicates ruff's `I` rule, already enabled in `pyproject.toml` |
| `mypy` + `django-stubs==5.0.4` | CI type-checks with **ty**, not mypy. And there is no Django anywhere in this project — pure copy-paste leftover |
| `pyupgrade --py38-plus` | `requires-python = ">=3.10"` |
| `tox-ini-fmt` | **No `tox.ini` exists** (`ls tox.ini` → not found) |

Related: `AGENT.md` tells contributors to run `tox` for multi-version testing, which cannot work.

**Fix:** reduce the config to `ruff check --fix`, `ruff format`, the `pre-commit-hooks` basics
(`check-json`/`check-toml`/`check-merge-conflict`/`end-of-file-fixer`/`trailing-whitespace`),
and `rstcheck`. Drop black, isort, mypy, django-stubs, and tox-ini-fmt. Bump pyupgrade to
`--py310-plus`. Fix or remove the `tox` line in `AGENT.md`.

**Effort:** ~30 minutes. **Risk:** low. Note that dropping black in favor of `ruff format` will
produce a one-time reformat diff — do it as its own commit.

---

### 10. Repo root and documentation have accumulated

- **Nine benchmark entrypoints at top level:** `benchmark.py`, `benchmark.sh`, `benchmark_all.py`,
  `benchmark_memory_rust.py`, `benchmark_multi_python.py`, `benchmark_rust.py`,
  `benchmark_security_hardening.py`, `benchmark_utils.py`.
  → Move to a `benchmarks/` directory. Update `.github/workflows/rust-ci.yml` (which runs
  `python benchmark_rust.py`) accordingly.
- **`dev.py`** re-implements `make lint` / `make test` / `make typecheck`, slightly differently
  (it runs bare `ruff`/`pytest` rather than the locked `uv run --locked --extra dev`).
  → Delete it; the `Makefile` is the entrypoint.
- **`plan.md`** is a committed scratch prompt about a Python 3.14 free-threaded CI task.
  → Delete.
- **`AGENT.md` and `AGENTS.md`** give overlapping, partly contradictory instructions.
  → Merge into `AGENTS.md` (the conventional filename).
- **`Makefile` release targets** (`dist`, `install`, `release-to-pypi`) still shell out to
  deprecated `python setup.py sdist` / `bdist_wheel` / `install` despite a complete
  pyproject + uv setup.
  → Replace with `uv build` and `uv publish`.

**Effort:** ~1-2 hours. **Risk:** low, but touches CI — verify `rust-ci.yml` after moving benchmarks.

---

### 11. Rust CI path filter has a coverage gap

**File:** `.github/workflows/rust-ci.yml:5-24`

The workflow triggers only on changes to four named `json2xml/*.py` files, `rust/**`, and
`tests/test_rust_dicttoxml.py`. A **new** test file exercising conversion behavior would never
run against the Rust backend, and changes to `json2xml/utils.py` or `json2xml/cli.py` do not
trigger it either.

The `rust-test` job does run the full suite (`pytest tests/ --ignore=tests/test_cli.py`) once
triggered, so the machinery is there — only the trigger is too narrow.

**Fix:** add `tests/**` to both the `push` and `pull_request` path filters.

**Effort:** ~5 minutes. **Risk:** none (only widens coverage; costs some CI minutes).

---

### 12. Dependencies are declared in three places and already drifting

- `pyproject.toml` — `[project.dependencies]` (unpinned) and `[project.optional-dependencies]`
- `requirements.in` / `requirements.txt` — pinned `==`
- `requirements-dev.in` / `requirements-dev.txt`

Observed drift:

- `xmltodict>=0.12.0` in the pyproject `dev` extra vs `xmltodict>=0.14.2` in `requirements-dev.in`
- `ruff` and `pytest-xdist` appear in `requirements-dev.in` but **not** in the pyproject `dev`
  extra, even though `make lint` runs `uv run --locked --extra dev ruff` (this currently resolves
  via `uv.lock`, so it works — but the declaration is missing)

**Fix:** make `pyproject.toml` + `uv.lock` the single source of truth. Generate the
`requirements*.txt` files from it if downstream consumers need them, or drop them.

**Effort:** ~1 hour. **Risk:** low-medium (touches the install path — verify CI after).

---

## Suggested order of work

**Quick wins (half a day total, all low risk):**

1. #1 — delete `pytest.ini`, clean `setup.cfg`
2. #5 — fast path for `key_is_valid_xml_attr`
3. #6 — stop mutating caller `attr` dicts
4. #11 — widen the Rust CI path filter
5. #9 — prune `.pre-commit-config.yaml`

**Real bugs (do next):**

6. #2 — replace the budget estimator with incremental enforcement
7. #7 — stop swallowing falsy objects into `null`

**Structural investment (highest long-term payoff):**

8. #3 — collapse the dispatch ladder
9. #8 — pretty-print at generation time, delete the tokenizer
10. #4 — decide the fate of the five dead public wrappers

**Hygiene (whenever):**

11. #10 — repo root and docs
12. #12 — dependency declaration consolidation

---

## What is genuinely good here — do not regress it

- **100% enforced line coverage** with `--cov-fail-under=100` in CI.
- **Serious security work in `json2xml/utils.py`**: SSRF protection via pre-resolution address
  validation and `redirect=False`, decompression-bomb limits with both encoded and decoded byte
  caps, `Content-Length` cross-checking, credential rejection, and IDNA handling.
- **XML 1.0 character validation** (`dicttoxml.py:120`, `_validate_xml_chars`) with a fast
  `isprintable()` path — correct *and* fast.
- **Genuine Python-vs-Rust differential testing** (`TestRustVsPythonCompatibility`), plus five
  Rust fuzz targets under `rust/fuzz/fuzz_targets/`.
- **SHA-pinned GitHub Actions** throughout — rare and correct.
- **The `BackendSelector` / `can_handle` seam** (`json2xml/backend_selector.py`) is a clean way
  to keep the optional Rust backend from silently changing semantics.
