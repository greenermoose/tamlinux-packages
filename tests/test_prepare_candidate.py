"""tools/prepare-candidate.py: exact pins, unused versions, kept records, no promotion."""
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/prepare-candidate.py"
spec = importlib.util.spec_from_file_location("prepare", SCRIPT)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)

OLD, NEW, PARENT = "1" * 40, "2" * 40, "3" * 40

# A stand-in for nix: `flake update` copies flake.nix revisions into the lock;
# `build --json` reports one output per target. It logs every call.
FAKE_NIX = r'''
import json, os, re, sys
from pathlib import Path
with open(os.environ["FAKE_NIX_LOG"], "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\n")
args = sys.argv[1:]
if args[:2] == ["flake", "update"]:
    lock = json.loads(Path("flake.lock").read_text())
    text = Path("flake.nix").read_text()
    for name in args[2:]:
        node = lock["nodes"][name]
        rev = re.search(rf'github:{node["original"]["owner"]}/{node["original"]["repo"]}/([0-9a-f]{{40}})', text).group(1)
        node["locked"]["rev"] = node["original"]["rev"] = rev
    Path("flake.lock").write_text(json.dumps(lock))
elif args[:1] == ["build"]:
    if os.environ.get("FAKE_NIX_FAIL"):
        print("boom", file=sys.stderr); sys.exit(3)
    targets = [a for a in args if a.startswith(".#")]
    print(json.dumps([{"drvPath": f"/nix/store/{i}.drv", "outputs": {"out": f"/nix/store/{i}"},
                       "startTime": 1} for i, _ in enumerate(targets)]))
'''


def node(owner, repo, rev):
    return {"flake": False, "locked": {"owner": owner, "repo": repo, "rev": rev, "type": "github",
                                       "narHash": "sha256-x", "lastModified": 1},
            "original": {"owner": owner, "repo": repo, "rev": rev, "type": "github"}}


class PrepareCandidate(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.root = self.temp / "assembly"
        (self.root / "deliveries").mkdir(parents=True)
        (self.root / "VERSION").write_text("0.4.4-b\n")
        (self.root / "deliveries/tamlinux-0.4.4-b.json").write_text('{"kept": true}\n')
        (self.root / "flake.nix").write_text(
            f'{{ inputs.tamlinux.url = "github:greenermoose/tamlinux/{OLD}";\n'
            f'  inputs.tam.url = "github:greenermoose/tam/{OLD}"; }}\n')
        (self.root / "flake.lock").write_text(json.dumps({"root": "root", "nodes": {
            "root": {"inputs": {"tamlinux": "tamlinux", "tam": "tam"}},
            "tamlinux": node("greenermoose", "tamlinux", OLD), "tam": node("greenermoose", "tam", OLD)}}))
        fake = self.temp / "nix"
        fake.write_text(f"#!{sys.executable}\n{FAKE_NIX}")
        fake.chmod(0o755)
        self.log = self.temp / "nix.log"
        self.env = os.environ | {"PREPARE_CANDIDATE_NIX": str(fake), "FAKE_NIX_LOG": str(self.log),
                                 "XDG_STATE_HOME": str(self.temp / "state")}

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],
                              env=self.env, capture_output=True, text=True, timeout=30)

    def ok(self, *args):
        result = self.run_tool(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def refused(self, message, *args):
        result = self.run_tool(*args)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)

    def test_full_preparation_records_the_lock_and_build(self):
        self.ok("version", "0.4.4-c")
        self.ok("pin", f"tamlinux={NEW}")
        self.assertIn(f"tamlinux/{NEW}", (self.root / "flake.nix").read_text())
        self.assertIn(f"tam/{OLD}", (self.root / "flake.nix").read_text())
        self.ok("build")
        evidence = self.temp / "state/tamlinux/candidates/0.4.4-c/build.json"
        self.assertEqual(len(json.loads(evidence.read_text())["outputs"]), len(prepare.DEFAULT_TARGETS))
        extra = self.temp / "extra.json"
        extra.write_text(json.dumps({"verification": {"desktopTests": "pass"}, "retainedSoftware": "0.4.4-b"}))
        self.ok("record", "--parent", PARENT, "--scope", "b plus a fix", "--extra", str(extra))
        record = json.loads((self.root / "deliveries/tamlinux-0.4.4-c.json").read_text())
        self.assertEqual((record["id"], record["parentAssembly"], record["scope"]),
                         ("tamlinux-0.4.4-c", PARENT, "b plus a fix"))
        self.assertEqual(record["components"]["tamlinux"]["rev"], NEW)
        self.assertEqual(record["outputs"][0], {"drvPath": "/nix/store/0.drv", "outputs": {"out": "/nix/store/0"}})
        self.assertEqual(record["verification"]["desktopTests"], "pass")
        self.assertEqual(record["retainedSoftware"], "0.4.4-b")
        self.assertIn("Not performed", record["activation"])
        self.assertEqual(self.run_tool("check", "--product", str(self.temp / "no-checkout")).returncode, 0)
        # Nothing but flake update and build ever ran: no switch, push or deploy.
        calls = [line.split()[0] for line in self.log.read_text().splitlines()]
        self.assertEqual(set(calls), {"flake", "build"})

    def test_versions_are_never_reused_or_moved_backwards(self):
        self.refused("already has a delivery record", "version", "0.4.4-b")
        self.refused("does not come after", "version", "0.4.4-a")
        self.refused("not X.Y.Z", "version", "0.4.4c")
        self.refused("already has lettered candidates", "version", "0.4.4")
        self.assertEqual((self.root / "VERSION").read_text(), "0.4.4-b\n")

    def test_letters_end_at_0_4_5(self):
        self.refused("letters ended at 0.4.5", "version", "0.4.5-a")
        self.refused("letters ended at 0.4.5", "version", "0.5.0-a")
        self.ok("version", "0.4.4-c")  # Letters below 0.4.5 still work.

    def test_plain_patch_numbers_follow_the_letters(self):
        self.ok("version", "0.4.5")
        self.assertEqual((self.root / "VERSION").read_text(), "0.4.5\n")
        (self.root / "deliveries/tamlinux-0.4.5.json").write_text('{"kept": true}\n')
        self.refused("already has a delivery record", "version", "0.4.5")
        self.refused("does not come after", "version", "0.4.4-c")
        self.ok("version", "0.4.6")

    def test_pins_must_be_exact_known_inputs(self):
        self.refused("exact 40-character", "pin", "tamlinux=develop")
        self.refused("exact 40-character", "pin", "tamlinux=abc123")
        self.refused("INPUT one of", "pin", f"nope={NEW}")
        self.assertIn(OLD, (self.root / "flake.nix").read_text())
        self.assertFalse(self.log.exists())

    def test_existing_record_is_kept(self):
        self.refused("is kept", "record", "--parent", PARENT, "--scope", "x")
        self.assertEqual((self.root / "deliveries/tamlinux-0.4.4-b.json").read_text(), '{"kept": true}\n')

    def test_record_needs_matching_build_evidence_and_protects_fields(self):
        self.ok("version", "0.4.4-c")
        self.refused("run build first", "record", "--parent", PARENT, "--scope", "x")
        self.refused("--parent must be", "record", "--parent", "HEAD", "--scope", "x")
        self.ok("build")
        extra = self.temp / "extra.json"
        extra.write_text(json.dumps({"components": {}}))
        self.refused("may not replace components", "record", "--parent", PARENT, "--scope", "x", "--extra", str(extra))

    def test_failed_build_keeps_its_log_outside_the_repository(self):
        self.ok("version", "0.4.4-c")
        self.env["FAKE_NIX_FAIL"] = "1"
        self.refused("build failed", "build")
        log = self.temp / "state/tamlinux/candidates/0.4.4-c/build.log"
        self.assertIn("boom", log.read_text())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["VERSION", "deliveries", "flake.lock", "flake.nix"])

    def test_056_requires_a_verified_native_archive_before_recording(self):
        self.ok('version', '0.5.6')
        self.ok('build')
        self.refused('requires its matching native package', 'record', '--parent', PARENT, '--scope', 'welcome')
        extra = self.temp / 'native.json'
        extra.write_text(json.dumps({'readiness': {'nativeInstallationRequired': True}}))
        self.refused('requires --native-archive', 'record', '--parent', PARENT, '--scope', 'welcome', '--extra', str(extra))
        self.assertFalse((self.root/'deliveries/tamlinux-0.5.6.json').exists())

    def test_056_records_only_matching_native_archive(self):
        self.ok('version', '0.5.6'); self.ok('build')
        archive = self.temp/'tamlinux-native.pkg.tar'
        files = {'.PKGINFO': b'pkgname = tamlinux-native\npkgver = 0.5.6-0.1\n',
                 'usr/share/tamlinux/native-integration.json': json.dumps({'productRevision': OLD}).encode(),
                 'usr/lib/issue.d/70-tamlinux.issue': b'Welcome to Tamlinux!\nCultivar: Blue Sparkler 0.5.6\n'}
        with tarfile.open(archive, 'w') as tar:
            for name, data in files.items():
                entry = tarfile.TarInfo(name); entry.size = len(data)
                tar.addfile(entry, io.BytesIO(data))
        extra = self.temp/'native.json'
        extra.write_text(json.dumps({'readiness': {'nativeInstallationRequired': True},
                                    'nativePackage': {'name': 'tamlinux-native', 'version': '0.5.6-0.1',
                                                      'archive': archive.name, 'productRevision': OLD,
                                                      'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}}))
        self.ok('record', '--parent', PARENT, '--scope', 'welcome', '--extra', str(extra), '--native-archive', str(archive))
        self.assertEqual(json.loads((self.root/'deliveries/tamlinux-0.5.6.json').read_text())['nativePackage']['productRevision'], OLD)

    def test_check_finds_drift(self):
        (self.root / "flake.nix").write_text((self.root / "flake.nix").read_text().replace(f"tamlinux/{OLD}", f"tamlinux/{NEW}"))
        result = self.run_tool("check", "--product", str(self.temp / "no-checkout"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("flake.nix pins", result.stdout)


if __name__ == "__main__":
    unittest.main()
