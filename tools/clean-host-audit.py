#!/usr/bin/env python3
"""Read explicit package outputs and a host root; never use the caller's PATH.

This is a readiness inventory, not an installer or a shell dependency parser.
Lexical custom-command references are candidates for investigation, including
commands inside conditions and launch arguments. Nothing inspected is executed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

CUSTOM = re.compile(r"(?<![\w.-])tam-[a-z0-9]+(?:-[a-z0-9]+)*(?![\w.-])")
ABSOLUTE = re.compile(r"(?:/usr/bin/|/usr/lib/tamlinux/)[a-zA-Z0-9][a-zA-Z0-9_-]*")
INHERITED = re.compile(r"omarchy", re.IGNORECASE)
SKIP_DIRS = {".git", "docs", "tests", "upstream", "__pycache__", "node_modules"}
SUFFIXES = {".qml", ".js", ".py", ".sh", ".json", ".jsonc", ".lua", ".desktop", ".conf",
            ".tpl", ".toml", ".ini", ".css"}


def wrapped_body(name):
    """makeWrapper moves the real script to .NAME-wrapped; its body still runs."""
    return name.startswith(".") and name.endswith("-wrapped")


def runtime_files(root):
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = Path(directory) / name
            if name.startswith("LICENSE") or name in {"source-revision", "version"}:
                continue
            # Extensionless files are scanned whether or not they are executable:
            # sourced environment files and application configs carry no suffix.
            if path.suffix in SUFFIXES or not path.suffix or wrapped_body(name):
                yield path


def code_lines(path):
    """Ignore whole comment lines, retaining interpreter declarations.

    Inline comments/docstrings are intentionally conservative: hits need review.
    No global inherited-name exception hides runtime compatibility strings.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return
    for number, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith(("//", "/*", "*")):
            continue
        if path.suffix == ".lua" and stripped.startswith("--"):
            continue
        if path.suffix == ".ini" and stripped.startswith(";"):
            continue
        if stripped.startswith("#") and not stripped.startswith("#!"):
            continue
        yield number, line


def scan_outputs(outputs):
    commands, absolute, inherited = {}, {}, []
    inherited_names = []
    embedded = {}
    available = {}
    files_scanned = 0
    for kind, root in sorted(outputs.items()):
        inherited_names.extend(f"{kind}:{rel}" for rel in inherited_paths(root))
        for path in sorted((root / "bin").glob("*")):
            if not path.name.startswith(".") and path.is_file() and os.access(path, os.X_OK):
                available.setdefault(path.name, []).append(f"{kind}:bin/{path.name}")
        for path in runtime_files(root):
            rel = path.relative_to(root).as_posix()
            location = f"{kind}:{rel}"
            if rel.startswith("share/tamlinux/plugins/") and os.access(path, os.X_OK):
                embedded.setdefault(path.name, []).append(location)
            files_scanned += 1
            for number, line in code_lines(path):
                reference = f"{location}:{number}"
                for name in set(CUSTOM.findall(line)):
                    commands.setdefault(name, []).append(reference)
                for name in set(ABSOLUTE.findall(line)):
                    absolute.setdefault(name, []).append(reference)
                if INHERITED.search(line):
                    # Record only identifiers/locations, never source bodies or state.
                    inherited.append(reference)
    return commands, absolute, inherited, inherited_names, embedded, available, files_scanned


def inherited_paths(root):
    """Shipped file and directory names are payload too (backgrounds, fonts)."""
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(dirs + files):
            if name.startswith("LICENSE"):
                continue
            rel = (Path(directory) / name).relative_to(root).as_posix()
            if INHERITED.search(name):
                yield rel


def native_executables(item):
    values = [(name, '/usr/bin/' + name) for name in item['binaries']]
    for path in item.get('executablePaths', []):
        if not isinstance(path, str) or not re.fullmatch(r'/usr/lib/tamlinux/[a-zA-Z0-9][a-zA-Z0-9_-]*', path):
            raise ValueError('Expected a fixed owned native executable path')
        values.append((path, path))
    return values


def host_inventory(root, contract):
    """Offline root inspection. No chroot, package manager or service invocation."""
    required_missing, optional_missing = [], []
    for item in contract["native"]:
        for binary, native_path in native_executables(item):
            path = root / native_path.lstrip("/")
            present = rooted_executable(root, path)
            if not present:
                target = optional_missing if item.get("optional", False) else required_missing
                target.append({"binary": binary, "package": item["package"]})
    forbidden = []
    for path in sorted((root / "var/lib/pacman/local").glob("*/desc")):
        lines = path.read_text().splitlines()
        if "%NAME%" in lines:
            name = lines[lines.index("%NAME%") + 1]
            if name in contract["forbiddenPackages"] or INHERITED.search(name):
                forbidden.append(name)
    return {"requiredBinariesMissing": required_missing,
            "optionalBinariesMissing": optional_missing,
            "forbiddenPackages": sorted(forbidden),
            "limits": "Offline binary/package presence only; repositories, sources, services, login and hardware still require installation proof."}


def rooted_executable(root, path):
    """Follow image symlinks inside the inspected root, with bounded traversal."""
    root = root.resolve()
    relative = path.relative_to(root)
    parts = list(relative.parts)
    current = root
    traversals = 0
    while parts:
        part = parts.pop(0)
        if part == ".":
            continue
        if part == "..":
            if current == root:
                return False
            current = current.parent
            continue
        current = current / part
        if current.is_symlink():
            traversals += 1
            if traversals > 40:
                return False
            target = Path(os.readlink(current))
            current = root if target.is_absolute() else current.parent
            parts = list(target.parts[1:] if target.is_absolute() else target.parts) + parts
    return current.is_file() and os.access(current, os.X_OK)


def audit(contract, outputs, host_root=None):
    commands, absolute, inherited, inherited_names, embedded, available, scanned = scan_outputs(outputs)
    declared = {path for item in contract["native"] for _, path in native_executables(item)}
    deferred = set(contract.get("deferredAbsoluteTools", []))
    missing = {name: sorted(refs) for name, refs in sorted(commands.items())
               if name not in available and name not in embedded}
    undeclared = {name: sorted(refs) for name, refs in sorted(absolute.items())
                  if name not in declared and name not in deferred}
    missing_outputs = sorted(set(contract["outputs"]) - set(outputs))
    missing_files = []
    for kind, paths in contract.get("requiredFiles", {}).items():
        missing_files.extend(f"{kind}:{path}" for path in paths
                             if kind not in outputs or not (outputs[kind] / path).is_file())
    for kind, paths in contract.get("requiredExecutables", {}).items():
        missing_files.extend(f"{kind}:{path}" for path in paths
                             if kind not in outputs or not (outputs[kind] / path).is_file()
                             or not os.access(outputs[kind] / path, os.X_OK))
    host = host_inventory(host_root, contract) if host_root else None
    blocked = bool(missing or inherited or inherited_names or undeclared or missing_outputs or missing_files or contract["pending"]
                   or (host and (host["requiredBinariesMissing"] or host["forbiddenPackages"])))
    return {
        "schema": 1, "target": contract["target"], "candidateReady": not blocked,
        "scope": "Static package-output inventory; not clean-host acceptance",
        "filesScanned": scanned, "missingOutputs": missing_outputs,
        "missingOutputFiles": sorted(missing_files),
        "availableCommands": available,
        "customCommandReferences": {name: sorted(refs) for name, refs in sorted(commands.items())},
        "missingPackageCommands": missing,
        "embeddedHelpers": embedded,
        "inheritedIdentifierLocations": sorted(inherited),
        "inheritedFileNames": sorted(inherited_names),
        "undeclaredAbsoluteTools": undeclared,
        "deferredAbsoluteTools": sorted(set(absolute) & deferred),
        "pendingRequirements": contract["pending"],
        "host": host,
        "limits": "Custom command matches are lexical, including data and dormant code; review before transfer. Embedded helper presence does not prove invocation resolution. PATH tools, dynamic commands, transitive third-party dependencies, repositories, theme assets and effective configuration require further proof. Whole-line provenance comments/licenses/tests/docs are excluded; inline comments and compatibility data may need review."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path,
                        default=Path(__file__).resolve().parents[1] / "contracts/arch-hyprland.json")
    parser.add_argument("--output", action="append", default=[], metavar="KIND=PATH",
                        help="Repeat for shell, plugins, commands, tools and tam immutable outputs")
    parser.add_argument("--host-root", type=Path, help="Optional clean Arch filesystem root to inspect")
    parser.add_argument("--format", choices=("json", "compact"), default="json",
                        help="Compact read-only summary; readiness and scan scope stay identical")
    parser.add_argument("--report", type=Path, help="Also retain the complete JSON evidence at this path")
    args = parser.parse_args()
    try:
        contract = json.loads(args.contract.read_text())
        if contract["schema"] != 1:
            raise ValueError("unsupported contract schema")
        outputs = {}
        for value in args.output:
            kind, path = value.split("=", 1)
            if kind not in contract["outputs"] or kind in outputs:
                raise ValueError(f"unknown or duplicate output kind: {kind}")
            root = Path(path).resolve()
            if not root.is_dir():
                raise ValueError(f"output is not a directory: {kind}")
            outputs[kind] = root
        host_root = args.host_root.resolve() if args.host_root else None
        if host_root and not (host_root / "etc/arch-release").is_file():
            raise ValueError("host root must contain etc/arch-release")
        result = audit(contract, outputs, host_root)
        report = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.report:
            args.report.write_text(report)
    except (OSError, ValueError, KeyError, IndexError) as error:
        parser.exit(2, f"clean-host-audit: {error}\n")
    print(compact_report(result) if args.format == "compact" else report, end="")
    return 0 if result["candidateReady"] else 1


def compact_report(result):
    """Present existing evidence without filtering blockers or guessing scope."""
    missing = result["missingPackageCommands"]
    menu_path = "shell:share/tamlinux/menu/"
    menu_only, shared, other = [], [], []
    for name, references in missing.items():
        menu = any(ref.startswith(menu_path) for ref in references)
        elsewhere = any(not ref.startswith(menu_path) for ref in references)
        (shared if menu and elsewhere else menu_only if menu else other).append(name)
    lines = [
        f"Target: {result['target']}",
        f"Inventory ready: {str(result['candidateReady']).lower()}",
        result["scope"],
        f"Runtime files scanned: {result['filesScanned']}",
        f"Available bin commands: {len(result['availableCommands'])}; embedded helper names: {len(result['embeddedHelpers'])}",
        f"Unresolved lexical command names: {len(missing)}",
    ]
    for label, names in (("Menu only", menu_only), ("Menu and other callers", shared), ("Other callers", other)):
        lines.append(f"{label} ({len(names)}): " + (", ".join(sorted(names)) or "none"))
    for label, key in (("Missing outputs", "missingOutputs"),
                       ("Missing required output files", "missingOutputFiles"),
                       ("Inherited identifier locations", "inheritedIdentifierLocations"),
                       ("Inherited file names", "inheritedFileNames"),
                       ("Undeclared absolute tools", "undeclaredAbsoluteTools"),
                       ("Deferred absolute tools", "deferredAbsoluteTools"),
                       ("Pending requirements", "pendingRequirements")):
        lines.append(f"{label}: {len(result[key])}")
    host = result["host"]
    if host is None:
        lines.append("Host: not inspected")
    else:
        for label, key in (("Missing required host binaries", "requiredBinariesMissing"),
                           ("Missing optional host binaries", "optionalBinariesMissing"),
                           ("Forbidden host packages", "forbiddenPackages")):
            lines.append(f"{label}: {len(host[key])}")
    lines.append("Lexical groups identify review candidates, not feature retirement or dependency counts.")
    lines.append(result["limits"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
