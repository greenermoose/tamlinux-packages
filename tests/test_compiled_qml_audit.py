"""Fail closed on hidden binary identifiers and unresolved module/library closure."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/compiled-qml-audit.py"
spec = importlib.util.spec_from_file_location("compiled", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class CompiledTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "output"
        self.modules = self.root / "modules"
        self.libraries = self.root / "libraries"
        for directory in (self.output, self.modules, self.libraries):
            directory.mkdir()
        self.write(self.output / "main.qml", "import Test.Module\nQtObject {}\n")
        self.module = self.modules / "Test/Module"
        self.write(self.module / "qmldir", "module Test.Module\n")
        self.scanner = self.tool("scanner", "print(" + repr(json.dumps([
            {"type": "module", "name": "Test.Module", "path": str(self.module)}])) + ")")
        self.readelf = self.tool("readelf", "print('')")

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)
        return path

    def tool(self, name, code):
        path = self.write(self.root / name, "#!" + sys.executable + "\n" + code + "\n")
        path.chmod(0o755)
        return path

    def inspect(self):
        return audit.inspect({"shell": self.output}, self.readelf, self.scanner,
                             [self.modules], [self.libraries])

    def test_resolved_fixture(self):
        result = self.inspect()
        self.assertTrue(result["resolvedQmlPassed"])
        self.assertTrue(result["compiledPayloadPassed"])
        self.assertIn("qmldirDigest", result["qmlImports"][0])

    def test_static_proof_binds_selected_provider_and_module_bytes(self):
        self.setUpScanner('testplugin')
        provider = self.write(self.output / 'bin/provider', b'provider bytes')
        record = {'schema': 1, 'passed': True,
                  'runner': {'name': 'tamlinux-qml-provider', 'sourceDigest': 'a' * 64},
                  'provider': {'path': str(provider), 'sha256': audit.sha(provider)},
                  'imports': [{'name': 'Test.Module', 'qmldir': str(self.module / 'qmldir'),
                               'qmldirDigest': audit.sha(self.module / 'qmldir'),
                               'passed': True, 'exit': 0, 'configDigest': 'b' * 64}]}
        report = self.write(self.root / 'proof.json', json.dumps(record))
        def inspect():
            return audit.inspect({'shell': self.output}, self.readelf, self.scanner,
                                 [self.modules], [self.libraries], [report])
        self.assertTrue(inspect()['resolvedQmlPassed'])
        provider.write_bytes(b'changed provider')
        with self.assertRaisesRegex(ValueError, 'stale static provider'):
            inspect()
        provider.write_bytes(b'provider bytes')
        (self.module / 'qmldir').write_text('module Changed.Module\n')
        with self.assertRaisesRegex(ValueError, 'stale static module'):
            inspect()

    def test_reference_host_static_provider_cannot_substitute_for_selected_output(self):
        provider = self.write(self.libraries / 'host-provider', b'host bytes')
        report = self.write(self.root / 'proof.json', json.dumps({
            'schema': 1, 'passed': True, 'provider': {'path': str(provider), 'sha256': audit.sha(provider)},
            'runner': {'name': 'tamlinux-qml-provider', 'sourceDigest': 'a' * 64}, 'imports': []}))
        with self.assertRaisesRegex(ValueError, 'not a selected'):
            audit.inspect({'shell': self.output}, self.readelf, self.scanner,
                          [self.modules], [self.libraries], [report])

    def test_non_utf8_null_and_utf16_inherited_payloads_are_not_skipped(self):
        for data in (b"\xffOMARCHY", b"\0omarchy-command", "omarchy".encode("utf-16le")):
            self.write(self.output / "opaque.bin", data)
            self.assertFalse(self.inspect()["compiledPayloadPassed"])

    def test_elf_inherited_string_detected(self):
        self.write(self.output / "bin/helper", b"\x7fELF\xffomarchy")
        self.assertFalse(self.inspect()["compiledPayloadPassed"])

    def test_missing_readelf_metadata_fails(self):
        self.write(self.output / "bin/helper", b"\x7fELF\0")
        self.readelf = self.tool("readelf", "raise SystemExit(1)")
        self.assertFalse(self.inspect()["compiledPayloadPassed"])

    def test_missing_transitive_library_or_interpreter_fails(self):
        self.write(self.output / "bin/helper", b"\x7fELF\0")
        self.readelf = self.tool("readelf", "print('(NEEDED) Shared library: [libabsent.so]')")
        result = self.inspect()
        self.assertFalse(result["compiledPayloadPassed"])
        self.assertIn("unresolved dependency", result["compiledErrors"][0])
        self.readelf = self.tool("readelf", "print('[Requesting program interpreter: /unowned/ld.so]')")
        self.assertFalse(self.inspect()["compiledPayloadPassed"])
        self.readelf = self.tool("readelf", "print('(NEEDED) Shared library: [relative/libtest.so]')")
        self.assertFalse(self.inspect()["compiledPayloadPassed"])

    def test_resolved_libraries_are_scanned_and_symlink_escape_rejected(self):
        self.write(self.output / "bin/helper", b"\x7fELF\0")
        library = self.write(self.libraries / "libtest.so", b"\x7fELF\0omarchy")
        self.readelf = self.tool("readelf", "import sys\nprint('(NEEDED) Shared library: [libtest.so]' if sys.argv[-1].endswith('helper') else '')")
        result = self.inspect()
        self.assertFalse(result["compiledPayloadPassed"])
        self.assertIn(str(library), result["inheritedBinaryLocations"])
        library.unlink()
        target = self.write(self.root / "outside.so", b"\x7fELF\0")
        library.symlink_to(target)
        self.assertFalse(self.inspect()["compiledPayloadPassed"])

    def test_payload_directory_symlink_is_inspected_and_cycle_rejected(self):
        target = self.root / "external"
        self.write(target / "blob", b"\0omarchy")
        (self.output / "linked").symlink_to(target, target_is_directory=True)
        self.assertFalse(self.inspect()["compiledPayloadPassed"])
        (self.output / "loop").symlink_to(self.output, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.inspect()

    def test_unresolved_qml_scan_exit_zero_does_not_pass(self):
        self.scanner = self.tool("scanner", "print('[{\"name\":\"Missing.Module\",\"type\":\"module\"}]')")
        self.assertFalse(self.inspect()["resolvedQmlPassed"])

    def test_scanner_failure_empty_output_or_warning_fails(self):
        for code in ("raise SystemExit(1)", "print('[]')", "print('{}')",
                     "import sys\nprint('warning', file=sys.stderr)\nprint('[]')"):
            self.scanner = self.tool("scanner", code)
            self.assertFalse(self.inspect()["resolvedQmlPassed"])

    def test_undeclared_qml_root_and_missing_qmldir_fail(self):
        self.scanner = self.tool("scanner", "print(" + repr(json.dumps([
            {"type": "module", "name": "Host.Module", "path": str(self.root)}])) + ")")
        self.assertFalse(self.inspect()["resolvedQmlPassed"])
        self.setUpScanner()
        (self.module / "qmldir").unlink()
        self.assertFalse(self.inspect()["resolvedQmlPassed"])

    def setUpScanner(self, plugin=None):
        record = {"type": "module", "name": "Test.Module", "path": str(self.module)}
        if plugin:
            record.update(plugin=plugin, pluginIsOptional=True)
        self.scanner = self.tool("scanner", "print(" + repr(json.dumps([record])) + ")")

    def test_optional_plugin_is_not_implicit_static_provider_proof(self):
        self.setUpScanner("testplugin")
        self.assertFalse(self.inspect()["resolvedQmlPassed"])
        self.write(self.module / "libtestplugin.so", b"\x7fELF\0")
        self.assertTrue(self.inspect()["resolvedQmlPassed"])
        (self.module / "libtestplugin.so").unlink()
        target = self.write(self.root / "outside.so", b"\x7fELF\0")
        (self.module / "libtestplugin.so").symlink_to(target)
        self.assertFalse(self.inspect()["resolvedQmlPassed"])

    def test_no_qml_or_no_import_roots_cannot_pass(self):
        (self.output / "main.qml").unlink()
        self.assertFalse(self.inspect()["resolvedQmlPassed"])
        result = audit.inspect({"shell": self.output}, self.readelf, self.scanner, [], [])
        self.assertFalse(result["resolvedQmlPassed"])

    def test_cli_partial_report_cannot_claim_I03_pass(self):
        report, check = self.root / "audit.json", self.root / "check.json"
        argv = [sys.executable, str(SCRIPT), "--output", "shell=" + str(self.output),
                "--readelf", str(self.readelf), "--qml-scanner", str(self.scanner),
                "--qml-root", str(self.modules), "--report", str(report),
                "--tuple-digest", "a" * 64, "--check-report", str(check)]
        result = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(check.read_text())["status"], "blocked")
        result = subprocess.run(argv + ["--output", "shell=" + str(self.output)], capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_real_readelf_rejects_invalid_elf_and_records_compiled_library(self):
        readelf = shutil.which("readelf")
        cc = shutil.which("cc")
        if not readelf or not cc:
            self.skipTest("Needs native or Nix check compiler/readelf")
        self.readelf = Path(readelf)
        self.write(self.output / "bad.so", b"\x7fELF\0invalid")
        self.assertFalse(self.inspect()["compiledPayloadPassed"])
        (self.output / "bad.so").unlink()
        source = self.write(self.root / "tiny.c", 'const char *identity = "tamlinux";\n')
        target = self.output / "tiny.so"
        subprocess.run([cc, "-shared", "-nostdlib", "-o", str(target), str(source)], check=True,
                       capture_output=True)
        result = self.inspect()
        self.assertTrue(result["compiledPayloadPassed"], result["compiledErrors"])
        self.assertEqual(result["elf"][0]["needed"], [])
        source.write_text('const char *identity = "omarchy";\n')
        subprocess.run([cc, "-shared", "-nostdlib", "-o", str(target), str(source)], check=True,
                       capture_output=True)
        self.assertFalse(self.inspect()["compiledPayloadPassed"])


if __name__ == "__main__":
    unittest.main()
