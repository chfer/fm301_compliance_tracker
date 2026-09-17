"""External conversion and validation workflow."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import subprocess
import sys

from .config import AppConfig, ConverterConfig
from .reports import create_final_report
from .summaries import ResultsFormatError, create_converter_summary, create_file_summary, summary_path


@dataclass(frozen=True)
class CommandOutcome:
    """Captured result of one external command."""

    stage: str
    subject: Path | str
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        """Whether the command exited successfully."""
        return self.returncode == 0


def discover_files(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    """Recursively discover unique files matching configured glob patterns."""
    if not root.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {root}")
    # A set removes duplicates when patterns overlap; sorting makes runs reproducible.
    return sorted({path for pattern in patterns for path in root.rglob(pattern) if path.is_file()})


def output_path(input_path: Path, converter: ConverterConfig, fm301_root: Path) -> Path:
    """Return the converter output location for an input ODIM-H5 file."""
    return fm301_root / converter.name / input_path.parent.name / f"{input_path.stem}.nc"


def run_workflow(config: AppConfig, logger: logging.Logger) -> list[CommandOutcome]:
    """Run configured conversions followed by compliance validation."""
    inputs = discover_files(config.data.odim_h5_path, config.data.odim_h5_patterns)
    if not inputs:
        logger.warning("No ODIM-H5 input files found in %s", config.data.odim_h5_path)
        return []

    outcomes: list[CommandOutcome] = []
    for converter in config.converters:
        if converter.setup is not None:
            # Setup scripts may use relative filenames, so run them from their own directory.
            outcomes.append(
                _run(
                    "setup",
                    converter.name,
                    ("/bin/sh", str(converter.setup)),
                    converter.setup.parent,
                    logger,
                )
            )
        for input_path in inputs:
            destination = output_path(input_path, converter, config.data.fm301_path)
            # mkdir is harmless when the directory already exists.
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Substitute so options like --metadata can reference the input file's own directory.
            options = [option.replace("{input_dir}", str(input_path.parent)) for option in converter.options]
            outcomes.append(_run("conversion", input_path, (str(converter.app), *options, str(input_path), str(destination)), config.project_root, logger))

    converter_summaries: dict[str, list[tuple[Path, dict[object, object]]]] = {
        converter.name: [] for converter in config.converters
    }
    for fm301_file in discover_files(config.data.fm301_path, config.data.fm301_patterns):
        # Preserve the converter/NODE hierarchy when placing validation artifacts.
        relative = fm301_file.relative_to(config.data.fm301_path)
        artifact_dir = config.data.validation_path / relative.parent
        artifact_dir.mkdir(parents=True, exist_ok=True)
        report = artifact_dir / f"{fm301_file.stem}.validation_report.pdf"
        results = artifact_dir / f"{fm301_file.stem}.results.json"
        file_summary_path = summary_path(results)
        # Do not retain a summary from an earlier validation when this validation fails.
        results.unlink(missing_ok=True)
        file_summary_path.unlink(missing_ok=True)
        outcome = _run("validation", fm301_file, (sys.executable, str(config.compliance_checker), str(fm301_file), str(report), "--results", str(results)), config.project_root, logger)
        outcomes.append(outcome)
        if outcome.succeeded:
            try:
                file_summary = create_file_summary(results, config.data.validation_path)
            except (OSError, ResultsFormatError, ValueError) as error:
                outcomes.append(_summary_failure(results, error, logger))
            else:
                converter_summaries.setdefault(relative.parts[0], []).append(
                    (file_summary_path, file_summary)
                )

    for converter in config.converters:
        try:
            create_converter_summary(
                converter.name,
                converter_summaries[converter.name],
                config.data.validation_path,
            )
        except (OSError, ResultsFormatError, ValueError) as error:
            outcomes.append(_summary_failure(converter.name, error, logger))

    try:
        report_path = create_final_report(
            config.data.validation_path, tuple(converter.name for converter in config.converters)
        )
    except OSError as error:
        outcomes.append(_summary_failure("final report", error, logger))
    else:
        logger.info("Wrote final compliance report: %s", report_path)
    return outcomes


def _run(stage: str, subject: Path | str, command: tuple[str, ...], cwd: Path, logger: logging.Logger) -> CommandOutcome:
    logger.info("Running %s: %s", stage, " ".join(command))
    try:
        # Capture output so it is written to the application log, not lost in a batch run.
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        outcome = CommandOutcome(stage, subject, command, completed.returncode, completed.stdout, completed.stderr)
    except OSError as error:
        # For example, the configured executable may lack execute permission.
        outcome = CommandOutcome(stage, subject, command, 1, "", str(error))
    if outcome.stdout:
        logger.info("%s stdout for %s:\n%s", stage, subject, outcome.stdout.rstrip())
    if outcome.stderr:
        logger.warning("%s stderr for %s:\n%s", stage, subject, outcome.stderr.rstrip())
    if not outcome.succeeded:
        logger.error("%s failed for %s (exit %s)", stage, subject, outcome.returncode)
    return outcome


def _summary_failure(subject: Path | str, error: Exception, logger: logging.Logger) -> CommandOutcome:
    """Record a summary error while allowing remaining files to be processed."""
    logger.error("summary failed for %s: %s", subject, error)
    return CommandOutcome("summary", subject, (), 1, "", str(error))