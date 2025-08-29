"""Pytest configuration for json2xml tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

import pytest

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_json_string() -> str:
    """Return a sample JSON string for testing.

    Returns:
        str: A sample JSON string
    """
    return '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'


@pytest.fixture
def sample_json_dict() -> dict[str, Any]:
    """Return a sample JSON dictionary for testing.

    Returns:
        Dict[str, Any]: A sample JSON dictionary
    """
    return {
        "login": "mojombo",
        "id": 1,
        "avatar_url": "https://avatars0.githubusercontent.com/u/1?v=4",
    }


@pytest.fixture
def sample_json_list() -> list[dict[str, Any]]:
    """Return a sample JSON list for testing.

    Returns:
        List[Dict[str, Any]]: A sample list of JSON dictionaries
    """
    return [
        {
            "login": "mojombo",
            "id": 1,
            "avatar_url": "https://avatars0.githubusercontent.com/u/1?v=4",
        },
        {
            "login": "defunkt",
            "id": 2,
            "avatar_url": "https://avatars0.githubusercontent.com/u/2?v=4",
        },
    ]


@pytest.fixture
def sample_json_file(tmp_path: Path) -> Path:
    """Create a sample JSON file for testing.

    Args:
        tmp_path (Path): Pytest temporary path fixture

    Returns:
        Path: Path to the created JSON file
    """
    file_path = tmp_path / "sample.json"

    data = {
        "login": "mojombo",
        "id": 1,
        "avatar_url": "https://avatars0.githubusercontent.com/u/1?v=4",
    }

    with open(file_path, "w") as f:
        json.dump(data, f)

    return file_path
