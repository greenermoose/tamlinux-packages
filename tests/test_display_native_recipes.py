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

    def user_packages(self):
        shell = self.root / 'shell'
        plugins = self.root / 'plugins'
        commands = self.root / 'commands'
        (shell / 'share/tamlinux').mkdir(parents=True)
        (shell / 'share/tamlinux/source-revision').write_text('a' * 40)
        for package, paths in CHECK.PRODUCT_FILES.items():
            for path in paths:
                installed = plugins / 'share/tamlinux/plugins' / path.removeprefix('desktop/plugins/') if package == 'plugins' else shell / 'share/tamlinux' / path.removeprefix('desktop/')
                installed.parent.mkdir(parents=True, exist_ok=True)
                installed.write_bytes(path.encode())
        for name, path in (("tam-desktop-mode", "desktop/plugins/fred.workspaces/tam-desktop-mode"),
                           ("hyprland_backend.py", "desktop/shell/host/hyprland_backend.py"),
                           ("compositor_commands.py", "desktop/shell/host/compositor_commands.py")):
            installed = commands / 'share/tamlinux/workspaces' / name
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.write_bytes(path.encode())
        for name, patch_name in (('hyprland', 'hyprland-output-workspace-logging.patch'),
                                 ('aquamarine', 'aquamarine-commit-attribution.patch')):
            (self.providers / 'recipes' / name / patch_name).write_bytes(('desktop/native/providers/display/' + patch_name).encode())
        return shell, plugins, commands

    def test_both_user_entry_points_match_the_exact_native_source_pair(self):
        shell, plugins, commands = self.user_packages()
        with patch.object(CHECK, 'source', side_effect=lambda product, rev, path: path.encode()):
            result = CHECK.verify(self.root, self.root, plugins, shell, self.archives, commands)
        self.assertEqual(len(result['userFiles']), 9)

    def test_standalone_command_cannot_lag_behind_bar_helper(self):
        shell, plugins, commands = self.user_packages()
        (commands / 'share/tamlinux/workspaces/tam-desktop-mode').write_text('old helper')
        with patch.object(CHECK, 'source', side_effect=lambda product, rev, path: path.encode()), self.assertRaisesRegex(ValueError, 'Standalone command differs'):
            CHECK.verify(self.root, self.root, plugins, shell, self.archives, commands)

    def test_missing_standalone_command_is_not_a_complete_integration(self):
        shell, plugins, commands = self.user_packages()
        with patch.object(CHECK, 'source', side_effect=lambda product, rev, path: path.encode()), self.assertRaisesRegex(ValueError, 'standalone command package'):
            CHECK.verify(self.root, self.root, plugins, shell, self.archives)

    def test_standard_nix_python_relocation_preserves_isolated_mode_and_source(self):
        original = b"#!/usr/bin/python3 -I\nprint('source')\n"
        installed = b"#!/nix/store/" + b"a" * 32 + b"-python3-3.14.8/bin/python3 -I\nprint('source')\n"
        self.assertTrue(CHECK.command_source_matches(original, installed))
        self.assertFalse(CHECK.command_source_matches(original, installed.replace(b" -I", b"")))
        self.assertFalse(CHECK.command_source_matches(original, installed.replace(b"source", b"changed")))
        self.assertFalse(CHECK.command_source_matches(original, installed.replace(b"/nix/store/", b"/tmp/")))
