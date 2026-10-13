#!/usr/bin/env python3
"""Partial I03 collector: payload bytes, ELF metadata and resolved QML modules.

Use explicit trusted readelf/qmlimportscanner executables and dependency roots.
Inspected executables/QML are never run. This does not collect effective login.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

VERSION = "2"
INHERITED = re.compile(b"omarchy", re.IGNORECASE)
SKIP = {".git", "docs", "tests", "upstream", "__pycache__"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_files(root):
    # Follow packaged directory links too, but fail on loops/unreadable targets.
    def walk(directory, ancestors):
        resolved = directory.resolve(strict=True)
        if resolved in ancestors:
            raise ValueError(f"Directory symlink cycle: {directory}")
        for path in sorted(directory.iterdir()):
            if path.name in SKIP or path.name.startswith("LICENSE"):
                continue
            if path.is_dir():
                yield from walk(path, ancestors | {resolved})
            else:
                if not path.is_file():
                    raise ValueError(f"Invalid payload file: {path}")
                yield path
    yield from walk(root, set())


def within(path, roots):
    resolved = path.resolve(strict=True)
    return any(resolved.is_relative_to(root.resolve(strict=True)) for root in roots)


def command(tool, args):
    result = subprocess.run([str(tool), *args], capture_output=True, text=True,
                            timeout=120, env={"PATH": "/nonexistent", "LC_ALL": "C"})
    if result.returncode or result.stderr.strip():
        raise ValueError(f"{tool.name} inspection failed: exit={result.returncode}; {result.stderr[:400]}")
    return result.stdout


def inspect(outputs, readelf, scanner, qml_roots, library_roots, static_provider_reports=()):
    roots = list(outputs.values()) + qml_roots + library_roots
    static_proofs = {}
    proof_refs = []
    for report_path in static_provider_reports:
        report = json.loads(report_path.read_text())
        provider = Path(report['provider']['path'])
        if report.get('schema') != 1 or report.get('passed') is not True or not within(provider, roots) \
                or sha(provider) != report['provider']['sha256'] \
                or report.get('runner', {}).get('name') != 'tamlinux-qml-provider' \
                or not re.fullmatch(r'[0-9a-f]{64}', report['runner'].get('sourceDigest', '')):
            raise ValueError('Invalid/stale static provider report')
        # The selected provider must be part of inspected outputs, rather than
        # a reference-host binary that happens to import the same module names.
        if not within(provider, list(outputs.values())):
            raise ValueError('Static provider is not a selected inspected output')
        seen = set()
        for item in report['imports']:
            definition = Path(item['qmldir'])
            if item['name'] in seen or item.get('passed') is not True or type(item.get('exit')) is not int or item['exit'] != 0 \
                    or not re.fullmatch(r'[0-9a-f]{64}', item.get('configDigest', '')) \
                    or not within(definition, qml_roots) or sha(definition) != item['qmldirDigest']:
                raise ValueError('Invalid/stale static module import proof')
            seen.add(item['name'])
            static_proofs[(item['name'], str(definition.resolve()))] = item
        if not seen:
            raise ValueError('Empty static module import proof')
        proof_refs.append({'path': str(report_path), 'sha256': sha(report_path),
                           'provider': report['provider'], 'modules': sorted(seen)})
    byte_hits, metadata, errors, qml_errors = [], [], [], []
    visited = set()
    identities = {}

    def binary(path, location):
        resolved = path.resolve(strict=True)
        if resolved in visited:
            return
        visited.add(resolved)
        data = path.read_bytes()
        identities[location] = hashlib.sha256(data).hexdigest()
        try:
            data.decode("utf-8")
            non_utf8 = False
        except UnicodeDecodeError:
            non_utf8 = True
        if data.startswith(b"\x7fELF") or b"\0" in data or non_utf8:
            # Include UTF-16 spellings as well as non-UTF-8 byte strings.
            if INHERITED.search(data) or INHERITED.search(data.replace(b"\0", b"")):
                byte_hits.append(location)
        if not data.startswith(b"\x7fELF"):
            return
        try:
            dynamic = command(readelf, ["-W", "-d", str(path)])
            headers = command(readelf, ["-W", "-l", str(path)])
        except (ValueError, subprocess.TimeoutExpired) as error:
            errors.append(f"{location}: {error}")
            return
        needed = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", dynamic)
        rpaths = re.findall(r"\((?:RPATH|RUNPATH)\).*?\[([^\]]+)\]", dynamic)
        interpreter = re.findall(r"Requesting program interpreter: ([^\]]+)\]", headers)
        search = []
        for value in rpaths:
            for entry in value.split(":"):
                entry = entry.replace("${ORIGIN}", str(path.parent)).replace("$ORIGIN", str(path.parent))
                if not entry.startswith("/") or "$" in entry:
                    errors.append(f"{location}: unsupported library search path")
                else:
                    search.append(Path(entry))
        resolved_deps = {}
        for name in needed:
            if "/" in name and not Path(name).is_absolute():
                errors.append(f"{location}: relative dependency requires runtime cwd {name}")
                continue
            candidates = ([Path(name)] if "/" in name else [root / name for root in search + library_roots])
            found = next((p for p in candidates if p.is_file() and within(p, roots)), None)
            if found is None:
                errors.append(f"{location}: unresolved dependency {name}")
            else:
                resolved_deps[name] = str(found.resolve())
                binary(found, str(found.resolve()))
        for name in interpreter:
            target = Path(name)
            if not target.is_file() or not within(target, roots):
                errors.append(f"{location}: undeclared/missing interpreter {name}")
            else:
                binary(target, str(target.resolve()))
        metadata.append({"file": location, "sha256": identities[location], "needed": needed,
                         "rpath": rpaths, "interpreter": interpreter, "resolvedLibraries": resolved_deps})

    files = []
    for kind, root in sorted(outputs.items()):
        for path in payload_files(root):
            location = f"{kind}:{path.relative_to(root).as_posix()}"
            files.append(path)
            binary(path, location)
    qml = []
    if not any(path.suffix == ".qml" for path in files):
        qml_errors.append("No delivered QML payload inspected")
    if not qml_roots:
        qml_errors.append("No declared QML import roots")
    else:
        for root in outputs.values():
            if not any(path.suffix == ".qml" and path.is_relative_to(root) for path in files):
                continue
            try:
                args = ["-rootPath", str(root)]
                for import_root in qml_roots:
                    args += ["-importPath", str(import_root)]
                modules = json.loads(command(scanner, args))
                if not isinstance(modules, list) or not modules:
                    raise ValueError("Scanner returned no import records")
                for module in modules:
                    if not isinstance(module, dict):
                        raise ValueError("Malformed import record")
                    target = module.get("path")
                    if not target or not Path(target).exists() or not within(Path(target), roots):
                        qml_errors.append(f"Unresolved/undeclared QML import: {module.get('name', '?')}")
                    elif module.get("type") == "module":
                        directory = Path(target)
                        qmldir = directory / "qmldir"
                        if not qmldir.is_file():
                            qml_errors.append(f"Missing qmldir: {module.get('name', '?')}")
                        else:
                            module["qmldirDigest"] = sha(qmldir)
                            if INHERITED.search(qmldir.read_bytes()):
                                qml_errors.append(f"Inherited QML module definition: {module.get('name', '?')}")
                        plugin = module.get("plugin")
                        if plugin:
                            shared = directory / ("lib" + plugin + ".so")
                            if shared.is_file() and within(shared, roots):
                                binary(shared, str(shared.resolve()))
                            elif (module.get('name'), str(qmldir.resolve())) in static_proofs:
                                module['staticProviderProof'] = static_proofs[(module['name'], str(qmldir.resolve()))]['configDigest']
                            else:
                                # Qt marks statically linked providers optional. Do not
                                # infer that the selected executable registered them.
                                qml_errors.append(f"Missing shared/static-provider proof: {module.get('name', '?')} ({plugin})")
                    qml.append(module)
            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                qml_errors.append(f"QML scanner failed: {error}")
    return {"schema": 1, "scope": "Partial I03; not effective runtime or complete delivered-software acceptance",
            "runner": {"name": "tamlinux-compiled-qml-audit", "version": VERSION, "sourceDigest": sha(Path(__file__))},
            "tools": {"readelf": {"path": str(readelf), "sha256": sha(readelf)},
                      "qmlimportscanner": {"path": str(scanner), "sha256": sha(scanner)}},
            "outputs": {k: str(v) for k, v in outputs.items()},
            "qmlRoots": list(map(str, qml_roots)), "libraryRoots": list(map(str, library_roots)),
            "staticProviderReports": proof_refs,
            "filesInspected": len(files), "fileDigests": identities,
            "compiledPayloadPassed": not byte_hits and not errors,
            "resolvedQmlPassed": not qml_errors,
            "inheritedBinaryLocations": byte_hits, "elf": metadata,
            "compiledErrors": errors, "qmlErrors": qml_errors, "qmlImports": qml,
            "limits": "Compiled/NUL payloads and ELF closure inspected. Text/config/assets/helper semantics need other I03 cases. Validated selected-provider import reports prove static module registration; effective desktop loading remains I04. Scanner success alone is insufficient."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--readelf", type=Path, required=True)
    parser.add_argument("--qml-scanner", type=Path, required=True)
    parser.add_argument("--qml-root", type=Path, action="append", default=[])
    parser.add_argument("--library-root", type=Path, action="append", default=[])
    parser.add_argument("--static-provider-report", type=Path, action="append", default=[])
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--tuple-digest")
    parser.add_argument("--check-report", type=Path)
    args = parser.parse_args()
    try:
        outputs = {}
        for item in args.output:
            kind, value = item.split("=", 1)
            if not kind or kind in outputs or not Path(value).is_dir():
                raise ValueError("Duplicate/invalid output")
            outputs[kind] = Path(value).resolve(strict=True)
        if not outputs:
            raise ValueError("No outputs supplied")
        for tool in (args.readelf, args.qml_scanner):
            if not tool.is_absolute() or not tool.is_file() or not os.access(tool, os.X_OK):
                raise ValueError("Inspection tools must be explicit absolute executables")
        for root in args.qml_root + args.library_root:
            if not root.is_absolute() or not root.is_dir():
                raise ValueError("Dependency roots must be absolute directories")
        if args.check_report and not re.fullmatch(r"[0-9a-f]{64}", args.tuple_digest or ""):
            raise ValueError("Check report requires selection tuple SHA-256")
        result = inspect(outputs, args.readelf, args.qml_scanner, args.qml_root, args.library_root,
                         args.static_provider_report)
        result["tupleDigest"] = args.tuple_digest
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        if args.check_report:
            ref = {"path": str(args.report.resolve()), "sha256": sha(args.report)}
            # Partial cases can never assert the complete I03 check passed.
            report = {"schema": 1, "id": "I03", "status": "blocked", "tupleDigest": args.tuple_digest,
                      "runner": result["runner"], "cases": [
                          {"id": name, "status": "pass" if result[field] else "blocked", "evidence": [ref]}
                          for name, field in (("compiled-payload", "compiledPayloadPassed"),
                                              ("resolved-qml", "resolvedQmlPassed"))]}
            args.check_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f"compiled-qml-audit: {error}\n")
    print(f"Inspected {result['filesInspected']} payloads / {len(result['elf'])} ELF objects; "
          f"compiled={result['compiledPayloadPassed']}, QML={result['resolvedQmlPassed']}. Evidence: {args.report}")
    return 0 if result["compiledPayloadPassed"] and result["resolvedQmlPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
