"""Reject mixed display provider archives, recipes and source patches."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('display_integration', ROOT / 'tools/check-display-integration.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class DisplayIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.providers = self.root / 'contracts/providers'
        self.providers.mkdir(parents=True)
        self.selection = {'providers': []}
        self.archives = {}
        for name, (member, markers) in CHECK.MARKERS.items():
            recipe = self.providers / 'recipes' / name / 'PKGBUILD'
            recipe.parent.mkdir(parents=True)
            recipe.write_text('fixture recipe ' + name)
            digest = hashlib.sha256(recipe.read_bytes()).hexdigest()
            archive = self.root / (name + '.pkg.tar.gz')
            payload = b'\x7fELF' + b' '.join(markers)
            metadata = f'pkgname = {name}\npkgver = 1-2\narch = x86_64\n'
            build = f'pkgname = {name}\npkgver = 1-2\npkgbuild_sha256sum = {digest}\n'
            with tarfile.open(archive, 'w:gz') as tar:
                for path, content in {'.PKGINFO': metadata.encode(), '.BUILDINFO': build.encode(), member: payload}.items():
                    item = tarfile.TarInfo(path)
                    item.size = len(content)
                    tar.addfile(item, io.BytesIO(content))
            self.archives[name] = archive
            self.selection['providers'].append({
                'id': name, 'package': name, 'version': '1-2', 'architecture': 'x86_64',
                'archive': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'recipeSha256': digest, 'recipeFiles': {f'recipes/{name}/PKGBUILD': digest},
                'requiredFiles': [member], 'sourceRevision': 'a' * 40})
        self.write_selection()

    def write_selection(self):
        (self.providers / 'selection.json').write_text(json.dumps(self.selection))

    def test_exact_pair_and_recipe_closure_pass(self):
        result = CHECK.verify_native(self.root, self.archives)
        self.assertEqual(set(result), {'hyprland', 'aquamarine'})
        self.assertEqual(result['hyprland']['sourceRevision'], 'a' * 40)

    def test_missing_pair_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Both native'):
            CHECK.verify_native(self.root, {'hyprland': self.archives['hyprland']})

    def test_changed_archive_is_rejected_before_inspection(self):
        with self.archives['aquamarine'].open('ab') as stream:
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'Missing/changed artifact'):
            CHECK.verify_native(self.root, self.archives)

    def test_changed_recipe_is_rejected(self):
        (self.providers / 'recipes/hyprland/PKGBUILD').write_text('different source')
        with self.assertRaisesRegex(ValueError, 'Missing/changed artifact'):
            CHECK.verify_native(self.root, self.archives)

    def test_build_recipe_identity_cannot_be_relabelled(self):
        entry = self.selection['providers'][0]
        entry['recipeSha256'] = 'b' * 64
        self.write_selection()
        with self.assertRaisesRegex(ValueError, 'Build recipe'):
            CHECK.verify_native(self.root, self.archives)

    def test_old_binary_without_correction_is_rejected(self):
        markers = copy.deepcopy(CHECK.MARKERS)
        member, words = markers['hyprland']
        markers['hyprland'] = (member, words + [b'absent correction'])
        with patch.object(CHECK, 'MARKERS', markers), self.assertRaisesRegex(ValueError, 'payload absent'):
            CHECK.verify_native(self.root, self.archives)

    def test_user_package_cannot_claim_a_different_source(self):
        shell = self.root / 'shell'
        (shell / 'share/tamlinux').mkdir(parents=True)
        (shell / 'share/tamlinux/source-revision').write_text('a' * 40)
        plugins = self.root / 'plugins'
        installed = plugins / 'share/tamlinux/plugins/fred.workspaces'
        installed.mkdir(parents=True)
        (installed / 'manifest.json').write_text('changed')
        with patch.object(CHECK, 'source', return_value=b'expected'), self.assertRaisesRegex(ValueError, 'differs from selected source'):
            CHECK.verify(self.root, self.root, plugins, shell, self.archives)
