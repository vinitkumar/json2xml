from __future__ import annotations

import importlib


# @lat: [[tests#Performance benchmarks#Benchmark script derives interpreter paths from configurable uv base dir]]
def test_benchmark_multi_python_uses_configurable_uv_base_dir(monkeypatch) -> None:
    monkeypatch.setenv("JSON2XML_UV_PYTHON_DIR", "/tmp/uv-python")
    monkeypatch.delenv("JSON2XML_PYTHON_CPYTHON_314_6", raising=False)
    monkeypatch.delenv("JSON2XML_PYTHON_CPYTHON_315_0B3", raising=False)
    monkeypatch.delenv("JSON2XML_PYTHON_PYPY_311_15", raising=False)

    module = importlib.import_module("benchmark_multi_python")
    module = importlib.reload(module)

    assert module.UV_PYTHON_DIR.as_posix() == "/tmp/uv-python"
    assert module.PYTHON_VERSIONS[0]["python"] == "/tmp/uv-python/cpython-3.14.6-macos-aarch64-none/bin/python3.14"
    assert module.PYTHON_VERSIONS[1]["python"] == "/tmp/uv-python/cpython-3.15.0b3-macos-aarch64-none/bin/python3.15"
    assert module.PYTHON_VERSIONS[2]["python"] == "/tmp/uv-python/pypy-3.11.15-macos-aarch64-none/bin/pypy3.11"


# @lat: [[tests#Performance benchmarks#Benchmark script lets explicit interpreter env vars override uv defaults]]
def test_benchmark_multi_python_env_overrides_interpreter_paths(monkeypatch) -> None:
    monkeypatch.setenv("JSON2XML_UV_PYTHON_DIR", "/tmp/uv-python")
    monkeypatch.setenv("JSON2XML_PYTHON_CPYTHON_314_6", "/custom/python314")
    monkeypatch.setenv("JSON2XML_PYTHON_CPYTHON_315_0B3", "/custom/python315")
    monkeypatch.setenv("JSON2XML_PYTHON_PYPY_311_15", "/custom/pypy311")

    module = importlib.import_module("benchmark_multi_python")
    module = importlib.reload(module)

    assert module.PYTHON_VERSIONS[0]["python"] == "/custom/python314"
    assert module.PYTHON_VERSIONS[1]["python"] == "/custom/python315"
    assert module.PYTHON_VERSIONS[2]["python"] == "/custom/pypy311"
