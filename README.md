# FM301 Compliance Tracker

`fm301-compliance-tracker` compares ODIM-H5 to CfRadial2 converters by running
each configured converter over the same input data and validating the resulting
FM301 files.

## Installation

From the project root, install the application and its bundled compliance-checker dependencies:

```bash
uv sync
```

## Configuration

The default configuration is [config/fm301_compliance_tracker.toml](config/fm301_compliance_tracker.toml).
All paths are relative to the project root. Add converters with a `[[converter]]`
table containing `name`, `app`, optional `options`, and optional `setup`.

The tracker recursively searches `data.odim_h5.path` using its configured
patterns. A converter output is written to:

```text
data/fm301/<converter>/<NODE>/<input-stem>.nc
```

`NODE` is the input file's direct parent directory. Validation artifacts mirror
that layout below `data/validation`:

```text
data/validation/<converter>/<NODE>/<input-stem>.validation_report.pdf
data/validation/<converter>/<NODE>/<input-stem>.results.json
data/validation/<converter>/<NODE>/<input-stem>.results.summary.json
data/validation/<converter>/<converter>-compliance.json
```

The JSON summaries score only mandatory checks in `Global_Attributes`,
`Global_Ancillary_variables`, `sweep_variables`, `radar_parameters`, and
`radar_calibration`. Attribute rows contribute to their parent category.
Optional checks and `data_variables` do not affect the score. Percentages pool
the raw passing and total mandatory-check counts; they are not averages of
category or file percentages.

## Run

From the project root, run one of the following commands:

```bash
uv run fm301-compliance-tracker
uv run fm301-compliance-tracker --verbose
uv run fm301-compliance-tracker --config path/to/config.toml
```

Each converter setup command runs once before its batch. Existing generated
files are overwritten. The tracker continues when an action fails, records the
command output in `logs/fm301_compliance_tracker.log`, and exits nonzero after
the batch when one or more actions failed.
