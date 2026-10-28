import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest


spec = importlib.util.spec_from_file_location('native_check', Path(__file__).parents[1] / 'tools/native-package-check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class NativePackageCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / 'tamlinux-native.pkg.tar'
        self.revision = '1' * 40
        files = {'.PKGINFO': b'pkgname = tamlinux-native\npkgver = 0.5.6-0.1\n',
                 'usr/share/tamlinux/native-integration.json': json.dumps({'productRevision': self.revision}).encode(),
                 'usr/lib/issue.d/70-tamlinux.issue': b'Welcome to Tamlinux!\nCultivar: Blue Sparkler 0.5.6\n'}
        with tarfile.open(self.archive, 'w') as tar:
            for name, content in files.items():
                entry = tarfile.TarInfo(name); entry.size = len(content)
                tar.addfile(entry, io.BytesIO(content))
        self.record = {'version': '0.5.6', 'components': {'tamlinux': {'rev': self.revision}},
                       'readiness': {'nativeInstallationRequired': True},
                       'nativePackage': {'name': 'tamlinux-native', 'version': '0.5.6-0.1',
                                         'archive': self.archive.name, 'productRevision': self.revision,
                                         'sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest()}}

    def test_matching_archive(self):
        self.assertEqual(check.verify(self.record, self.archive), self.record['nativePackage']['sha256'])

    def test_archive_or_revision_mismatch_is_refused(self):
        self.record['components']['tamlinux']['rev'] = '2' * 40
        with self.assertRaisesRegex(ValueError, 'selected product revision'):
            check.verify(self.record, self.archive)
        self.record['components']['tamlinux']['rev'] = self.revision
        self.record['nativePackage']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'digest'):
            check.verify(self.record, self.archive)

    def test_candidate_version_mismatch_is_refused(self):
        self.record['version'] = '0.5.7'
        with self.assertRaisesRegex(ValueError, 'candidate version'):
            check.verify(self.record, self.archive)


if __name__ == '__main__':
    unittest.main()
