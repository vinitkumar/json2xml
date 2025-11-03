# json2xml AGENT.md

## Build/Test Commands
- Test: `pytest -vv` (all tests) or `pytest tests/test_<name>.py -vv` (single test file)
- Test with coverage: `pytest --cov=json2xml --cov-report=xml:coverage/reports/coverage.xml --cov-report=term -xvs`
- Lint: `ruff check json2xml tests`
- Type check: `uvx ty check json2xml tests`
- Test all Python versions: `tox`
- Clean artifacts: `make clean`

## Architecture
- Main module: `json2xml/` with `json2xml.py` (main converter), `dicttoxml.py` (core conversion), `utils.py` (utilities), `parallel.py` (parallel processing)
- Core functionality: JSON to XML conversion via `Json2xml` class wrapping `dicttoxml`
- Tests: `tests/` with test files following `test_*.py` pattern

## Code Style (from .cursorrules)
- Always add typing annotations to functions/classes with descriptive docstrings (PEP 257)
- Use pytest (no unittest), all tests in `./tests/` with typing annotations
- Import typing fixtures when TYPE_CHECKING: `CaptureFixture`, `FixtureRequest`, `LogCaptureFixture`, `MonkeyPatch`, `MockerFixture`
- Ruff formatting: line length 119, ignores E501, F403, E701, F401
- Python 3.13+ required, supports up to 3.14 (including 3.13t, 3.14t freethreaded)
- Dependencies: defusedxml, urllib3, xmltodict, pytest, pytest-cov
