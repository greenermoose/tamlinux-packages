#!/usr/bin/env python3
"""Verify I01–I09 evidence against one immutable selection; never promote/install.

Exit 0: all required evidence passes. Exit 1: missing/blocked/stale evidence.
Exit 2: invalid input. This verifies records, not the truth of runner assertions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

IDS = tuple(f"I{i:02}" for i in range(1, 10))
SHA = re.compile(r"[0-9a-f]{64}\Z")
REV = re.compile(r"[0-9a-f]{40}\Z")
VERSION = "1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def load_json(path):
    # Ambiguous duplicate keys can otherwise overwrite a failing assertion.
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def selection_digest(selection, outputs):
    require(isinstance(selection, dict) and selection.get("schema") == 1,
            "Selection must be a schema-1 object")
    for name in ("sources", "delivery", "outputs", "native", "consumer", "recovery"):
        require(isinstance(selection.get(name), dict) and selection[name], f"Missing selection {name}")
    for name in ("product", "tam", "libtam", "tools"):
        require(isinstance(selection["sources"].get(name), str)
                and REV.fullmatch(selection["sources"][name]), f"Missing exact {name} revision")
    require(REV.fullmatch(str(selection["delivery"].get("revision", ""))), "Missing delivery revision")
    for group, names in {"delivery": ["lockDigest", "contractDigest"],
                         "native": ["imageDigest", "manifestDigest", "providersDigest"],
                         "consumer": ["digest"], "recovery": ["digest"]}.items():
        for name in names:
            require(SHA.fullmatch(str(selection[group].get(name, ""))), f"Missing {group}.{name} SHA-256")
    require(set(selection["outputs"]) == set(outputs), "Selection must name exactly the required outputs")
    for name, value in selection["outputs"].items():
        require(isinstance(value, dict) and nonempty(value.get("path"))
                and nonempty(value.get("narHash")), f"Missing {name} path/NAR identity")
    caps = selection.get("capabilities")
    require(isinstance(caps, list), "Missing declared capability matrix")
    seen = set()
    for cap in caps:
        require(isinstance(cap, dict) and nonempty(cap.get("id")), "Invalid capability")
        require(cap["id"] not in seen and type(cap.get("required")) is bool, "Duplicate/invalid capability")
        seen.add(cap["id"])
        if not cap["required"]:
            require(nonempty(cap.get("unavailableBehavior")), "Optional capability needs unavailable behavior")
    return digest(canonical(selection))


def definitions(contract):
    gate = contract["independenceGate"]
    require(gate["requiredChecks"] == list(IDS), "Contract must require exactly I01–I09")
    checks = gate["checks"]
    require(isinstance(checks, dict) and set(checks) == set(IDS), "Missing/unknown contract check")
    for identifier, check in checks.items():
        cases = check.get("requiredCases")
        require(isinstance(cases, list) and cases and all(nonempty(x) for x in cases)
                and len(set(cases)) == len(cases), f"Invalid required cases for {identifier}")
    return checks


def aggregate(contract, selection, reports):
    checks = definitions(contract)
    tuple_digest = selection_digest(selection, contract["outputs"]) if selection is not None else None
    contract_digest = digest(canonical(contract))
    global_errors = []
    if selection is None:
        global_errors.append("No complete immutable selection supplied")
    elif selection["delivery"]["contractDigest"] != contract_digest:
        global_errors.append("Selected contract digest differs from this contract")
    by_id = {}
    for path, report in reports:
        require(isinstance(report, dict), "Check report must be an object")
        identifier = report.get("id")
        require(identifier in IDS, f"Unknown check ID: {identifier}")
        require(identifier not in by_id, f"Duplicate check ID: {identifier}")
        by_id[identifier] = (path, report)
    outcomes = []
    for identifier in IDS:
        required = list(checks[identifier]["requiredCases"])
        caps = selection["capabilities"] if selection and identifier == "I07" else []
        required += ["capability:" + c["id"] for c in caps]
        errors = list(global_errors)
        verified = []
        item = by_id.get(identifier)
        if item is None:
            errors.append("Check not run")
            path, report = None, {}
        else:
            path, report = item
            if report.get("schema") != 1 or report.get("tupleDigest") != tuple_digest or tuple_digest is None:
                errors.append("Missing/stale tuple binding or schema")
            if report.get("status") != "pass":
                errors.append("Runner did not pass this check")
            runner = report.get("runner")
            if not isinstance(runner, dict) or not all(nonempty(runner.get(k)) for k in ("name", "version")):
                errors.append("Missing runner identity/version")
            cases = report.get("cases", [])
            if not isinstance(cases, list):
                cases = []
                errors.append("Invalid cases")
            present = {}
            for case in cases:
                if not isinstance(case, dict) or case.get("id") not in required:
                    errors.append("Unknown case")
                    continue
                name = case["id"]
                if name in present:
                    errors.append(f"Duplicate case: {name}")
                    continue
                present[name] = case
                cap = next((c for c in caps if "capability:" + c["id"] == name), None)
                status = case.get("status")
                unavailable = (cap and not cap["required"] and status == "unavailable"
                               and case.get("unavailableBehavior") == cap["unavailableBehavior"])
                if status != "pass" and not unavailable:
                    errors.append(f"Case did not pass: {name}")
                refs = case.get("evidence")
                if not isinstance(refs, list) or not refs:
                    errors.append(f"No evidence: {name}")
                    continue
                for ref in refs:
                    if not isinstance(ref, dict) or not nonempty(ref.get("path")) or not SHA.fullmatch(str(ref.get("sha256", ""))):
                        errors.append(f"Invalid evidence reference: {name}")
                        continue
                    evidence_path = Path(ref["path"])
                    if not evidence_path.is_absolute():
                        evidence_path = path.parent / evidence_path
                    try:
                        actual = digest(evidence_path.read_bytes())
                        if actual != ref["sha256"]:
                            errors.append(f"Evidence digest changed: {name}")
                        else:
                            verified.append({"case": name, **ref})
                    except OSError:
                        errors.append(f"Missing/unreadable evidence: {name}")
            errors += [f"Missing case: {name}" for name in required if name not in present]
        outcomes.append({"id": identifier, "status": "blocked" if errors else "pass",
                         "reasons": errors, "runner": report.get("runner"),
                         "reportDigest": digest(canonical(report)) if path else None,
                         "requiredCases": required, "verifiedEvidence": verified})
    return {"schema": 1, "tupleDigest": tuple_digest, "contractDigest": contract_digest,
            "runner": {"name": "tamlinux-independence-gate", "version": VERSION,
                       "sourceDigest": digest(Path(__file__).read_bytes())},
            "candidateReady": all(x["status"] == "pass" for x in outcomes),
            "checks": outcomes, "capabilities": selection["capabilities"] if selection else None,
            "limits": "Evidence integrity and declared runner outcomes only; inspect underlying proof. Does not authorize Test/Run/Release."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path(__file__).resolve().parents[1] / "contracts/arch-hyprland.json")
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--check", type=Path, action="append", default=[])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--format", choices=("json", "compact"), default="json")
    args = parser.parse_args()
    try:
        result = aggregate(load_json(args.contract), load_json(args.selection) if args.selection else None,
                           [(path, load_json(path)) for path in args.check])
        payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.report:
            args.report.write_text(payload)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"independence-gate: {error}\n")
    if args.format == "json":
        print(payload, end="")
    else:
        print(f"Independence ready: {str(result['candidateReady']).lower()}")
        print(f"Tuple: {result['tupleDigest'] or 'not selected'}")
        for check in result["checks"]:
            print(f"{check['id']}: {check['status']}" + (" — " + "; ".join(check["reasons"]) if check["reasons"] else ""))
    return 0 if result["candidateReady"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
