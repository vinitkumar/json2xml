"""Tests for streaming JSON Lines conversion."""

from __future__ import annotations

import argparse
import json
import stat
from collections.abc import Iterator
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from json2xml.cli import invalid_xml_policy, main
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
    records = [{"name": "Ada"}, 7, ["nested"], {"name": "Grace"}]
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
# @lat: [[tests#Streaming JSONL conversion#Whole-document modes materialize records]]
def test_cli_materializes_whole_document_modes(tmp_path: Path, flag: str) -> None:
    """Convert JSONL through the materialized reader for whole-document modes."""
    jsonl_file = tmp_path / "records.jsonl"
    output_file = tmp_path / "records.xml"
    jsonl_file.write_text('{"name": "Ada"}\n{"name": "Grace"}\n', encoding="utf-8")

    assert main([flag, "-o", str(output_file), str(jsonl_file)]) == 0
    assert "Ada" in output_file.read_text(encoding="utf-8")
    assert "Grace" in output_file.read_text(encoding="utf-8")


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


# @lat: [[tests#CLI failure messages#Missing JSONL reuses the missing-file message]]
def test_cli_reports_missing_jsonl(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report a missing JSONL source the same way a missing JSON file is."""
    with pytest.raises(SystemExit) as exit_info:
        main([str(tmp_path / "missing.jsonl")])

    assert exit_info.value.code == 1
    assert "JSON file not found" in capsys.readouterr().err


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


# @lat: [[tests#Streaming JSONL conversion#Output files keep conventional permissions]]
def test_cli_output_permissions_match_plain_writes(tmp_path: Path) -> None:
    """Leave streamed output readable rather than temporary-file private."""
    jsonl_file = tmp_path / "records.jsonl"
    json_file = tmp_path / "record.json"
    jsonl_file.write_text('{"name": "Ada"}\n', encoding="utf-8")
    json_file.write_text('{"name": "Ada"}\n', encoding="utf-8")
    streamed = tmp_path / "streamed.xml"
    materialized = tmp_path / "materialized.xml"

    assert main(["-o", str(streamed), str(jsonl_file)]) == 0
    assert main(["-o", str(materialized), str(json_file)]) == 0
    assert streamed.stat().st_mode == materialized.stat().st_mode

    existing = tmp_path / "existing.xml"
    existing.write_bytes(b"")
    existing.chmod(0o640)

    assert main(["-o", str(existing), str(jsonl_file)]) == 0
    assert stat.S_IMODE(existing.stat().st_mode) == 0o640


# @lat: [[tests#Streaming JSONL conversion#Output failures name the destination]]
def test_cli_output_error_names_destination(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Name the requested output file instead of the hidden temporary file."""
    jsonl_file = tmp_path / "records.jsonl"
    jsonl_file.write_text('{"name": "Ada"}\n', encoding="utf-8")
    output_file = tmp_path / "missing-directory" / "records.xml"

    assert main(["-o", str(output_file), str(jsonl_file)]) == 1
    error = capsys.readouterr().err
    assert str(output_file) in error
    assert ".tmp" not in error


# @lat: [[tests#Streaming JSONL conversion#Byte order marks are dropped]]
def test_stream_drops_byte_order_mark() -> None:
    """Convert a first record an editor saved with a byte order mark."""
    destination = BytesIO()

    stream_jsonl_to_xml(
        ['﻿{"name": "Ada"}\n'],
        destination,
        JsonlConversionOptions(attr_type=False),
    )

    assert b"<name>Ada</name>" in destination.getvalue()


# @lat: [[tests#Streaming JSONL conversion#Record conversion failures stop the CLI]]
def test_cli_reports_record_conversion_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report a record that is valid JSON but forbidden by XML 1.0."""
    jsonl_file = tmp_path / "records.jsonl"
    output_file = tmp_path / "records.xml"
    jsonl_file.write_text('{"name": "Ada"}\n{"name": "\\u0001"}\n', encoding="utf-8")

    assert main(["-o", str(output_file), str(jsonl_file)]) == 1
    assert "JSONL line 2" in capsys.readouterr().err
    assert not output_file.exists()


# @lat: [[tests#Streaming JSONL conversion#Unreadable sources use the file parse error]]
def test_cli_reports_unreadable_jsonl(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report an existing JSONL file the process is not allowed to open."""
    jsonl_file = tmp_path / "records.jsonl"
    jsonl_file.write_text('{"name": "Ada"}\n', encoding="utf-8")

    with patch("json2xml.cli.open", side_effect=OSError("denied")):
        assert main([str(jsonl_file)]) == 1

    assert "Could not parse JSON file:" in capsys.readouterr().err


# @lat: [[tests#CLI input resolution#JSONL string input is framed by line]]
def test_cli_frames_string_input_by_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Frame --string input by line and report malformed records."""
    assert main(["--jsonl", "-s", '{"name": "Ada"}\n{"name": "Grace"}']) == 0
    assert capsys.readouterr().out.count("<item") == 2

    with pytest.raises(SystemExit) as exit_info:
        main(["--jsonl", "-s", '{"name": "Ada"}\ninvalid'])

    assert exit_info.value.code == 1
    assert "Invalid JSON Lines in --string input" in capsys.readouterr().err


# @lat: [[tests#CLI failure messages#Argument conflicts fail during parsing]]
def test_cli_rejects_jsonl_with_url(capsys: pytest.CaptureFixture[str]) -> None:
    """Reject flag combinations and values while parsing arguments."""
    with pytest.raises(SystemExit) as exit_info:
        main(["--jsonl", "-u", "https://example.com/data.json"])

    assert exit_info.value.code == 2
    assert "--jsonl cannot be combined with --url" in capsys.readouterr().err

    with pytest.raises(SystemExit) as exit_info:
        main(["--invalid-xml-chars", "bogus", "-s", "{}"])

    assert exit_info.value.code == 2
    assert "choose from reject, replace, escape, remove" in capsys.readouterr().err

    with pytest.raises(argparse.ArgumentTypeError, match="choose from reject"):
        invalid_xml_policy("bogus")
