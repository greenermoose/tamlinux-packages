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
overwritten. Letters end at 0.4.5, and a plain number never follows its own
letters (D180). Build evidence goes to the private runtime state directory,
outside every repository.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import importlib.util
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = re.compile(r"[0-9a-f]{40}")
VERSION_FORM = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-([a-z]))?")
LETTERS_END = (0, 4, 5)  # The first plain-number candidate (D180).
DEFAULT_TARGETS = (
    ".#tamlinux-shell", ".#tamlinux-plugins", ".#tamlinux-commands",
    ".#tam", ".#libtam", ".#tamlinux-tools",
    ".#checks.x86_64-linux.assembly-contract", ".#checks.x86_64-linux.installed-components",
    ".#checks.x86_64-linux.fresh-session", ".#checks.x86_64-linux.example-contract",
)
FOCUSED_TESTS = ('test_theme_ownership.py', 'test_keybinding_defaults.py', 'test_user_defaults.py')


def fingerprint(root: Path) -> str:
    """Bind evidence to the complete assembly recipe and verification policy."""
    paths = {root / name for name in ('VERSION', 'flake.nix', 'flake.lock')}
    paths.update((root / 'nix').rglob('*'))
    paths.update((root / 'tools').glob('*.py'))
    digest = hashlib.sha256(json.dumps([DEFAULT_TARGETS, FOCUSED_TESTS]).encode())
    for path in sorted(p for p in paths if p.is_file()):
        digest.update(str(path.relative_to(root)).encode() + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def load_checks(root: Path, out: Path) -> dict:
    path = out / 'checks.json'
    if not path.is_file():
        fail('required focused checks are missing; run verify or prepare first')
    checks = json.loads(path.read_text())
    if checks.get('fingerprint') != fingerprint(root) or checks.get('tests') != list(FOCUSED_TESTS):
        fail('focused check evidence is stale; run verify again')
    return checks


def cmd_verify(root: Path, args) -> None:
    out = Path(args.evidence) if args.evidence else evidence_dir(read_version(root))
    identity = fingerprint(root)
    path = out / 'checks.json'
    if path.exists() and json.loads(path.read_text()).get('fingerprint') == identity:
        load_checks(root, out)
        print('verify: reusing focused checks for identical inputs', flush=True)
        return
    if cmd_check(root, args):
        fail('candidate consistency check failed')
    rev = lock_inputs(root)['tamlinux']['locked']['rev']
    # Test the exact pinned source, never a neighbour's changing checkout.
    archive = subprocess.check_output(['git', '-C', str(args.product), 'archive', rev])
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tamlinux-candidate-check-') as directory:
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(directory, filter='data')
        with (out / 'checks.log').open('w') as log:
            for test in FOCUSED_TESTS:
                start = time.monotonic()
                print(f'verify: {test}', flush=True)
                source = Path(directory) / 'desktop/tests' / test
                if not source.is_file():
                    fail(f'required focused test is missing in pinned source: {test}')
                result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover',
                                         '-s', 'desktop/tests', '-p', test, '-q'],
                                        cwd=directory, stdout=log, stderr=log)
                print(f'verify: {test} finished in {time.monotonic()-start:.1f}s', flush=True)
                if result.returncode:
                    fail(f'focused check failed: {test}; log: {out / "checks.log"}')
    if fingerprint(root) != identity:
        fail('assembly inputs changed during focused checks')
    path.write_text(json.dumps({'fingerprint': identity, 'tests': list(FOCUSED_TESTS), 'product': rev}) + '\n')


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
    *number, letter = VERSION_FORM.fullmatch(args.version).groups()
    number = tuple(int(part) for part in number)
    if letter and number >= LETTERS_END:
        fail(f"{args.version}: letters ended at 0.4.5 (D180); use a plain X.Y.Z")
    if not letter and any((root / "deliveries").glob(f"tamlinux-{args.version}-[a-z].json")):
        fail(f"{args.version} already has lettered candidates; use the next patch number (D180)")
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
    identity = fingerprint(root)
    load_checks(root, out)
    started = time.monotonic()
    print(f'build: {len(targets)} required outputs (Nix reuses valid store results)', flush=True)
    with open(out / "build.log", "w", encoding="utf-8") as log:
        run = subprocess.run([nix(), "build", "--no-link", "--json", *targets], cwd=root,
                             stdout=subprocess.PIPE, stderr=log, text=True)
    if run.returncode:
        fail(f"build failed ({run.returncode}); log: {out / 'build.log'}")
    built = [{"drvPath": item["drvPath"], "outputs": item["outputs"]} for item in json.loads(run.stdout)]
    if fingerprint(root) != identity:
        fail('assembly inputs changed during build; evidence not recorded')
    (out / "build.json").write_text(json.dumps({"schema": 2, "fingerprint": identity,
                                               "checks": load_checks(root, out),
                                               "version": version, "targets": targets, "outputs": built},
                                               indent=2) + "\n", encoding="utf-8")
    print(f"build: {len(built)} outputs for {version} in {time.monotonic()-started:.1f}s; evidence {out / 'build.json'}", flush=True)


def cmd_record(root: Path, args) -> None:
    version = read_version(root)
    path = delivery_path(root, version)
    if path.exists():
        fail(f"{path.relative_to(root)} exists; a prepared candidate's record is kept, use the next version")
    if not REV.fullmatch(args.parent):
        fail("--parent must be the exact 40-character parent assembly commit")
    build_file = Path(args.build) if args.build else evidence_dir(version) / "build.json"
    if not build_file.is_file():
        fail(f"no build evidence at {build_file}; run build first")
    build = json.loads(build_file.read_text(encoding="utf-8"))
    if build.get("version") != version:
        fail(f"build evidence is for {build.get('version')}, not {version}")
    if build.get('schema') != 2 or build.get('fingerprint') != fingerprint(root):
        fail('build evidence is stale or unbound; verify and build again')
    if build.get('checks') != load_checks(root, build_file.parent):
        fail('build evidence does not match the required focused checks')
    if set(build.get('targets', [])) != set(DEFAULT_TARGETS) or len(build.get('outputs', [])) != len(DEFAULT_TARGETS):
        fail('build evidence is missing required targets or outputs')
    paths = [path for item in build['outputs'] for path in item['outputs'].values()]
    checked = subprocess.run([nix(), 'path-info', *paths], capture_output=True, text=True)
    if checked.returncode:
        fail('required outputs are unavailable; run build again to reuse or restore Nix results')
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
        "verification": {"builtTargets": build["targets"], "build": "pass",
                         "fingerprint": build['fingerprint'], "focusedChecks": build['checks']},
        "activation": "Not performed; await user Test instruction",
    }
    if args.extra:
        extra = json.loads(Path(args.extra).read_text(encoding="utf-8"))
        protected = set(record) - {"verification"}
        clash = protected & set(extra)
        if clash:
            fail(f"--extra may not replace {', '.join(sorted(clash))}")
        if set(extra.get('verification', {})) & {'builtTargets', 'build', 'fingerprint', 'focusedChecks'}:
            fail('--extra may not replace required verification evidence')
        record["verification"].update(extra.pop("verification", {}))
        record.update(extra)
    if version == '0.5.6' and not record.get('readiness', {}).get('nativeInstallationRequired'):
        fail('0.5.6 requires its matching native package and installation record')
    if record.get('readiness', {}).get('nativeInstallationRequired'):
        if not args.native_archive:
            fail('native installation requires --native-archive for candidate verification')
        spec = importlib.util.spec_from_file_location('native_package_check', ROOT / 'tools/native-package-check.py')
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        try:
            verifier.verify(record, Path(args.native_archive))
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            fail(f'native package verification failed: {error}')
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
    if not REV.fullmatch(rev or ''):
        problems.append('tamlinux requires an exact locked product revision')
    if rev:
        shown = subprocess.run(["git", "-C", str(product), "show", f"{rev}:VERSION"],
                               capture_output=True, text=True)
        if shown.returncode:
            problems.append(f"cannot read VERSION at tamlinux {rev[:12]} in {product}; not verified")
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
    p.add_argument("--target", action="append", help="flake output to build (repeatable; recording requires all ten)")
    p.add_argument("--evidence", help="evidence directory (default: ~/.local/state/tamlinux/candidates/<version>)")
    p = sub.add_parser("record", help="write deliveries/tamlinux-<version>.json from the lock and build")
    p.add_argument("--parent", required=True, help="exact parent assembly commit")
    p.add_argument("--scope", required=True, help="what this candidate changes")
    p.add_argument("--build", help="build.json (default: the evidence directory)")
    p.add_argument("--extra", help="JSON object of further fields; its verification merges")
    p.add_argument("--native-archive", help="matching native archive when native installation is required")
    p = sub.add_parser("check", help="read-only consistency check of VERSION, pins and record")
    p.add_argument("--product", default=str(ROOT.parent / "tamlinux"), help="tamlinux checkout")
    p = sub.add_parser('verify', help='run focused checks on the exact pinned product source')
    p.add_argument('--product', default=str(ROOT.parent / 'tamlinux'))
    p.add_argument('--evidence')
    p = sub.add_parser('prepare', help='resume inspect, focused checks, build, verify and record')
    p.add_argument('--product', default=str(ROOT.parent / 'tamlinux'))
    p.add_argument('--evidence')
    p.add_argument('--parent', required=True)
    p.add_argument('--scope', required=True)
    p.add_argument('--extra')
    p.add_argument('--native-archive')
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.command == "check":
        return cmd_check(root, args)
    if args.command == 'prepare':
        started = time.monotonic()
        print('inspect: verifying candidate pins and versions', flush=True)
        if cmd_check(root, args):
            fail('candidate consistency check failed')
        if delivery_path(root, read_version(root)).exists():
            fail('candidate is already frozen; use its recorded assembly for Test')
        cmd_verify(root, args)
        args.target = None
        cmd_build(root, args)
        args.build = str((Path(args.evidence) if args.evidence else evidence_dir(read_version(root))) / 'build.json')
        cmd_record(root, args)
        print(f'prepare: completed in {time.monotonic()-started:.1f}s; no promotion or activation', flush=True)
        return 0
    {"version": cmd_version, "pin": cmd_pin, "verify": cmd_verify,
     "build": cmd_build, "record": cmd_record}[args.command](root, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
