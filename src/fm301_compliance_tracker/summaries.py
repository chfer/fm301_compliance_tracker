"""Compliance-summary calculation for checker result files."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


CATEGORIES = (
    "Global_Attributes",
    "Global_Ancillary_variables",
    "sweep_variables",
    "radar_parameters",
    "radar_calibration",
)
CATEGORY_INDEX = 0
APPLICABILITY_INDEX = 7
STATUS_INDEX = 8
SUMMARY_SUFFIX = ".results.summary.json"


class ResultsFormatError(ValueError):
    """Raised when a checker result file does not have the expected format."""


def summary_path(results_path: Path) -> Path:
    """Return the per-file summary path for a checker result path."""
    if not results_path.name.endswith(".results.json"):
        raise ValueError(f"Expected a .results.json file: {results_path}")
    return results_path.with_name(results_path.name.removesuffix(".results.json") + SUMMARY_SUFFIX)


def create_file_summary(results_path: Path, validation_root: Path) -> dict[str, Any]:
    """Calculate and write a mandatory-only compliance summary for one result file."""
    rows = _load_rows(results_path)
    category_counts = {category: {"passed": 0, "total": 0} for category in CATEGORIES}

    for row_number, row in enumerate(rows, start=1):
        _validate_row(row, results_path, row_number)
        category = row[CATEGORY_INDEX].split(":", 1)[0]
        if category not in category_counts or row[APPLICABILITY_INDEX] != "Mandatory":
            continue
        category_counts[category]["total"] += 1
        if row[STATUS_INDEX] == "pass":
            category_counts[category]["passed"] += 1

    categories = {
        category: _score(counts["passed"], counts["total"])
        for category, counts in category_counts.items()
        if counts["total"]
    }
    total = sum(score["total"] for score in categories.values())
    overall = (
        _score(sum(score["passed"] for score in categories.values()), total)
        if total
        else None
    )
    summary = {
        "schema_version": 1,
        "source_results": str(results_path.relative_to(validation_root)),
        "categories": categories,
        "overall": overall,
    }
    _write_json(summary_path(results_path), summary)
    return summary


def create_converter_summary(
    converter_name: str, file_summaries: list[tuple[Path, dict[str, Any]]], validation_root: Path
) -> Path:
    """Pool per-file summary counts and write one converter compliance report."""
    counts = {category: {"passed": 0, "total": 0} for category in CATEGORIES}
    for _, file_summary in file_summaries:
        for category, score in file_summary["categories"].items():
            counts[category]["passed"] += score["passed"]
            counts[category]["total"] += score["total"]

    categories = {
        category: _score(value["passed"], value["total"])
        for category, value in counts.items()
        if value["total"]
    }
    total = sum(score["total"] for score in categories.values())
    report = {
        "schema_version": 1,
        "converter": converter_name,
        # Local time, second precision is enough for a human-facing report.
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "included_file_summaries": [str(path.relative_to(validation_root)) for path, _ in file_summaries],
        "included_file_count": len(file_summaries),
        "categories": categories,
        "overall": _score(sum(score["passed"] for score in categories.values()), total) if total else None,
    }
    destination = validation_root / converter_name / f"{converter_name}-compliance.json"
    _write_json(destination, report)
    return destination


def _load_rows(results_path: Path) -> list[list[str]]:
    try:
        with results_path.open(encoding="utf-8") as results_file:
            rows = json.load(results_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ResultsFormatError(f"Cannot read result file {results_path}: {error}") from error
    if not isinstance(rows, list):
        raise ResultsFormatError(f"Result file must contain an array: {results_path}")
    return rows


def _validate_row(row: object, results_path: Path, row_number: int) -> None:
    if not isinstance(row, list) or len(row) <= STATUS_INDEX:
        raise ResultsFormatError(f"Invalid result row {row_number} in {results_path}")
    if not all(isinstance(row[index], str) for index in (CATEGORY_INDEX, APPLICABILITY_INDEX, STATUS_INDEX)):
        raise ResultsFormatError(f"Invalid category, applicability, or status in row {row_number} of {results_path}")


def _score(passed: int, total: int) -> dict[str, int | float]:
    return {
        "passed": passed,
        "failed": total - passed,
        "total": total,
        "compliance_percent": round(100 * passed / total, 2),
    }


def _write_json(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as output_file:
        json.dump(content, output_file, indent=2)
        output_file.write("\n")
    temporary_path.replace(path)