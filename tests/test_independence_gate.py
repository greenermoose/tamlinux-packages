"""Falsify tuple/evidence substitutions, exclusions and incomplete gate claims."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/independence-gate.py"
spec = importlib.util.spec_from_file_location("gate", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract = gate.load_json(ROOT / "contracts/arch-hyprland.json")
        self.selection = {
            "schema": 1, "sources": {k: "a" * 40 for k in ("product", "tam", "libtam", "tools")},
            "delivery": {"revision": "b" * 40, "lockDigest": "c" * 64,
                         "contractDigest": gate.digest(gate.canonical(self.contract))},
            "outputs": {k: {"path": "/fixture/" + k, "narHash": "sha256-fixture"}
                        for k in self.contract["outputs"]},
            "native": {k: "d" * 64 for k in ("imageDigest", "manifestDigest", "providersDigest")},
            "consumer": {"digest": "e" * 64}, "recovery": {"digest": "f" * 64},
            "capabilities": [{"id": "bluetooth", "required": True}]}
        self.tuple = gate.selection_digest(self.selection, self.contract["outputs"])
        self.evidence = self.root / "observation.txt"
        self.evidence.write_text("Synthetic fixture; not desktop acceptance\n")
        self.reports = []
        for identifier, definition in self.contract["independenceGate"]["checks"].items():
            names = definition["requiredCases"] + (["capability:bluetooth"] if identifier == "I07" else [])
            report = {"schema": 1, "id": identifier, "tupleDigest": self.tuple, "status": "pass",
                      "runner": {"name": "fixture", "version": "1"},
                      "cases": [{"id": name, "status": "pass", "evidence": [
                          {"path": self.evidence.name, "sha256": gate.digest(self.evidence.read_bytes())}]}
                          for name in names]}
            path = self.root / (identifier + ".json")
            path.write_text(json.dumps(report))
            self.reports.append((path, report))

    def result(self):
        return gate.aggregate(self.contract, self.selection, self.reports)

    def report(self, identifier):
        return next(report for _, report in self.reports if report["id"] == identifier)

    def test_complete_synthetic_records_pass(self):
        self.assertTrue(self.result()["candidateReady"])

    def test_missing_selection_cannot_pass(self):
        self.assertFalse(gate.aggregate(self.contract, None, self.reports)["candidateReady"])

    def test_each_missing_check_fails(self):
        for index in range(9):
            with self.subTest(index=index):
                reports = self.reports[:index] + self.reports[index + 1:]
                self.assertFalse(gate.aggregate(self.contract, self.selection, reports)["candidateReady"])

    def test_duplicate_or_unknown_check_is_invalid(self):
        for identifier in ("I01", "I10"):
            reports = self.reports + [(self.root / "extra.json", {"id": identifier})]
            with self.assertRaises(ValueError):
                gate.aggregate(self.contract, self.selection, reports)

    def test_changed_source_native_consumer_recovery_or_capability_stales_evidence(self):
        for section in ("sources", "native", "consumer", "recovery", "capabilities", "outputs"):
            altered = copy.deepcopy(self.selection)
            if section == "capabilities":
                altered[section][0]["required"] = False
                altered[section][0]["unavailableBehavior"] = "unavailable"
            elif section == "outputs":
                altered[section]["shell"]["narHash"] = "changed"
            else:
                key = next(iter(altered[section]))
                value = altered[section][key]
                altered[section][key] = "1" * len(value)
            self.assertFalse(gate.aggregate(self.contract, altered, self.reports)["candidateReady"], section)

    def test_contract_mutation_stales_selection(self):
        self.contract["pending"].append({"id": "new"})
        self.assertFalse(self.result()["candidateReady"])

    def test_partial_check_even_marked_pass_cannot_pass(self):
        self.report("I03")["cases"] = self.report("I03")["cases"][:2]
        self.assertFalse(self.result()["candidateReady"])

    def test_case_duplicate_unknown_or_failed_is_blocked(self):
        baseline = copy.deepcopy(self.report("I03")["cases"])
        for kind in ("duplicate", "unknown", "failed", "missing-evidence", "bad-digest"):
            cases = copy.deepcopy(baseline)
            if kind == "duplicate":
                cases.append(cases[0])
            elif kind == "unknown":
                cases.append({"id": "substitute", "status": "pass"})
            elif kind == "failed":
                cases[0]["status"] = "pending"
            elif kind == "missing-evidence":
                cases[0]["evidence"] = []
            else:
                cases[0]["evidence"][0]["sha256"] = "z" * 64
            self.report("I03")["cases"] = cases
            self.assertFalse(self.result()["candidateReady"], kind)

    def test_changed_deleted_or_unreadable_evidence_fails(self):
        self.evidence.write_text("altered")
        self.assertFalse(self.result()["candidateReady"])
        self.evidence.unlink()
        self.assertFalse(self.result()["candidateReady"])
        self.evidence.mkdir()
        self.assertFalse(self.result()["candidateReady"])

    def test_missing_runner_and_failed_check_fail(self):
        for value in ({}, {"name": "runner"}, {"name": "runner", "version": " "}):
            self.report("I04")["runner"] = value
            self.assertFalse(self.result()["candidateReady"])
        self.report("I04")["runner"] = {"name": "runner", "version": "1"}
        self.report("I04")["status"] = "blocked"
        self.assertFalse(self.result()["candidateReady"])

    def test_required_capability_cannot_be_unavailable(self):
        self.report("I07")["cases"][-1]["status"] = "unavailable"
        self.assertFalse(self.result()["candidateReady"])

    def test_predeclared_optional_capability_must_prove_expected_behavior(self):
        self.selection["capabilities"][0].update(required=False, unavailableBehavior="show unavailable")
        self.tuple = gate.selection_digest(self.selection, self.contract["outputs"])
        for _, report in self.reports:
            report["tupleDigest"] = self.tuple
        case = self.report("I07")["cases"][-1]
        case.update(status="unavailable", unavailableBehavior="wrong behavior")
        self.assertFalse(self.result()["candidateReady"])
        case["unavailableBehavior"] = "show unavailable"
        self.assertTrue(self.result()["candidateReady"])
        case["evidence"] = []
        self.assertFalse(self.result()["candidateReady"])

    def test_incomplete_selection_or_capability_matrix_is_invalid(self):
        for section in ("sources", "native", "consumer", "outputs", "capabilities"):
            altered = copy.deepcopy(self.selection)
            del altered[section]
            with self.assertRaises(ValueError):
                gate.selection_digest(altered, self.contract["outputs"])
        self.selection["capabilities"].append(self.selection["capabilities"][0])
        with self.assertRaises(ValueError):
            gate.selection_digest(self.selection, self.contract["outputs"])

    def test_duplicate_json_keys_rejected(self):
        path = self.root / "ambiguous.json"
        path.write_text('{"status":"blocked","status":"pass"}')
        with self.assertRaises(ValueError):
            gate.load_json(path)

    def test_cli_missing_report_compact_parity_and_invalid_destination(self):
        saved = self.root / "gate.json"
        result = subprocess.run([sys.executable, str(SCRIPT), "--format", "compact", "--report", str(saved)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Independence ready: false", result.stdout)
        self.assertEqual(len(json.loads(saved.read_text())["checks"]), 9)
        result = subprocess.run([sys.executable, str(SCRIPT), "--report", str(self.root / "missing/file")],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
