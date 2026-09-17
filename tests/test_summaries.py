"""Tests for mandatory-only compliance summaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fm301_compliance_tracker.summaries import (
    ResultsFormatError,
    create_converter_summary,
    create_file_summary,
    summary_path,
)


def write_results(path: Path, rows: object) -> None:
    """Write test checker output as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")


def row(category: str, applicability: str, status: str) -> list[str]:
    """Create a checker row with the fields used by summary calculation."""
    return [category, "item", "Yes", "", "", "", "", applicability, status]


def test_file_summary_normalizes_categories_and_pools_mandatory_checks(tmp_path: Path) -> None:
    """Attribute rows count toward their parent category and optional rows do not count."""
    results_path = tmp_path / "example" / "EDZW" / "volume.results.json"
    write_results(
        results_path,
        [
            row("Global_Attributes", "Mandatory", "pass"),
            row("Global_Attributes", "Mandatory", "fail_mandatory"),
            row("Global_Ancillary_variables:latitude", "Mandatory", "pass"),
            row("sweep_variables:sweep_0/time", "Mandatory", "fail_mandatory"),
            row("data_variables", "Mandatory", "pass"),
            row("radar_parameters", "Optional", "pass"),
        ],
    )

    summary = create_file_summary(results_path, tmp_path)

    assert summary["categories"] == {
        "Global_Attributes": {"passed": 1, "failed": 1, "total": 2, "compliance_percent": 50.0},
        "Global_Ancillary_variables": {"passed": 1, "failed": 0, "total": 1, "compliance_percent": 100.0},
        "sweep_variables": {"passed": 0, "failed": 1, "total": 1, "compliance_percent": 0.0},
    }
    assert summary["overall"] == {"passed": 2, "failed": 2, "total": 4, "compliance_percent": 50.0}
    assert summary_path(results_path).is_file()


def test_converter_summary_pools_counts_instead_of_averaging_percentages(tmp_path: Path) -> None:
    """Converter scores give every mandatory check equal weight across files."""
    first_path = tmp_path / "example" / "A.results.summary.json"
    second_path = tmp_path / "example" / "B.results.summary.json"
    first = {"categories": {"Global_Attributes": {"passed": 1, "total": 1}}}
    second = {"categories": {"Global_Attributes": {"passed": 0, "total": 9}}}

    report_path = create_converter_summary("example", [(first_path, first), (second_path, second)], tmp_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["categories"]["Global_Attributes"] == {
        "passed": 1,
        "failed": 9,
        "total": 10,
        "compliance_percent": 10.0,
    }
    assert report["overall"]["compliance_percent"] == 10.0


def test_malformed_rows_raise_a_format_error(tmp_path: Path) -> None:
    """The row contract rejects incomplete checker output."""
    results_path = tmp_path / "bad.results.json"
    write_results(results_path, [["too", "short"]])

    with pytest.raises(ResultsFormatError, match="Invalid result row 1"):
        create_file_summary(results_path, tmp_path)