#!/usr/bin/env python3
"""Prepare a Tamlinux candidate in this assembly, one step at a time.

    tools/prepare-candidate.py version 0.4.5
    tools/prepare-candidate.py pin tamlinux=<40-hex> [tam=<40-hex> ...]
    tools/prepare-candidate.py build
    tools/prepare-candidate.py record --parent <assembly rev> --scope "..."
    tools/prepare-candidate.py check

Every step is optional and repeatable, and none of them commits, pushes,
promotes or activates anything: committing the assembly and Fred's Test and
Run stay explicit. Exact revisions only. A version that already has a
delivery record is never reused (D135, D178), and an existing record is never
overwritten. Build evidence goes to the private runtime state directory,
outside every repository.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = re.compile(r"[0-9a-f]{40}")
VERSION_FORM = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-([a-z]))?")
DEFAULT_TARGETS = (
    ".#tamlinux-shell", ".#tamlinux-plugins", ".#tamlinux-commands",
    ".#checks.x86_64-linux.installed-components", ".#checks.x86_64-linux.example-contract",
)


def fail(message: str) -> None:
    raise SystemExit(f"prepare-candidate: {message}")


def nix() -> str:
    return os.environ.get("PREPARE_CANDIDATE_NIX", "nix")


def read_version(root: Path) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def version_key(version: str) -> tuple:
    match = VERSION_FORM.fullmatch(version)
    if not match:
        fail(f"version {version!r} is not X.Y.Z (or a historical X.Y.Z-<letter>)")
    major, minor, patch, letter = match.groups()
    # A letter precedes its release: 0.4.4-c < 0.4.4.
    return int(major), int(minor), int(patch), letter or "~"


def delivery_path(root: Path, version: str) -> Path:
    return root / "deliveries" / f"tamlinux-{version}.json"


def lock_inputs(root: Path) -> dict[str, dict]:
    lock = json.loads((root / "flake.lock").read_text(encoding="utf-8"))
    nodes = lock["nodes"]
    return {name: nodes[node] for name, node in nodes[lock["root"]]["inputs"].items()}


def flake_revs(root: Path, inputs: dict[str, dict]) -> dict[str, list[str]]:
    """Revisions flake.nix names for each input's owner/repo."""
    text = (root / "flake.nix").read_text(encoding="utf-8")
    found = {}
    for name, node in inputs.items():
        original = node.get("original", {})
        pattern = rf'"github:{re.escape(original.get("owner", ""))}/{re.escape(original.get("repo", ""))}/([0-9a-f]{{40}})"'
        found[name] = re.findall(pattern, text, flags=re.IGNORECASE)
    return found


def cmd_version(root: Path, args) -> None:
    current = read_version(root)
    if delivery_path(root, args.version).exists():
        fail(f"{args.version} already has a delivery record; versions are never reused, use the next one")
    if version_key(args.version) <= version_key(current):
        fail(f"{args.version} does not come after the current {current}")
    (root / "VERSION").write_text(args.version + "\n", encoding="utf-8")
    print(f"version: {current} -> {args.version}")


def cmd_pin(root: Path, args) -> None:
    inputs = lock_inputs(root)
    text = (root / "flake.nix").read_text(encoding="utf-8")
    wanted = {}
    for pair in args.pins:
        name, sep, rev = pair.partition("=")
        if not sep or name not in inputs:
            fail(f"pin needs INPUT=REV with INPUT one of {', '.join(sorted(inputs))}; got {pair!r}")
        if not REV.fullmatch(rev):
            fail(f"{name}: pin an exact 40-character commit, not {rev!r}")
        original = inputs[name].get("original", {})
        url = rf'("github:{re.escape(original.get("owner", ""))}/{re.escape(original.get("repo", ""))}/)[0-9a-f]{{40}}"'
        text, count = re.subn(url, lambda match: match.group(1) + rev + '"', text, flags=re.IGNORECASE)
        if count != 1:
            fail(f"{name}: expected one pinned github URL in flake.nix, found {count}")
        wanted[name] = rev
    (root / "flake.nix").write_text(text, encoding="utf-8")
    subprocess.run([nix(), "flake", "update", *wanted], cwd=root, check=True)
    locked = lock_inputs(root)
    for name, rev in wanted.items():
        got = locked[name]["locked"].get("rev")
        if got != rev:
            fail(f"{name}: flake.lock resolved {got}, not {rev}")
        print(f"pin: {name} {rev}")


def evidence_dir(version: str) -> Path:
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return state / "tamlinux" / "candidates" / version


def cmd_build(root: Path, args) -> None:
    version = read_version(root)
    out = Path(args.evidence) if args.evidence else evidence_dir(version)
    out.mkdir(parents=True, exist_ok=True)
    targets = args.target or list(DEFAULT_TARGETS)
    with open(out / "build.log", "w", encoding="utf-8") as log:
        run = subprocess.run([nix(), "build", "--no-link", "--json", *targets], cwd=root,
                             stdout=subprocess.PIPE, stderr=log, text=True)
    if run.returncode:
        fail(f"build failed ({run.returncode}); log: {out / 'build.log'}")
    built = [{"drvPath": item["drvPath"], "outputs": item["outputs"]} for item in json.loads(run.stdout)]
    (out / "build.json").write_text(json.dumps({"version": version, "targets": targets, "outputs": built},
                                               indent=2) + "\n", encoding="utf-8")
    print(f"build: {len(built)} outputs for {version}; evidence {out / 'build.json'}")


def cmd_record(root: Path, args) -> None:
    version = read_version(root)
    path = delivery_path(root, version)
    if path.exists():
        fail(f"{path.relative_to(root)} exists; a prepared letter's record is kept, use the next letter")
    if not REV.fullmatch(args.parent):
        fail("--parent must be the exact 40-character parent assembly commit")
    build_file = Path(args.build) if args.build else evidence_dir(version) / "build.json"
    if not build_file.is_file():
        fail(f"no build evidence at {build_file}; run build first")
    build = json.loads(build_file.read_text(encoding="utf-8"))
    if build.get("version") != version:
        fail(f"build evidence is for {build.get('version')}, not {version}")
    record = {
        "schemaVersion": 1,
        "id": f"tamlinux-{version}",
        "version": version,
        "stage": "Develop candidate prepared for Test",
        "packagingRevision": "The Git commit containing this record",
        "parentAssembly": args.parent,
        "scope": args.scope,
        "components": {name: node["locked"] for name, node in sorted(lock_inputs(root).items())},
        "outputs": build["outputs"],
        "verification": {"builtTargets": build["targets"], "build": "pass"},
        "activation": "Not performed; await user Test instruction",
    }
    if args.extra:
        extra = json.loads(Path(args.extra).read_text(encoding="utf-8"))
        protected = set(record) - {"verification"}
        clash = protected & set(extra)
        if clash:
            fail(f"--extra may not replace {', '.join(sorted(clash))}")
        record["verification"].update(extra.pop("verification", {}))
        record.update(extra)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"record: wrote {path.relative_to(root)}")


def cmd_check(root: Path, args) -> int:
    problems = []
    version = read_version(root)
    version_key(version)
    inputs = lock_inputs(root)
    for name, revs in flake_revs(root, inputs).items():
        locked = inputs[name]["locked"].get("rev")
        if revs and revs != [locked]:
            problems.append(f"{name}: flake.nix pins {', '.join(revs)} but flake.lock has {locked}")
    product = Path(args.product)
    rev = inputs.get("tamlinux", {}).get("locked", {}).get("rev")
    if rev:
        shown = subprocess.run(["git", "-C", str(product), "show", f"{rev}:VERSION"],
                               capture_output=True, text=True)
        if shown.returncode:
            print(f"check: cannot read VERSION at tamlinux {rev[:12]} in {product}; not verified")
        elif shown.stdout.strip() != version:
            problems.append(f"tamlinux {rev[:12]} has VERSION {shown.stdout.strip()}, assembly has {version}")
    record = delivery_path(root, version)
    if record.exists():
        components = json.loads(record.read_text(encoding="utf-8")).get("components", {})
        for name, node in inputs.items():
            if components.get(name, {}).get("rev") != node["locked"].get("rev"):
                problems.append(f"{record.name}: {name} differs from flake.lock")
    for problem in problems:
        print(f"check: {problem}")
    print(f"check: {version} {'consistent' if not problems else 'has problems'}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a Tamlinux candidate")
    parser.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("version", help="set VERSION to the next unused version")
    p.add_argument("version")
    p = sub.add_parser("pin", help="pin inputs to exact commits and update flake.lock")
    p.add_argument("pins", nargs="+", metavar="INPUT=REV")
    p = sub.add_parser("build", help="build the candidate outputs and checks without links")
    p.add_argument("--target", action="append", help="flake output to build (repeatable; default: the standard five)")
    p.add_argument("--evidence", help="evidence directory (default: ~/.local/state/tamlinux/candidates/<version>)")
    p = sub.add_parser("record", help="write deliveries/tamlinux-<version>.json from the lock and build")
    p.add_argument("--parent", required=True, help="exact parent assembly commit")
    p.add_argument("--scope", required=True, help="what this candidate changes")
    p.add_argument("--build", help="build.json (default: the evidence directory)")
    p.add_argument("--extra", help="JSON object of further fields; its verification merges")
    p = sub.add_parser("check", help="read-only consistency check of VERSION, pins and record")
    p.add_argument("--product", default=str(ROOT.parent / "tamlinux"), help="tamlinux checkout")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.command == "check":
        return cmd_check(root, args)
    {"version": cmd_version, "pin": cmd_pin, "build": cmd_build, "record": cmd_record}[args.command](root, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
