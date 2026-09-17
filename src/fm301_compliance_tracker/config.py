"""Configuration loading and validation for the tracker."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


class ConfigurationError(ValueError):
    """Raised when the tracker configuration is invalid."""


@dataclass(frozen=True)
class DataConfig:
    """Resolved locations and patterns for application data."""

    odim_h5_path: Path
    odim_h5_patterns: tuple[str, ...]
    fm301_path: Path
    fm301_patterns: tuple[str, ...]
    validation_path: Path


@dataclass(frozen=True)
class ConverterConfig:
    """Configuration for one ODIM-H5 to FM301 converter."""

    name: str
    app: Path
    options: tuple[str, ...]
    setup: Path | None


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for tracker logging."""

    level: str
    file: Path
    max_size: int
    backup_count: int


@dataclass(frozen=True)
class AppConfig:
    """Resolved application configuration."""

    project_root: Path
    data: DataConfig
    converters: tuple[ConverterConfig, ...]
    compliance_checker: Path
    logging: LoggingConfig


def load_config(config_path: Path) -> AppConfig:
    """Load and validate a tracker TOML configuration file.

    Parameters
    ----------
    config_path
        Path to the TOML configuration file. Relative paths are resolved from
        the current working directory.
    """
    config_path = config_path.resolve()
    if not config_path.is_file():
        raise ConfigurationError(f"Configuration file does not exist: {config_path}")

    with config_path.open("rb") as config_file:
        raw = tomllib.load(config_file)

    # The default configuration lives in <project-root>/config/.
    project_root = config_path.parent.parent
    # TOML dotted keys such as odim_h5.path become nested dictionaries.
    data_raw = _mapping(raw, "data")
    odim_raw = _mapping(data_raw, "odim_h5")
    fm301_raw = _mapping(data_raw, "fm301")
    validation_raw = _mapping(data_raw, "validation")
    validation_path = _path(project_root, validation_raw, "path")

    data = DataConfig(
        odim_h5_path=_path(project_root, odim_raw, "path"),
        odim_h5_patterns=_strings(odim_raw, "pattern"),
        fm301_path=_path(project_root, fm301_raw, "path"),
        fm301_patterns=_strings(fm301_raw, "pattern"),
        validation_path=validation_path,
    )

    converters_raw = raw.get("converter")
    if not isinstance(converters_raw, list) or not converters_raw:
        raise ConfigurationError("Configuration requires at least one [[converter]] entry")
    converters = tuple(_converter(project_root, item) for item in converters_raw)
    names = [converter.name for converter in converters]
    # Converter names form part of output paths, so each name must identify one converter.
    if len(names) != len(set(names)):
        raise ConfigurationError("Converter names must be unique")

    checker_raw = _mapping(raw, "compliance_checker")
    logging_raw = _mapping(raw, "logging")
    checker = _path(project_root, checker_raw, "app")
    logging = LoggingConfig(
        level=_string(logging_raw, "level"),
        file=_path(project_root, logging_raw, "file"),
        max_size=_integer(logging_raw, "max_size"),
        backup_count=_integer(logging_raw, "backup_count"),
    )

    # Fail before work begins when a configured program cannot be found.
    for label, path in [("Compliance checker", checker), *[("Converter application", c.app) for c in converters]]:
        if not path.is_file():
            raise ConfigurationError(f"{label} does not exist: {path}")
    for converter in converters:
        if converter.setup is not None and not converter.setup.is_file():
            raise ConfigurationError(f"Converter setup does not exist: {converter.setup}")

    return AppConfig(project_root, data, converters, checker, logging)


def _converter(project_root: Path, raw: object) -> ConverterConfig:
    if not isinstance(raw, dict):
        raise ConfigurationError("Each [[converter]] entry must be a table")
    setup_value = raw.get("setup")
    # A setup command is optional; absent TOML values become None in Python.
    setup = None if setup_value is None else _path(project_root, raw, "setup")
    return ConverterConfig(
        name=_string(raw, "name"),
        app=_path(project_root, raw, "app"),
        options=_strings(raw, "options", required=False),
        setup=setup,
    )


def _mapping(raw: dict[str, object], name: str) -> dict[str, object]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Configuration requires a [{name}] table")
    return value


def _string(raw: dict[str, object], name: str) -> str:
    value = raw.get(name)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Configuration value '{name}' must be a non-empty string")
    return value


def _strings(raw: dict[str, object], name: str, required: bool = True) -> tuple[str, ...]:
    value = raw.get(name)
    if value is None and not required:
        return ()
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ConfigurationError(f"Configuration value '{name}' must be a non-empty string list")
    return tuple(value)


def _integer(raw: dict[str, object], name: str) -> int:
    value = raw.get(name)
    if not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"Configuration value '{name}' must be a non-negative integer")
    return value


def _path(project_root: Path, raw: dict[str, object], name: str) -> Path:
    return (project_root / _string(raw, name)).resolve()