"""Falsify readiness with absent outputs, hidden menu calls and polluted hosts."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/clean-host-audit.py"
spec = importlib.util.spec_from_file_location("audit", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract = {"schema": 1, "target": "arch-hyprland", "outputs": ["shell", "commands"],
                         "native": [{"package": "bash", "binaries": ["bash"]}],
                         "pending": [], "forbiddenPackages": ["omarchy"],
                         "deferredAbsoluteTools": ["/usr/bin/swaymsg"]}
        self.outputs = {name: self.root / name for name in self.contract["outputs"]}
        for path in self.outputs.values():
            path.mkdir()

    def write(self, path, text, executable=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if executable:
            path.chmod(0o755)
        return path

    def run_audit(self, **kwargs):
        return module.audit(self.contract, self.outputs, **kwargs)

    def menu(self, text):
        return self.write(self.outputs["shell"] / "share/tamlinux/menu/default.jsonc", text)

    def test_minimal_complete_fixture(self):
        self.assertTrue(self.run_audit()["candidateReady"])

    def test_second_launcher_argument_and_conditions_are_required(self):
        self.menu('{"action": "tam-launch-tui tam-missing", "when": "tam-hw-laptop"}')
        self.write(self.outputs["commands"] / "bin/tam-launch-tui", "#!/bin/bash\n", True)
        result = self.run_audit()
        self.assertFalse(result["candidateReady"])
        self.assertEqual(set(result["missingPackageCommands"]), {"tam-missing", "tam-hw-laptop"})

    def test_personal_path_does_not_supply_missing_command(self):
        self.menu('{"action": "tam-private"}')
        personal = self.write(self.root / "personal/tam-private", "#!/bin/bash\n", True)
        old_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = str(personal.parent)
            self.assertIn("tam-private", self.run_audit()["missingPackageCommands"])
        finally:
            os.environ["PATH"] = old_path

    def test_session_lua_and_native_configuration_are_audited(self):
        self.write(self.outputs["shell"] / "share/tamlinux/session/autostart.lua",
                   '-- Omarchy ancestry\nhl.exec_cmd("tam-unprovided")\n')
        self.write(self.outputs["shell"] / "share/wayland-sessions/tamlinux.desktop",
                   '[Desktop Entry]\nExec=/usr/bin/unprovided\n')
        result = self.run_audit()
        self.assertEqual(result["filesScanned"], 2)
        self.assertIn("tam-unprovided", result["missingPackageCommands"])
        self.assertIn("/usr/bin/unprovided", result["undeclaredAbsoluteTools"])
        self.assertEqual(result["inheritedIdentifierLocations"], [])

    def test_non_executable_installed_file_does_not_supply_command(self):
        self.menu('{"action": "tam-missing"}')
        self.write(self.outputs["commands"] / "bin/tam-missing", "not executable")
        self.assertIn("tam-missing", self.run_audit()["missingPackageCommands"])

    def test_missing_output_blocks_empty_scan(self):
        del self.outputs["commands"]
        self.assertEqual(self.run_audit()["missingOutputs"], ["commands"])
        self.assertFalse(self.run_audit()["candidateReady"])

    def test_empty_output_directory_does_not_supply_declared_payload(self):
        self.contract["requiredFiles"] = {"shell": ["share/tamlinux/menu/default.jsonc"]}
        self.contract["requiredExecutables"] = {"commands": ["bin/tam-shell"]}
        result = self.run_audit()
        self.assertEqual(len(result["missingOutputFiles"]), 2)
        self.assertFalse(result["candidateReady"])

    def test_pending_work_blocks_apparently_complete_outputs(self):
        self.contract["pending"] = [{"id": "fonts"}]
        self.assertFalse(self.run_audit()["candidateReady"])

    def test_runtime_inherited_name_and_domain_block_readiness(self):
        self.menu('// Omarchy ancestry is preserved\n{"action": "omarchy-launch-about",\n'
                  '"server": "https://omarchy.org/data"}\n')
        result = self.run_audit()
        self.assertEqual(len(result["inheritedIdentifierLocations"]), 2)
        self.assertFalse(result["candidateReady"])

    def test_tests_docs_licenses_and_comment_ancestry_are_excluded(self):
        self.menu('// Omarchy ancestry\n{}\n')
        for name in ["tests/x.py", "docs/x.js", "LICENSE-omarchy"]:
            self.write(self.outputs["shell"] / name, '"omarchy-inherited"')
        self.assertEqual(self.run_audit()["inheritedIdentifierLocations"], [])

    def test_wrapped_bodies_templates_and_extensionless_files_are_scanned(self):
        shell = self.outputs["shell"] / "share/tamlinux"
        self.write(shell / "services/clipboard/.open.sh-wrapped", 'open "$OMARCHY_X"\n', executable=True)
        self.write(shell / "templates/claude.json.tpl", '{"name": "Omarchy"}\n')
        self.write(shell / "session/uwsm-env", 'unset OMARCHY_PATH\n')
        self.write(shell / "screensaver/foot.ini", '; Omarchy ancestry\n# Omarchy ancestry\n[main]\n')
        result = self.run_audit()
        self.assertEqual(result["inheritedIdentifierLocations"], [
            "shell:share/tamlinux/services/clipboard/.open.sh-wrapped:1",
            "shell:share/tamlinux/session/uwsm-env:1",
            "shell:share/tamlinux/templates/claude.json.tpl:1"])
        self.assertFalse(result["candidateReady"])

    def test_inherited_file_names_block_readiness_except_licenses_and_tests(self):
        assets = self.outputs["commands"] / "share/tamlinux/assets"
        (assets / "themes/x/backgrounds").mkdir(parents=True)
        (assets / "themes/x/backgrounds/2-omarchy.png").write_bytes(b"\x89PNG")
        self.write(assets / "LICENSE-omarchy", "MIT")
        self.write(self.outputs["shell"] / "tests/test_no_omarchy.py", "")
        result = self.run_audit()
        self.assertEqual(result["inheritedFileNames"],
                         ["commands:share/tamlinux/assets/themes/x/backgrounds/2-omarchy.png"])
        self.assertEqual(result["inheritedIdentifierLocations"], [])
        self.assertFalse(result["candidateReady"])

    def test_undeclared_absolute_binary_requires_host_owner(self):
        self.menu('{"action": "/usr/bin/bash /usr/bin/unowned /usr/bin/swaymsg"}')
        result = self.run_audit()
        self.assertEqual(set(result["undeclaredAbsoluteTools"]), {"/usr/bin/unowned"})
        self.assertEqual(result["deferredAbsoluteTools"], ["/usr/bin/swaymsg"])

    def test_embedded_helper_is_reported_separately_from_path_commands(self):
        self.outputs["plugins"] = self.root / "plugins"
        self.menu('{"action": "tam-desktop-mode"}')
        self.write(self.outputs["plugins"] / "share/tamlinux/plugins/fred.workspaces/tam-desktop-mode",
                   "#!/usr/bin/bash\n", True)
        result = self.run_audit()
        self.assertIn("tam-desktop-mode", result["embeddedHelpers"])
        self.assertNotIn("tam-desktop-mode", result["availableCommands"])

    def test_host_binary_and_forbidden_package(self):
        host = self.root / "host"
        self.write(host / "var/lib/pacman/local/omarchy-1/desc", "%NAME%\nomarchy\n")
        result = self.run_audit(host_root=host)
        self.assertEqual(result["host"]["forbiddenPackages"], ["omarchy"])
        self.assertEqual(result["host"]["requiredBinariesMissing"][0]["binary"], "bash")
        self.assertFalse(result["candidateReady"])

    def test_owned_lib_executable_is_declared_and_inspected_at_its_actual_image_path(self):
        host = self.root / 'host'
        self.write(host / 'usr/bin/bash', 'fixture', True)
        self.write(self.outputs['commands'] / 'bin/control', '#!/bin/sh\n/usr/lib/tamlinux/asdcontrol --help\n', True)
        self.assertIn('/usr/lib/tamlinux/asdcontrol', self.run_audit()['undeclaredAbsoluteTools'])
        self.contract['native'].append({'package': 'tamlinux-native', 'binaries': [],
                                       'executablePaths': ['/usr/lib/tamlinux/asdcontrol']})
        result = self.run_audit(host_root=host)
        self.assertFalse(result['undeclaredAbsoluteTools'])
        self.assertEqual(result['host']['requiredBinariesMissing'][0]['binary'], '/usr/lib/tamlinux/asdcontrol')
        # An older provider at the former pathname cannot satisfy the new owner.
        self.write(host / 'usr/bin/asdcontrol', 'old provider', True)
        self.assertFalse(self.run_audit(host_root=host)['candidateReady'])
        self.write(host / 'usr/lib/tamlinux/asdcontrol', 'owned provider', True)
        self.assertTrue(self.run_audit(host_root=host)['candidateReady'])

    def test_owned_native_path_inventory_refuses_escape_and_other_host_roots(self):
        for path in ['/usr/lib/tamlinux/../../bin/bash', '/root/private', '/usr/lib/tamlinux/']:
            with self.assertRaises(ValueError):module.native_executables({'binaries': [], 'executablePaths': [path]})

    def test_optional_missing_native_binary_is_reported_without_blocking(self):
        host = self.root / "host"
        self.write(host / "usr/bin/bash", "fixture", True)
        self.contract["native"].append({"package": "optional", "binaries": ["optional"], "optional": True})
        result = self.run_audit(host_root=host)
        self.assertTrue(result["candidateReady"])
        self.assertEqual(result["host"]["optionalBinariesMissing"][0]["binary"], "optional")

    def test_absolute_image_symlink_cannot_use_auditor_host(self):
        host = self.root / "host"
        path = host / "usr/bin/bash"
        path.parent.mkdir(parents=True)
        path.symlink_to("/bin/bash")
        self.assertFalse(module.rooted_executable(host, path))
        self.write(host / "bin/bash", "fixture", True)
        self.assertTrue(module.rooted_executable(host, path))

    def test_image_directory_symlink_is_root_relative(self):
        host = self.root / "host"
        (host / "usr").mkdir(parents=True)
        (host / "usr/bin").symlink_to("/bin")
        self.assertFalse(module.rooted_executable(host, host / "usr/bin/bash"))
        self.write(host / "bin/bash", "fixture", True)
        self.assertTrue(module.rooted_executable(host, host / "usr/bin/bash"))

    def test_symlink_escape_and_cycle_fail_closed(self):
        host = self.root / "host"
        (host / "usr/bin").mkdir(parents=True)
        (host / "usr/bin/bash").symlink_to("../../../outside")
        (host / "usr/bin/cycle").symlink_to("cycle")
        self.write(self.root / "outside", "fixture", True)
        self.assertFalse(module.rooted_executable(host, host / "usr/bin/bash"))
        self.assertFalse(module.rooted_executable(host, host / "usr/bin/cycle"))

    def test_cli_blocked_report_and_invalid_output(self):
        contract = self.write(self.root / "contract.json", json.dumps(self.contract))
        result = subprocess.run([sys.executable, str(SCRIPT), "--contract", str(contract)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["candidateReady"])
        bad = subprocess.run([sys.executable, str(SCRIPT), "--output", "shell=/does-not-exist"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)

    def test_compact_groups_partition_missing_names_without_dropping_blockers(self):
        self.menu('{"action": "tam-menu-only tam-shared"}')
        self.write(self.outputs["commands"] / "bin/tam-caller",
                   '#!/bin/bash\ntam-shared tam-transitive\n', True)
        result = self.run_audit()
        compact = module.compact_report(result)
        self.assertIn('Menu only (1): tam-menu-only', compact)
        self.assertIn('Menu and other callers (1): tam-shared', compact)
        self.assertIn('Other callers (1): tam-transitive', compact)
        self.assertIn('Inventory ready: false', compact)
        self.assertIn('Host: not inspected', compact)

    def test_compact_cli_retains_identical_complete_evidence_and_exit(self):
        self.menu('{"action": "tam-missing", "font": "omarchy"}')
        contract = self.write(self.root / "contract.json", json.dumps(self.contract))
        args = [sys.executable, str(SCRIPT), '--contract', str(contract)]
        for name, path in self.outputs.items():
            args += ['--output', f'{name}={path}']
        full = subprocess.run(args, capture_output=True, text=True)
        report = self.root / 'evidence.json'
        short = subprocess.run(args + ['--format', 'compact', '--report', str(report)],
                               capture_output=True, text=True)
        self.assertEqual(short.returncode, full.returncode)
        self.assertEqual(json.loads(report.read_text()), json.loads(full.stdout))
        self.assertIn('Inherited identifier locations: 1', short.stdout)

    def test_compact_reports_optional_host_and_required_blockers(self):
        host = self.root / 'host'
        self.contract['native'].append({'package': 'extra', 'binaries': ['extra'], 'optional': True})
        self.write(host / 'var/lib/pacman/local/omarchy-1/desc', '%NAME%\nomarchy\n')
        compact = module.compact_report(self.run_audit(host_root=host))
        self.assertIn('Missing required host binaries: 1', compact)
        self.assertIn('Missing optional host binaries: 1', compact)
        self.assertIn('Forbidden host packages: 1', compact)

    def test_compact_ready_and_invalid_evidence_destination(self):
        contract = self.write(self.root / 'contract.json', json.dumps(self.contract))
        args = [sys.executable, str(SCRIPT), '--contract', str(contract), '--format', 'compact']
        for name, path in self.outputs.items():
            args += ['--output', f'{name}={path}']
        ready = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(ready.returncode, 0)
        self.assertIn('Inventory ready: true', ready.stdout)
        bad = subprocess.run(args + ['--report', str(self.root / 'absent/evidence.json')],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
