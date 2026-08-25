"""Tests for streaming JSON Lines conversion."""

from __future__ import annotations

import json
from collections.abc import Iterator
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from json2xml.cli import main
from json2xml.json2xml import Json2xml
from json2xml.jsonl import JsonlConversionOptions, stream_jsonl_to_xml
from json2xml.utils import InvalidDataError, JSONReadError
from json2xml.xml_chars import InvalidXMLPolicy, transform_json_xml_chars


# @lat: [[tests#Streaming JSONL conversion#Records are written before reading ahead]]
def test_writes_each_record_before_next() -> None:
    """Write one XML item before requesting the following JSONL record."""
    destination = BytesIO()

    def observed_lines() -> Iterator[str]:
        yield '{"name": "Ada"}\n'
        assert b"Ada" in destination.getvalue()
        yield '{"name": "Grace"}\n'

    count = stream_jsonl_to_xml(
        observed_lines(),
        destination,
        JsonlConversionOptions(attr_type=False),
    )

    assert count == 2
    assert destination.getvalue() == (
        b'<?xml version="1.0" encoding="UTF-8" ?>'
        b"<all><item><name>Ada</name></item>"
        b"<item><name>Grace</name></item></all>"
    )


@pytest.mark.parametrize(
    "options",
    [
        JsonlConversionOptions(),
        JsonlConversionOptions(wrapper="events"),
        JsonlConversionOptions(root=False),
        JsonlConversionOptions(attr_type=False),
        JsonlConversionOptions(item_wrap=False),
        JsonlConversionOptions(cdata=True),
    ],
)
# @lat: [[tests#Streaming JSONL conversion#Supported options retain batch output]]
def test_supported_options_match_batch(options: JsonlConversionOptions) -> None:
    """Keep the existing list conversion shape for supported options."""
    records = [{"name": "Ada"}, {"name": "Grace"}]
    destination = BytesIO()

    stream_jsonl_to_xml(
        [json.dumps(record) for record in records],
        destination,
        options,
    )

    assert destination.getvalue() == Json2xml(
        records,
        wrapper=options.wrapper,
        root=options.root,
        attr_type=options.attr_type,
        item_wrap=options.item_wrap,
        cdata=options.cdata,
    ).to_xml()


# @lat: [[tests#Streaming JSONL conversion#Malformed records retain physical line numbers]]
def test_malformed_record_keeps_line_number() -> None:
    """Stop at a malformed physical line after writing earlier records."""
    destination = BytesIO()

    with pytest.raises(JSONReadError, match="Invalid JSONL at line 3"):
        stream_jsonl_to_xml(
            ['{"name": "Ada"}\n', "\n", "invalid\n"],
            destination,
            JsonlConversionOptions(attr_type=False),
        )

    assert b"Ada" in destination.getvalue()
    assert not destination.getvalue().endswith(b"</all>")


# @lat: [[tests#Streaming JSONL conversion#Conversion errors retain physical line numbers]]
def test_conversion_error_keeps_line_number() -> None:
    """Identify valid JSON that contains data forbidden by XML 1.0."""
    destination = BytesIO()

    with pytest.raises(InvalidDataError, match="JSONL line 2"):
        stream_jsonl_to_xml(
            ['{"name": "Ada"}\n', '{"name": "\\u0001"}\n'],
            destination,
        )


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (InvalidXMLPolicy.REPLACE, "A\ufffdB".encode()),
        (InvalidXMLPolicy.ESCAPE, b"A\\u0001B"),
        (InvalidXMLPolicy.REMOVE, b"AB"),
    ],
)
# @lat: [[tests#Streaming JSONL conversion#Invalid XML character policies are explicit]]
def test_invalid_xml_char_policy(
    policy: InvalidXMLPolicy, expected: bytes
) -> None:
    """Transform forbidden characters without changing valid Unicode."""
    destination = BytesIO()
    record = json.dumps(
        {
            "values": ["A\u0001B", 1],
            "valid": "x\u2028y\ue000z",
        }
    )

    stream_jsonl_to_xml(
        [record],
        destination,
        JsonlConversionOptions(
            attr_type=False,
            invalid_xml_policy=policy,
        ),
    )

    assert expected in destination.getvalue()
    assert "x\u2028y\ue000z".encode() in destination.getvalue()
    assert str(policy) == policy.value


def test_invalid_xml_policy_rejects_key_collision() -> None:
    """Do not silently overwrite object values when transformed keys collide."""
    with pytest.raises(InvalidDataError, match="duplicate JSON key"):
        transform_json_xml_chars(
            {"key\u0001": 1, "key\u0002": 2},
            InvalidXMLPolicy.REMOVE,
        )


# @lat: [[tests#Streaming JSONL conversion#CLI applies the selected character policy]]
def test_cli_applies_invalid_xml_policy(tmp_path: Path) -> None:
    """Apply explicit replacement to regular JSON and streamed JSONL."""
    for suffix in (".json", ".jsonl"):
        input_file = tmp_path / f"input{suffix}"
        output_file = tmp_path / f"output{suffix}.xml"
        input_file.write_text('{"value": "A\\u0001B"}\n', encoding="utf-8")

        assert main(
            [
                "--invalid-xml-chars",
                "replace",
                "-o",
                str(output_file),
                str(input_file),
            ]
        ) == 0
        assert "A\ufffdB".encode() in output_file.read_bytes()


# @lat: [[tests#Streaming JSONL conversion#Record limits do not become file limits]]
def test_cli_streams_above_aggregate_limit(tmp_path: Path) -> None:
    """Convert a JSONL file whose aggregate values exceed the JSON limit."""
    jsonl_file = tmp_path / "records.jsonl"
    output_file = tmp_path / "records.xml"
    record = json.dumps({"values": list(range(100))})
    jsonl_file.write_text(f"{record}\n" * 1_000, encoding="utf-8")

    assert main(["--no-type", "-o", str(output_file), str(jsonl_file)]) == 0
    assert output_file.read_bytes().startswith(
        b'<?xml version="1.0" encoding="UTF-8" ?><all><item>'
    )
    assert output_file.read_bytes().endswith(b"</item></all>")


# @lat: [[tests#Streaming JSONL conversion#Output files replace atomically]]
def test_cli_keeps_output_after_late_error(tmp_path: Path) -> None:
    """Keep an existing destination when a later JSONL record is malformed."""
    jsonl_file = tmp_path / "records.jsonl"
    output_file = tmp_path / "records.xml"
    jsonl_file.write_text('{"name": "Ada"}\ninvalid\n', encoding="utf-8")
    output_file.write_bytes(b"existing output")

    assert main(["-o", str(output_file), str(jsonl_file)]) == 1
    assert output_file.read_bytes() == b"existing output"
    assert list(tmp_path.glob(".records.xml.*.tmp")) == []


@pytest.mark.parametrize("flag", ["--pretty", "--xpath", "--list-headers"])
# @lat: [[tests#Streaming JSONL conversion#Incompatible modes fail before output]]
def test_cli_rejects_incompatible_modes(tmp_path: Path, flag: str) -> None:
    """Reject whole-document modes before creating the destination."""
    jsonl_file = tmp_path / "records.jsonl"
    output_file = tmp_path / "records.xml"
    jsonl_file.write_text('{"name": "Ada"}\n', encoding="utf-8")

    assert main([flag, "-o", str(output_file), str(jsonl_file)]) == 1
    assert not output_file.exists()


def test_cli_streams_jsonl_stdin_to_file(tmp_path: Path) -> None:
    """Stream explicitly framed stdin without materializing all records."""
    output_file = tmp_path / "records.xml"
    with patch("sys.stdin", StringIO('{"name": "Ada"}\n')):
        assert main(["--jsonl", "-", "-o", str(output_file)]) == 0

    assert b"Ada" in output_file.read_bytes()


def test_cli_streams_jsonl_to_stdout(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """Write streamed XML directly to binary stdout."""
    with patch("sys.stdin", StringIO('{"name": "Ada"}\n')):
        assert main(["--jsonl", "-"]) == 0

    assert capsysbinary.readouterr().out.endswith(b"</all>\n")


def test_cli_reports_invalid_jsonl_stdin(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Identify parse errors from explicitly framed JSONL stdin."""
    output_file = tmp_path / "output.xml"
    with patch("sys.stdin", StringIO("invalid\n")):
        assert main(["--jsonl", "-", "-o", str(output_file)]) == 1

    assert "Error: Invalid JSONL from stdin." in capsys.readouterr().err
    assert not output_file.exists()


def test_cli_reports_missing_jsonl(tmp_path: Path) -> None:
    """Return failure when a selected JSONL source cannot be opened."""
    assert main([str(tmp_path / "missing.jsonl")]) == 1


# @lat: [[tests#Streaming JSONL conversion#Invalid UTF-8 uses file parse errors]]
def test_cli_wraps_invalid_utf8(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report decoding failures through the JSON-file parse contract."""
    jsonl_file = tmp_path / "invalid-utf8.jsonl"
    output_file = tmp_path / "output.xml"
    jsonl_file.write_bytes(b'{"valid": true}\n\xff\n')

    assert main([str(jsonl_file), "-o", str(output_file)]) == 1
    assert "Error: Could not parse JSON file:" in capsys.readouterr().err
    assert not output_file.exists()


def test_cli_reports_missing_binary_stdout() -> None:
    """Return failure when the host does not expose binary stdout."""
    with (
        patch("sys.stdin", StringIO('{"name": "Ada"}\n')),
        patch("sys.stdout", StringIO()),
    ):
        assert main(["--jsonl", "-"]) == 1
