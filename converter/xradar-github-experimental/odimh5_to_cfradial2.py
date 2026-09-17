#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["xradar @ git+https://github.com/chfer/xradar@experimental/fm301"]
# ///
"""Convert an ODIM_H5 radar volume to CfRadial2 using xradar.

Usage:
    ./odimh5_to_cfradial2.py <input_odim_h5_file> <output_cfradial2_file> [--metadata <json_file>]

The optional --metadata option points to a JSON file containing a
"global_attrs" entry; its value is passed as the global_attrs dict to
xd.io.to_cfradial2 so those attributes are written to the output file.

Make the script executable once with:

    chmod +x odimh5_to_cfradial2.py

This is a PEP 723 inline-metadata script: uv reads the dependency block above
and resolves/caches an isolated environment for it automatically, no manual
venv or pip install needed.

xradar source:
    Unlike the sibling xradar-pip-latest script, this variant installs
    xradar from the "experimental/fm301" branch of
    https://github.com/chfer/xradar instead of from PyPI, to try out new
    functionality not yet released.

Refreshing xradar to the latest commit on the branch:
    A lockfile (odimh5_to_cfradial2.py.lock) pins the resolved dependency
    (including the exact git commit) so repeated runs are reproducible. When
    the branch is updated, refresh the lock and cached environment with:

        uv lock --script odimh5_to_cfradial2.py --upgrade-package xradar
        uv run --refresh-package xradar odimh5_to_cfradial2.py <input> <output>

    The first command re-resolves and rewrites the lockfile to the newest
    commit on the branch; the second forces uv to fetch/build that
    commit instead of reusing a stale cached environment.
"""

import argparse
import json
from pathlib import Path

import xradar as xd


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an ODIM_H5 radar volume to CfRadial2 using xradar."
    )
    parser.add_argument("input_path", type=Path, help="Path to the input ODIM_H5 file")
    parser.add_argument("output_path", type=Path, help="Path for the output CfRadial2 file")
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="Path to a JSON file with a 'global_attrs' entry to add to the output",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print progress information"
    )
    args = parser.parse_args()

    if args.verbose:
        print(
            f"Trying to convert {args.input_path} to {args.output_path} "
            f"with xradar version {xd.__version__}"
        )

    if not args.input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {args.input_path}")

    if not args.output_path.parent.is_dir():
        raise NotADirectoryError(
            f"Output directory does not exist: {args.output_path.parent}"
        )

    global_attrs = None
    if args.metadata is not None:
        if not args.metadata.is_file():
            print(f"Warning: metadata file does not exist: {args.metadata}")
        else:
            with args.metadata.open() as f:
                global_attrs = json.load(f).get("global_attrs")

    dtree = xd.io.open_odim_datatree(args.input_path)
    try:
        xd.io.to_cfradial2(dtree, args.output_path, global_attrs=global_attrs)
    finally:
        dtree.close()


if __name__ == "__main__":
    main()
