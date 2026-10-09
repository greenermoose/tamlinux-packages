#!/usr/bin/env python3
"""Reject workstation/private references in the public delivery source."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
forbidden = ["/" + "home/fred", "config-" + "fred-tamlinux",
             "improvements-" + "fred-tamlinux", "git+" + "file:", "path:" + "/"]
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
failures = []
for name in filter(None, files):
    path = root / name
    if not path.is_file():
        continue
    text = path.read_text()
    failures += [f"{name}: {needle}" for needle in forbidden if needle in text]
if failures:
    raise SystemExit("\n".join(failures))
print(f"Public portability references checked in {len(files) - 1} tracked files.")
