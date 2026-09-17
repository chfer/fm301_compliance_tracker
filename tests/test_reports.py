"""Tests for the final side-by-side compliance PDF report."""

from __future__ import annotations

import json
from pathlib import Path

from fm301_compliance_tracker.reports import create_final_report


def write_compliance(validation_root: Path, name: str, categories: dict[str, dict[str, float]]) -> None:
    """Write a converter compliance JSON as produced by create_converter_summary."""
    total = sum(score["total"] for score in categories.values())
    passed = sum(score["passed"] for score in categories.values())
    report = {
        "schema_version": 1,
        "converter": name,
        "generated_at": "2026-09-16T12:00:00+02:00",
        "included_file_summaries": [f"{name}/EDZW/volume.results.summary.json"],
        "included_file_count": 1,
        "categories": categories,
        "overall": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "compliance_percent": round(100 * passed / total, 2),
        },
    }
    destination = validation_root / name / f"{name}-compliance.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report), encoding="utf-8")


def test_create_final_report_writes_a_pdf_from_available_converters(tmp_path: Path) -> None:
    """The report is written even when only some converters have a compliance file."""
    write_compliance(
        tmp_path, "example", {"Global_Attributes": {"passed": 1, "failed": 0, "total": 1, "compliance_percent": 100.0}}
    )

    destination = create_final_report(tmp_path, ("example", "missing-converter"))

    assert destination == tmp_path / "fm301_compliance_report.pdf"
    assert destination.is_file()
    assert destination.stat().st_size > 0
