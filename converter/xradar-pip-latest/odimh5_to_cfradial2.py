#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["xradar"]
# ///
"""Convert an ODIM_H5 radar volume to CfRadial2 using xradar.

Usage:
    ./odimh5_to_cfradial2.py <input_odim_h5_file> <output_cfradial2_file>

Make the script executable once with:

    chmod +x odimh5_to_cfradial2.py

This is a PEP 723 inline-metadata script: uv reads the dependency block above
and resolves/caches an isolated environment for it automatically, no manual
venv or pip install needed.

Refreshing xradar to the latest release:
    A lockfile (odimh5_to_cfradial2.py.lock) pins the resolved dependency
    versions so repeated runs are reproducible. When a new xradar version is
    published on PyPI, update the lock and cached environment with:

        uv lock --script odimh5_to_cfradial2.py --upgrade-package xradar
        uv run --refresh-package xradar odimh5_to_cfradial2.py <input> <output>

    The first command re-resolves and rewrites the lockfile to the newest
    compatible xradar version; the second forces uv to fetch/build that
    version instead of reusing a stale cached environment.
"""

import argparse
from pathlib import Path

import xradar as xd


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an ODIM_H5 radar volume to CfRadial2 using xradar."
    )
    parser.add_argument("input_path", type=Path, help="Path to the input ODIM_H5 file")
    parser.add_argument("output_path", type=Path, help="Path for the output CfRadial2 file")
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

    dtree = xd.io.open_odim_datatree(args.input_path)
    try:
        xd.io.to_cfradial2(dtree, args.output_path)
    finally:
        dtree.close()


if __name__ == "__main__":
    main()
