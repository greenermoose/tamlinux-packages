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
    if any('#homeConfigurations.' in value for value in args):
        print('/nix/store/' + 'a' * 32 + '-home-manager-generation')
        sys.exit(0)
    targets = [a for a in args if a.startswith(".#")]
    print(json.dumps([{"drvPath": f"/nix/store/{i}.drv", "outputs": {"out": f"/nix/store/{i}"},
                       "startTime": 1} for i, _ in enumerate(targets)]))
elif args[:1] == ['path-info']:
    if os.environ.get('FAKE_MISSING_OUTPUT'):sys.exit(1)
    targets=[a for a in args if a.startswith('git+file://')]
    if targets:print('\n'.join(f'/nix/store/{i}' for i,_ in enumerate(targets)))
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
        self.product = self.temp / "product"
        (self.product / 'desktop/tests').mkdir(parents=True)
        for test in prepare.FOCUSED_TESTS:
            (self.product / 'desktop/tests' / test).write_text('import unittest\nclass Check(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n')
        subprocess.run(['git', 'init', '-q', str(self.product)], check=True)
        subprocess.run(['git', '-C', str(self.product), 'config', 'user.name', 'Fixture'], check=True)
        subprocess.run(['git', '-C', str(self.product), 'config', 'user.email', 'fixture@example.invalid'], check=True)
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
        if args[0] == 'build':
            # Produce a real commit at the pinned revision, as ordinary
            # candidate preparation does before entering the build phase.
            version = (self.root / 'VERSION').read_text()
            (self.product / 'VERSION').write_text(version)
            subprocess.run(['git', '-C', str(self.product), 'add', '--', 'VERSION', 'desktop/tests'], check=True)
            subprocess.run(['git', '-C', str(self.product), 'commit', '-q', '--allow-empty', '-m', 'Pinned product'], check=True)
            rev = subprocess.check_output(['git', '-C', str(self.product), 'rev-parse', 'HEAD'], text=True).strip()
            lock = json.loads((self.root / 'flake.lock').read_text())
            old = lock['nodes']['tamlinux']['locked']['rev']
            lock['nodes']['tamlinux']['locked']['rev'] = rev
            (self.root / 'flake.lock').write_text(json.dumps(lock))
            (self.root / 'flake.nix').write_text((self.root / 'flake.nix').read_text().replace('tamlinux/' + old, 'tamlinux/' + rev))
            self.product_rev = rev
            self.ok('verify', '--product', str(self.product))
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
        self.assertEqual(record["components"]["tamlinux"]["rev"], self.product_rev)
        self.assertEqual(record["outputs"][0], {"drvPath": "/nix/store/0.drv", "outputs": {"out": "/nix/store/0"}})
        self.assertEqual(record["verification"]["desktopTests"], "pass")
        self.assertEqual(record["retainedSoftware"], "0.4.4-b")
        self.assertIn("Not performed", record["activation"])
        self.assertEqual(self.run_tool("check", "--product", str(self.temp / "no-checkout")).returncode, 1)
        # Nothing but flake update and build ever ran: no switch, push or deploy.
        calls = [line.split()[0] for line in self.log.read_text().splitlines()]
        self.assertEqual(set(calls), {"flake", "build", "path-info"})

    def test_version_only_change_reuses_checks_but_source_change_invalidates(self):
        self.ok('version', '0.4.4-c');self.ok('build')
        (self.product/'VERSION').write_text('0.4.4-d\n')
        (self.product/'README.md').write_text('documentation only\n')
        subprocess.run(['git','-C',str(self.product),'add','--','VERSION','README.md'],check=True)
        subprocess.run(['git','-C',str(self.product),'commit','-qm','Candidate metadata'],check=True)
        rev=subprocess.check_output(['git','-C',str(self.product),'rev-parse','HEAD'],text=True).strip()
        self.ok('version','0.4.4-d');self.ok('pin','tamlinux='+rev)
        result=self.ok('verify','--product',str(self.product))
        self.assertIn('reusing focused checks',result.stdout)
        test=self.product/'desktop/tests'/prepare.FOCUSED_TESTS[0]
        test.write_text(test.read_text()+'\n# changed test policy\n')
        subprocess.run(['git','-C',str(self.product),'add','--','desktop/tests'],check=True)
        subprocess.run(['git','-C',str(self.product),'commit','-qm','Change focused check'],check=True)
        rev=subprocess.check_output(['git','-C',str(self.product),'rev-parse','HEAD'],text=True).strip()
        self.ok('pin','tamlinux='+rev)
        self.assertNotIn('reusing focused checks',self.ok('verify','--product',str(self.product)).stdout)

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
        self.ok('build')
        self.env["FAKE_NIX_FAIL"] = "1"
        (self.root / "flake.nix").write_text((self.root / "flake.nix").read_text() + "\n# changed recipe\n")
        self.ok("verify", "--product", str(self.product))
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
                 'usr/share/tamlinux/native-integration.json': json.dumps({'productRevision': self.product_rev}).encode(),
                 'usr/lib/issue.d/70-tamlinux.issue': b'Welcome to Tamlinux!\nCultivar: Blue Sparkler 0.5.6\n'}
        with tarfile.open(archive, 'w') as tar:
            for name, data in files.items():
                entry = tarfile.TarInfo(name); entry.size = len(data)
                tar.addfile(entry, io.BytesIO(data))
        extra = self.temp/'native.json'
        extra.write_text(json.dumps({'readiness': {'nativeInstallationRequired': True},
                                    'nativePackage': {'name': 'tamlinux-native', 'version': '0.5.6-0.1',
                                                      'archive': archive.name, 'productRevision': self.product_rev,
                                                      'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}}))
        self.ok('record', '--parent', PARENT, '--scope', 'welcome', '--extra', str(extra), '--native-archive', str(archive))
        self.assertEqual(json.loads((self.root/'deliveries/tamlinux-0.5.6.json').read_text())['nativePackage']['productRevision'], self.product_rev)

    def test_stale_recipes_and_missing_outputs_cannot_be_recorded(self):
        self.ok('version', '0.4.4-c')
        self.ok('build')
        evidence = self.temp / 'state/tamlinux/candidates/0.4.4-c/build.json'
        before = json.loads(evidence.read_text())
        changed = dict(before, targets=before['targets'][:-1])
        evidence.write_text(json.dumps(changed))
        self.refused('missing required targets', 'record', '--parent', PARENT, '--scope', 'x')
        evidence.write_text(json.dumps(before))
        (self.root / 'nix').mkdir()
        (self.root / 'nix/recipe.nix').write_text('{ changed = true; }')
        self.refused('stale or unbound', 'record', '--parent', PARENT, '--scope', 'x')

    def test_missing_focused_checks_refuse_before_build(self):
        self.ok('version', '0.4.4-c')
        self.refused('focused checks are missing', 'build')
        self.assertFalse(self.log.exists())

    def test_unavailable_outputs_and_overridden_checks_refuse_recording(self):
        self.ok('version', '0.4.4-c')
        self.ok('build')
        self.env['FAKE_MISSING_OUTPUT'] = '1'
        self.refused('outputs are unavailable', 'record', '--parent', PARENT, '--scope', 'x')
        self.env.pop('FAKE_MISSING_OUTPUT')
        extra = self.temp / 'extra.json'
        extra.write_text(json.dumps({'verification': {'fingerprint': 'invented'}}))
        self.refused('required verification evidence', 'record', '--parent', PARENT, '--scope', 'x', '--extra', str(extra))

    def test_unchanged_checks_are_reused_and_prepare_records_all_ten(self):
        self.ok('version', '0.4.4-c')
        self.ok('build')
        result = self.ok('prepare', '--product', str(self.product), '--parent', PARENT, '--scope', 'x',
                         '--skip-fleet-profiles')
        self.assertIn('reusing focused checks', result.stdout)
        record = json.loads((self.root/'deliveries/tamlinux-0.4.4-c.json').read_text())
        self.assertEqual(len(record['verification']['builtTargets']), 10)
        self.assertEqual(len(record['verification']['focusedChecks']['tests']), 3)

    def test_check_finds_drift(self):
        (self.root / "flake.nix").write_text((self.root / "flake.nix").read_text().replace(f"tamlinux/{OLD}", f"tamlinux/{NEW}"))
        result = self.run_tool("check", "--product", str(self.temp / "no-checkout"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("flake.nix pins", result.stdout)

    def fleet_consumer(self):
        consumer = self.temp / 'consumer'
        (consumer / 'system').mkdir(parents=True, exist_ok=True)
        (consumer / 'flake.nix').write_text('{ homeConfigurations = {}; }\n')
        return consumer

    def commit_assembly_fixture(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), 'config', 'user.name', 'Fixture'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'config', 'user.email', 'fixture@example.invalid'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '--', 'VERSION', 'flake.nix', 'flake.lock'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'commit', '-qm', 'Fixture assembly'], check=True)

    def test_fleet_profiles_read_operator_values_from_local_consumer(self):
        consumer = self.fleet_consumer()
        profiles = ['alex@portable-a', 'sam@portable-b']
        (consumer / 'system/fleet-profiles.json').write_text(json.dumps({'profiles': profiles}))
        self.commit_assembly_fixture()
        self.ok('fleet-profiles', '--consumer', str(consumer))
        evidence = self.temp / 'state/tamlinux/candidates/0.4.4-b/fleet-profiles.json'
        receipt = json.loads(evidence.read_text())
        self.assertEqual([item['profile'] for item in receipt['profiles']], profiles)
        calls = self.log.read_text().splitlines()
        self.assertEqual(len(calls), 2)
        for profile, call in zip(profiles, calls):
            self.assertIn(f'{consumer}#homeConfigurations.{profile}.activationPackage', call)
        self.assertEqual(len(list((self.root / 'deliveries').iterdir())), 1)

    def test_explicit_fleet_profiles_override_even_unreadable_defaults(self):
        consumer = self.fleet_consumer()
        self.commit_assembly_fixture()
        for defaults in (None, 'malformed JSON'):
            if defaults is not None:
                (consumer / 'system/fleet-profiles.json').write_text(defaults)
            self.ok('fleet-profiles', '--consumer', str(consumer), '--profile', 'alex@override')
        calls = self.log.read_text().splitlines()
        self.assertEqual(len(calls), 2)
        self.assertTrue(all('#homeConfigurations.alex@override.activationPackage' in call for call in calls))

    def test_missing_fleet_defaults_stop_before_build(self):
        consumer = self.fleet_consumer()
        self.refused('no default fleet profiles', 'fleet-profiles', '--consumer', str(consumer))
        self.assertFalse(self.log.exists())

    def test_bad_fleet_defaults_stop_before_build(self):
        consumer = self.fleet_consumer()
        path = consumer / 'system/fleet-profiles.json'
        for value in ({}, {'profiles': []}, {'profiles': ['']}, {'profiles': [None]},
                      {'profiles': 'alex@portable'}, ['alex@portable']):
            with self.subTest(value=value):
                path.write_text(json.dumps(value))
                self.refused('nonempty list', 'fleet-profiles', '--consumer', str(consumer))
        path.write_text('{')
        self.refused('cannot read default fleet profiles', 'fleet-profiles', '--consumer', str(consumer))
        self.assertFalse(self.log.exists())

    def test_prepare_checks_local_fleet_defaults_before_freezing_or_building(self):
        consumer = self.fleet_consumer()
        baseline = {name: (self.root / name).read_bytes() for name in ('VERSION', 'flake.nix', 'flake.lock')}
        self.refused('no default fleet profiles', 'prepare', '--consumer', str(consumer),
                     '--parent', PARENT, '--scope', 'fixture')
        self.assertFalse(self.log.exists())
        self.assertEqual(baseline, {name: (self.root / name).read_bytes() for name in baseline})
        self.assertEqual(len(list((self.root / 'deliveries').iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
