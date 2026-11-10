import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('compare_bundle',Path(__file__).resolve().parents[1]/'tools/compare-bundle.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class BundleComparison(unittest.TestCase):
    def test_missing_product_command_is_not_hidden_by_packaging_differences(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=Path(tmp)/'old';new=Path(tmp)/'new';old.mkdir();new.mkdir()
            for name in ('bin/tam','bin/.tam-wrapped','share/man/man1/tam.1.gz'):
                p=old/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('old')
            p=new/'share/man/man1/tam.1';p.parent.mkdir(parents=True);p.write_text('new')
            (new/'BUNDLE').write_text('identity')
            result=m.compare(new,[old])
            self.assertFalse(result['explained'])
            self.assertEqual(result['differences']['removed: UNEXPLAINED'],['bin/tam'])
            self.assertEqual(result['commonFiles'],1)
            p=new/'bin/tam';p.parent.mkdir();p.write_text('native')
            self.assertTrue(m.compare(new,[old])['explained'])

    def test_only_named_external_font_families_are_explained(self):
        self.assertNotEqual(m.explanation('share/fonts/opentype/AtkinsonHyperlegible-Regular.otf',False),'UNEXPLAINED')
        self.assertEqual(m.explanation('share/fonts/truetype/TamlinuxIcons.ttf',False),'UNEXPLAINED')
