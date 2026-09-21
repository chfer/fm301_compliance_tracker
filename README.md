# FM301 Compliance Tracker

`fm301-compliance-tracker` compares ODIM-H5 to CfRadial2 converters by running
each configured converter over the same input data and validating the resulting
FM301 files.

## Installation

From the project root, install the application and its bundled compliance-checker dependencies:

```bash
uv sync
```

## BoM FM301 library source

The `converter/bom-radar-fm301` submodule contains an
[unofficial GitHub development fork](https://github.com/chfer/bom-radar-fm301)
of the [original BoM FM301 C++ API and Toolkit](https://gitlab.com/bom-radar/fm301).
The upstream history credits Mark Curtis; the source copyright is
2021 Commonwealth of Australia, Bureau of Meteorology. Original history,
copyright notices, and the Apache License 2.0 are preserved. Ownership of the
GitHub fork does not imply authorship of the original software or upstream
endorsement.

Initialize the pinned source checkout with:

```bash
git submodule update --init --recursive converter/bom-radar-fm301
```

The default configuration enables this converter using the locally installed
`~/.local/opt/bom-radar-fm301/bin/fm301-convert` executable, with explicit
ODIM_H5 input and FM301 output formats. Follow the submodule's
[macOS build and local installation instructions](converter/bom-radar-fm301/README.md#macos-local-installation-without-sudo)
before running the tracker. There is no automatic build or update step for this
converter; rebuild and reinstall it when changing its source.

For upstream maintenance, configure the additional remote once in each new
checkout, then fetch updates:

```bash
git -C converter/bom-radar-fm301 remote add upstream https://gitlab.com/bom-radar/fm301.git
git -C converter/bom-radar-fm301 fetch upstream
```

Before making changes, switch to a development branch inside the submodule.
Merge upstream updates deliberately and push the tested converter commits to
the GitHub fork before committing the updated submodule pointer in this tracker.
The tracker pins an exact commit so converter comparisons remain reproducible.

## Configuration

The default configuration is [config/fm301_compliance_tracker.toml](config/fm301_compliance_tracker.toml).
Relative paths are resolved from the project root; absolute paths and `~/` home
directory paths are also supported. Add converters with a `[[converter]]`
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
