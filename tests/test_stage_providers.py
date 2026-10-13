import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('stage_providers', Path(__file__).parents[1] / 'tools/stage-providers.py')
stage_providers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage_providers)


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bsdtar = Path(shutil.which('bsdtar') or '/nonexistent')
        cls.gpgv = Path(shutil.which('gpgv') or '/nonexistent')
        cls.gpg = Path(shutil.which('gpg') or '/nonexistent')
        if not all(p.is_file() for p in [cls.bsdtar, cls.gpgv, cls.gpg]):
            raise RuntimeError('Provider tests require libarchive and GnuPG')
        cls.keys = tempfile.TemporaryDirectory()
        cls.keyhome = Path(cls.keys.name)
        cls.keyhome.chmod(0o700)
        cls.command(['--batch', '--passphrase', '', '--quick-generate-key',
                     'Provider fixture <fixture@example.invalid>', 'ed25519', 'sign', '0'])
        listing = cls.command(['--with-colons', '--list-keys']).stdout.decode()
        cls.fingerprint = next(line.split(':')[9] for line in listing.splitlines() if line.startswith('fpr:'))
        cls.public = cls.command(['--export']).stdout

    @classmethod
    def command(cls, args):
        return subprocess.run([str(cls.gpg), '--homedir', str(cls.keyhome), *args],
                              capture_output=True, check=True, timeout=20)

    @classmethod
    def tearDownClass(cls):
        gpgconf = shutil.which('gpgconf')
        if gpgconf:
            subprocess.run([gpgconf, '--homedir', str(cls.keyhome), '--kill', 'gpg-agent'],
                           capture_output=True, timeout=10)
        cls.keys.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'fixture.pkg.tar.gz'
        self.recipe = self.root / 'PKGBUILD'
        self.recipe.write_text('pkgname=fixture\n')
        self.recipe_hash = stage_providers.sha(self.recipe)
        self.metadata = 'pkgname = fixture\npkgver = 1-1\narch = x86_64\nurl = https://example.invalid/project\ndepend = glibc\n'
        self.build = f'pkgname = fixture\npkgver = 1-1\npkgbuild_sha256sum = {self.recipe_hash}\n'
        self.files = {'.PKGINFO': self.metadata, '.BUILDINFO': self.build,
                      'usr/bin/fixture': 'fixture bytes\n'}
        self.make_archive()
        self.keyring = self.root / 'keys.gpg'
        self.keyring.write_bytes(self.public)
        self.manifest = {'schema': 1, 'target': 'arch-hyprland',
                         'keyring': {'binarySha256': stage_providers.sha(self.keyring)},
                         'providers': [{'id': 'fixture', 'status': 'selected',
                           'package': 'fixture', 'version': '1-1', 'architecture': 'x86_64',
                           'archive': self.archive.name, 'sha256': stage_providers.sha(self.archive),
                           'recipeSha256': self.recipe_hash, 'requiredFiles': ['usr/bin/fixture'],
                           'origin': 'https://example.invalid/project',
                           'updateChannel': 'https://example.invalid/packages',
                           'trust': 'reviewed-local-build', 'recipeFiles': {'PKGBUILD': self.recipe_hash}},
                           {'id': 'native-system', 'status': 'pending', 'reason': 'Closure not selected'}]}

    def make_archive(self):
        with tarfile.open(self.archive, 'w:gz') as tar:
            for name, content in self.files.items():
                data = content.encode()
                member = tarfile.TarInfo(name)
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))

    def execute(self):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.manifest))
        return stage_providers.stage(path, [self.root], self.root / 'stage', self.bsdtar, self.gpgv, self.keyring)

    def signed(self):
        signature = self.archive.with_suffix(self.archive.suffix + '.sig')
        self.command(['--batch', '--yes', '--detach-sign', '--output', str(signature), str(self.archive)])
        provider = self.manifest['providers'][0]
        provider['trust'] = 'arch-signature'
        provider['signature'] = {'file': signature.name, 'sha256': stage_providers.sha(signature),
                                 'fingerprint': self.fingerprint}

    def test_partial_local_stage_is_never_candidate_ready(self):
        report = self.execute()
        self.assertTrue(report['selectedArtifactsVerified'])
        self.assertFalse(report['candidateReady'])
        self.assertEqual(len(report['pendingProviders']), 1)
        self.assertEqual(report['providers'][0]['dependencies'], ['glibc'])
        self.assertEqual((self.root / 'stage/fixture/fixture.pkg.tar.gz').read_bytes(), self.archive.read_bytes())

    def test_real_signature_and_pinned_key(self):
        self.signed()
        report = self.execute()
        self.assertEqual(report['providers'][0]['signingFingerprint'], self.fingerprint)

    def test_wrong_signing_key_rejects_publication(self):
        self.signed()
        self.manifest['providers'][0]['signature']['fingerprint'] = 'A' * 40
        with self.assertRaisesRegex(ValueError, 'selected signing key'):
            self.execute()
        self.assertFalse((self.root / 'stage').exists())

    def test_modified_archive_is_rejected_before_inspection(self):
        self.archive.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed artifact'):
            self.execute()

    def test_modified_signature_is_rejected(self):
        self.signed()
        (self.root / self.manifest['providers'][0]['signature']['file']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed artifact'):
            self.execute()

    def test_changed_keyring_is_rejected(self):
        self.signed()
        self.keyring.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed artifact'):
            self.execute()

    def test_wrong_version_and_missing_file_are_rejected(self):
        for key, value in [('version', '2-1'), ('requiredFiles', ['usr/bin/missing'])]:
            with self.subTest(key=key):
                saved = copy.deepcopy(self.manifest)
                self.manifest['providers'][0][key] = value
                with self.assertRaises(ValueError):
                    self.execute()
                self.manifest = saved

    def test_mismatched_recipe_and_changed_inputs_rejected(self):
        self.manifest['providers'][0]['recipeSha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Build recipe'):
            self.execute()
        self.manifest['providers'][0]['recipeSha256'] = self.recipe_hash
        self.recipe.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed artifact'):
            self.execute()

    def test_inherited_dependencies_and_update_channels_rejected(self):
        self.files['.PKGINFO'] += 'depend = omarchy-settings\n'
        self.make_archive()
        self.manifest['providers'][0]['sha256'] = stage_providers.sha(self.archive)
        with self.assertRaisesRegex(ValueError, 'Inherited active package'):
            self.execute()
        self.manifest['providers'][0]['updateChannel'] = 'https://github.com/omacom/repo'
        with self.assertRaisesRegex(ValueError, 'Inherited provider update'):
            self.execute()

    def test_path_traversal_and_duplicate_paths_rejected(self):
        for extra in ['../escape', './usr/bin/fixture']:
            with self.subTest(extra=extra):
                self.files[extra] = 'bad'
                self.make_archive()
                self.manifest['providers'][0]['sha256'] = stage_providers.sha(self.archive)
                with self.assertRaises(ValueError):
                    self.execute()
                del self.files[extra]
        self.assertFalse((self.root / 'stage').exists())

    def test_existing_destination_and_duplicate_provider_rejected(self):
        self.manifest['providers'].append(copy.deepcopy(self.manifest['providers'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate provider'):
            self.execute()
        self.manifest['providers'].pop()
        (self.root / 'stage').mkdir()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.execute()


if __name__ == '__main__':
    unittest.main()
