"""Finite native staging, deterministic sources and explicit trust limits."""
import importlib.util
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_stage',ROOT/'tools/prepare-native-integration.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class NativeStaging(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.product=self.base/'product'
        for relative in m.FILES.values():
            p=self.product/relative;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('controlled source '+relative+'\n')

    def test_same_selected_sources_produce_same_digest_bound_recipe_and_archive(self):
        a=m.prepare(self.product,self.base/'a','development')
        b=m.prepare(self.product,self.base/'b','development')
        self.assertEqual(a,b);self.assertFalse(a['candidateReady'])
        self.assertIn(a['sourceSha256'],(self.base/'a/PKGBUILD').read_text())
        with tarfile.open(self.base/'a/tamlinux-native-source.tar') as archive:
            self.assertEqual(len(archive.getmembers()),len(m.FILES)+1)
            self.assertTrue(all(p.name.startswith('tamlinux-native/') and p.uid==0 and p.mtime==0 for p in archive.getmembers()))

    def test_existing_destination_is_preserved(self):
        destination=self.base/'existing';destination.mkdir();(destination/'personal').write_text('keep')
        with self.assertRaises(FileExistsError):m.prepare(self.product,destination,'development')
        self.assertEqual((destination/'personal').read_text(),'keep')

    def test_destination_inside_product_is_refused(self):
        with self.assertRaises(ValueError):m.prepare(self.product,self.product/'stage','development')
        self.assertFalse((self.product/'stage').exists())

    def test_redirected_source_is_refused_before_any_staging(self):
        path=self.product/next(iter(m.FILES.values()));path.unlink()
        outside=self.base/'outside';outside.write_text('unselected');path.symlink_to(outside)
        with self.assertRaises(ValueError):m.prepare(self.product,self.base/'stage','development')
        self.assertFalse((self.base/'stage').exists())
