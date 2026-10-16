import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


path = Path(__file__).resolve().parents[1] / 'tools/boot-checkpoint.py'
spec = importlib.util.spec_from_file_location('boot_checkpoint', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BootCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'root'
        (self.root / 'boot/EFI').mkdir(parents=True)
        (self.root / 'boot/EFI/kernel.efi').write_bytes(b'previous boot image\0')
        (self.root / 'boot/loader-link').symlink_to('EFI/kernel.efi')
        self.input = dict(paths=['/boot', '/etc/new-setting.conf'], packages=[])
        self.out = self.base / 'checkpoint'

    def test_round_trip_archive_content_metadata_links_and_absence(self):
        record = module.capture(self.input, self.root, self.out)
        self.assertEqual(record, module.verify(self.out))
        self.assertEqual(record['files']['etc/new-setting.conf']['type'], 'absent')
        self.assertEqual(record['files']['boot/loader-link']['target'], 'EFI/kernel.efi')
        restored = self.base / 'restored'
        restored.mkdir()
        import subprocess
        subprocess.run(['/usr/bin/tar', '-xpf', str(self.out / 'state.tar'), '-C', str(restored)], check=True)
        self.assertEqual((restored / 'boot/EFI/kernel.efi').read_bytes(), b'previous boot image\0')
        self.assertTrue((restored / 'boot/loader-link').is_symlink())

    def test_rejects_changed_archive(self):
        module.capture(self.input, self.root, self.out)
        with (self.out / 'state.tar').open('ab') as out:
            out.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            module.verify(self.out)

    def test_does_not_traverse_symlink_ancestor(self):
        (self.root / 'escape').symlink_to('/etc', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink ancestor'):
            module.inventory(self.root, ['/escape/passwd'])

    def test_existing_destination_is_preserved(self):
        self.out.mkdir()
        (self.out / 'keep').write_text('other recovery kit')
        with self.assertRaisesRegex(ValueError, 'destination exists'):
            module.capture(self.input, self.root, self.out)
        self.assertEqual((self.out / 'keep').read_text(), 'other recovery kit')

    def test_package_lock_prevents_capture(self):
        lock = self.root / 'var/lib/pacman/db.lck'
        lock.parent.mkdir(parents=True)
        lock.touch()
        with self.assertRaisesRegex(ValueError, 'transaction lock'):
            module.capture(self.input, self.root, self.out)

    def test_package_mismatch_leaves_only_incomplete_evidence(self):
        self.input['packages'] = [dict(path='/missing.pkg.tar.zst', sha256='0' * 64)]
        with self.assertRaisesRegex(ValueError, 'Missing/changed package'):
            module.capture(self.input, self.root, self.out)
        self.assertTrue((self.out / 'INCOMPLETE').exists())
        self.assertFalse((self.out / 'VERIFIED').exists())

    def test_rejects_root_and_parent_traversal(self):
        for path in ['/', '/boot/../etc', 'boot/kernel', '/boot//kernel']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                module.relative(path)


if __name__ == '__main__':
    unittest.main()
