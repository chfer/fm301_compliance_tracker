"""Tests for FM301 tracker workflow helpers and subprocess orchestration."""

from __future__ import annotations

import logging
from pathlib import Path

from fm301_compliance_tracker.config import (
    AppConfig,
    ConverterConfig,
    DataConfig,
    LoggingConfig,
)
from fm301_compliance_tracker.workflow import discover_files, output_path, run_workflow


def write_script(path: Path, content: str) -> None:
    """Write an executable Python test script."""
    path.write_text(f"#!/usr/bin/env python3\n{content}", encoding="utf-8")
    path.chmod(0o755)


def test_discover_files_deduplicates_and_sorts(tmp_path: Path) -> None:
    """Discovery combines patterns and returns paths in stable order."""
    (tmp_path / "B").mkdir()
    (tmp_path / "A").mkdir()
    first = tmp_path / "A" / "one.h5"
    second = tmp_path / "B" / "two.hdf"
    first.touch()
    second.touch()

    assert discover_files(tmp_path, ("*.h5", "*.hdf", "*.h5")) == [first, second]


def test_output_path_uses_converter_node_and_stem(tmp_path: Path) -> None:
    """Conversion output mirrors the input NODE below the converter name."""
    converter = ConverterConfig("example", tmp_path / "converter", (), None)
    input_path = tmp_path / "odim" / "EDZW" / "volume.hdf"

    assert output_path(input_path, converter, tmp_path / "fm301") == (
        tmp_path / "fm301" / "example" / "EDZW" / "volume.nc"
    )


def test_workflow_continues_after_failed_conversion_and_mirrors_artifacts(tmp_path: Path) -> None:
    """A failed conversion does not prevent later conversion or validation work."""
    project = tmp_path
    odim_root = project / "data" / "odim_h5"
    first_input = odim_root / "EDZW" / "bad.hdf"
    second_input = odim_root / "EDZW" / "good.h5"
    first_input.parent.mkdir(parents=True)
    first_input.touch()
    second_input.touch()

    setup_marker = project / "setup-ran"
    setup = project / "setup.sh"
    setup.write_text(f"#!/usr/bin/env sh\ntouch {setup_marker}\n", encoding="utf-8")
    setup.chmod(0o755)
    converter = project / "converter.py"
    write_script(
        converter,
        "import pathlib, sys\n"
        "source, destination = map(pathlib.Path, sys.argv[-2:])\n"
        "if source.stem == 'bad': raise SystemExit(2)\n"
        "destination.write_text('converted', encoding='utf-8')\n",
    )
    checker = project / "checker.py"
    write_script(
        checker,
        "import json, pathlib, sys\n"
        "pdf = pathlib.Path(sys.argv[2])\n"
        "results = pathlib.Path(sys.argv[4])\n"
        "pdf.write_text('report', encoding='utf-8')\n"
        "json.dump([[\"Global_Attributes\", \"item\", \"Yes\", \"\", \"\", \"\", \"\", \"Mandatory\", \"pass\"]], results.open('w', encoding='utf-8'))\n",
    )

    config = AppConfig(
        project_root=project,
        data=DataConfig(odim_root, ("*.h5", "*.hdf"), project / "data" / "fm301", ("*.nc",), project / "data" / "validation"),
        converters=(ConverterConfig("example", converter, (), setup),),
        compliance_checker=checker,
        logging=LoggingConfig("INFO", project / "tracker.log", 1_000_000, 1),
    )
    outcomes = run_workflow(config, logging.getLogger("test_workflow"))

    assert setup_marker.exists()
    assert [(outcome.stage, outcome.succeeded) for outcome in outcomes] == [
        ("setup", True),
        ("conversion", False),
        ("conversion", True),
        ("validation", True),
    ]
    assert (project / "data" / "fm301" / "example" / "EDZW" / "good.nc").exists()
    assert (project / "data" / "validation" / "example" / "EDZW" / "good.validation_report.pdf").exists()
    assert (project / "data" / "validation" / "example" / "EDZW" / "good.results.json").exists()
    assert (project / "data" / "validation" / "example" / "EDZW" / "good.results.summary.json").exists()
    assert (project / "data" / "validation" / "example" / "example-compliance.json").exists()