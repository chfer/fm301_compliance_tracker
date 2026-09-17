#!/usr/bin/env sh

# update the script lockfile without running any conversion
uv lock --script odimh5_to_cfradial2.py --upgrade-package xradar
# refresh the script xradar cached package and then do a dummy run (only display argparse help; no input or output conversion occurs).
uv run --refresh-package xradar odimh5_to_cfradial2.py --help
