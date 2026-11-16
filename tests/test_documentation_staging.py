import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('stage_documentation',Path(__file__).resolve().parents[1]/'tools/stage-documentation.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class Staging(unittest.TestCase):
    def fixture(self,base,name='usr/share/info/demo.info',content=b'manual'):
        archive=base/'fixture-1-any.pkg.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            member=tarfile.TarInfo(name);member.size=len(content);tar.addfile(member,io.BytesIO(content))
            license=tarfile.TarInfo('usr/share/licenses/fixture/COPYING');license.size=7;tar.addfile(license,io.BytesIO(b'license'))
        return {'format':1,'archives':[{'collection':'info','package':'fixture','version':'1','archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}]}

    def test_fixed_layout_and_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);dest=base/'stage';dest.mkdir();sources=self.fixture(base)
            with patch.object(m.subprocess,'run'):
                m.stage(dest,sources,base)
            root=dest/'placed/usr/share/doc/info'
            self.assertEqual((root/'demo.info').read_bytes(),b'manual')
            self.assertEqual((root/'licenses/fixture/COPYING').read_bytes(),b'license')
            self.assertIn(sources['archives'][0]['sha256'],(root/'SOURCE.json').read_text())
            self.assertFalse((dest/'usr/share/info').exists())

    def test_hash_and_archive_traversal_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);dest=base/'stage';dest.mkdir();sources=self.fixture(base)
            sources['archives'][0]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'hash'):m.stage(dest,sources,base)
            sources=self.fixture(base,'usr/share/info/../../escape')
            with self.assertRaisesRegex(ValueError,'unsafe'):m.stage(dest,sources,base)
            self.assertFalse((dest/'placed/usr/escape').exists())

if __name__=='__main__':unittest.main()
