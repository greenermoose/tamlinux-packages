import gzip
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

    def test_archwiki_tam_staging_from_docs_and_lite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);dest=base/'stage';dest.mkdir()
            docs_arc=base/'arch-wiki-docs-1-any.pkg.tar.gz'
            html=b'<html><head><title>pacman - ArchWiki</title></head><body><div class="mw-content-ltr mw-parser-output"><p>Pacman docs</p><script>x</script></div></body></html>'
            with tarfile.open(docs_arc,'w:gz') as tar:
                m1=tarfile.TarInfo('usr/share/doc/arch-wiki/html/en/Pacman.html');m1.size=len(html);tar.addfile(m1,io.BytesIO(html))
                l1=tarfile.TarInfo('usr/share/licenses/arch-wiki-docs/GFDL');l1.size=4;tar.addfile(l1,io.BytesIO(b'gfdl'))
            lite_arc=base/'arch-wiki-lite-1-any.pkg.tar.gz'
            idx=b'en/Pacman 00000001\n'
            txt=gzip.compress(b'00000001:Pacman docs\n')
            with tarfile.open(lite_arc,'w:gz') as tar:
                m2=tarfile.TarInfo('usr/share/doc/arch-wiki/text/index');m2.size=len(idx);tar.addfile(m2,io.BytesIO(idx))
                m3=tarfile.TarInfo('usr/share/doc/arch-wiki/text/arch-wiki.txt.gz');m3.size=len(txt);tar.addfile(m3,io.BytesIO(txt))
                l2=tarfile.TarInfo('usr/share/licenses/arch-wiki-lite/GPL');l2.size=3;tar.addfile(l2,io.BytesIO(b'gpl'))
            sources={'format':1,'archives':[
                {'collection':'archwiki','package':'arch-wiki-docs','version':'1','archive':docs_arc.name,'sha256':hashlib.sha256(docs_arc.read_bytes()).hexdigest()},
                {'collection':'archwiki-lite','package':'arch-wiki-lite','version':'1','archive':lite_arc.name,'sha256':hashlib.sha256(lite_arc.read_bytes()).hexdigest()},
            ]}
            m.stage(dest,sources,base)
            root=dest/'placed/usr/share/doc/arch-wiki'
            tam_page=(root/'tam/Pacman.html').read_text()
            self.assertIn('Pacman docs',tam_page)
            self.assertNotIn('<script',tam_page)
            self.assertFalse((root/'html').exists())
            self.assertEqual((root/'licenses/arch-wiki-docs/GFDL').read_bytes(),b'gfdl')
            self.assertEqual((root/'licenses/arch-wiki-lite/GPL').read_bytes(),b'gpl')
            self.assertIn('arch-wiki-lite', (root/'SOURCE.json').read_text())

if __name__=='__main__':unittest.main()
