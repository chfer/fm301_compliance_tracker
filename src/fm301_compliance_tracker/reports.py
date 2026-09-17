"""Final overview PDF report pooling every converter's compliance summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .summaries import CATEGORIES

REPORT_FILENAME = "fm301_compliance_report.pdf"


def create_final_report(validation_root: Path, converter_names: tuple[str, ...]) -> Path:
    """Read every converter's compliance JSON and render a side-by-side PDF overview."""
    reports: dict[str, dict[str, Any]] = {}
    for name in converter_names:
        compliance_path = validation_root / name / f"{name}-compliance.json"
        if compliance_path.is_file():
            reports[name] = json.loads(compliance_path.read_text(encoding="utf-8"))

    destination = validation_root / REPORT_FILENAME
    _render_pdf(destination, reports)
    return destination


def _render_pdf(destination: Path, reports: dict[str, dict[str, Any]]) -> None:
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    header_style = ParagraphStyle("header", parent=styles["Normal"], fontSize=9, leading=11, textColor=colors.white)

    converter_names = list(reports)
    header_row = [Paragraph("", cell_style)] + [Paragraph(name, header_style) for name in converter_names]

    files_row = [Paragraph("Input files", cell_style)] + [
        Paragraph("<br/>".join(_input_files(report)), cell_style) for report in reports.values()
    ]
    generated_row = [Paragraph("Generated", cell_style)] + [
        Paragraph(report.get("generated_at", "n/a"), cell_style) for report in reports.values()
    ]

    rows = [header_row, files_row, generated_row]
    for category in CATEGORIES:
        row = [Paragraph(category.replace("_", " "), cell_style)]
        for report in reports.values():
            score = report["categories"].get(category)
            row.append(Paragraph(_percent_text(score), cell_style))
        rows.append(row)

    overall_row = [Paragraph("Overall", cell_style)] + [
        Paragraph(_percent_text(report.get("overall")), cell_style) for report in reports.values()
    ]
    rows.append(overall_row)

    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 3), (-1, -1), [colors.whitesmoke, colors.white]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dfe6e9")),
            ]
        )
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(destination), pagesize=landscape(A4))
    document.build(
        [
            Paragraph("FM301 Compliance Tracker &ndash; Final Report", styles["Title"]),
            Spacer(1, 12),
            table,
        ]
    )


def _input_files(report: dict[str, Any]) -> list[str]:
    """Return each input file identifier, stripped of the summary-file suffix."""
    return [
        summary.removesuffix(".results.summary.json")
        for summary in report.get("included_file_summaries", [])
    ]


def _percent_text(score: dict[str, Any] | None) -> str:
    if not score:
        return "n/a"
    return f"{score['compliance_percent']}%"
