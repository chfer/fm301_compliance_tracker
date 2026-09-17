"""Command-line interface for FM301 compliance tracking."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import ConfigurationError, load_config
from .logging_setup import configure_logging
from .workflow import run_workflow


def main() -> None:
    """Run the command-line application."""
    parser = argparse.ArgumentParser(description="Convert ODIM-H5 files and track FM301 compliance.")
    parser.add_argument("--config", type=Path, default=Path("config/fm301_compliance_tracker.toml"), help="Path to the TOML configuration file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print detailed progress to the console")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except (ConfigurationError, OSError) as error:
        parser.error(str(error))
    logger = configure_logging(config.logging, args.verbose)
    outcomes = run_workflow(config, logger)
    # Keep processing all inputs, then use the process exit code to signal any failures.
    failed = [outcome for outcome in outcomes if not outcome.succeeded]
    logger.info("Finished %s actions; %s failed", len(outcomes), len(failed))
    if failed:
        raise SystemExit(1)