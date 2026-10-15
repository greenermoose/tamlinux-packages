"""Runtime parsing/resolution must use actual paths and omit secret values."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('runtime', Path(__file__).resolve().parents[1]/'tools/collect-session-runtime.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RuntimeCollector(unittest.TestCase):
    def test_environment_never_copies_credentials_or_inherited_values(self):
        values, names = m.environment(b'HOME=/home/alex\0TOKEN=private\0OMARCHY_SECRET=private\0PATH=/owned/bin:/usr/bin\0')
        self.assertEqual(values, {'HOME':'/home/alex', 'PATH':'/owned/bin:/usr/bin'})
        self.assertEqual(names, ['OMARCHY_SECRET'])
        self.assertNotIn('private', str(values)+str(names))

    def test_maps_separates_real_paths_spaces_deleted_files_and_anonymous_objects(self):
        result = m.mapped_paths('''a-b r-xp 0 00:00 1 /opt/Qt library.so
a-b r--p 0 00:00 1 /opt/Qt library.so
a-b rw-p 0 00:00 0 [heap]
a-b rw-p 0 00:00 0
a-b r--p 0 00:00 1 /old/provider.so (deleted)
''')
        self.assertEqual(result, ['/old/provider.so (deleted)', '/opt/Qt library.so'])

    def test_resolution_detects_an_executable_shadowing_selected_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root/'selected'
            (selected/'bin').mkdir(parents=True)
            other = root/'other'
            other.mkdir()
            for directory in (selected/'bin', other):
                target = directory/'tam-shell'
                target.write_text('#!/bin/sh\n')
                target.chmod(0o700)
            path = str(other)+':'+str(selected/'bin')
            result = m.resolve_commands(['tam-shell'], path, selected)
            self.assertFalse(result[0]['matchesSelected'])
            (other/'tam-shell').unlink()
            (other/'tam-shell').symlink_to(selected/'bin/tam-shell')
            self.assertTrue(m.resolve_commands(['tam-shell'], path, selected)[0]['matchesSelected'])

    def test_broken_resource_links_are_reported_with_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'font'
            path.symlink_to('/missing/font.ttf')
            result = m.file_identity(path)
            self.assertFalse(result['present'])
            self.assertEqual(result['link'], '/missing/font.ttf')

    def test_qml_path_accepts_managed_alias_only_when_it_resolves_to_selected_modules(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);selected=root/'modules';selected.mkdir()
            alias=root/'managed';alias.symlink_to(selected)
            self.assertTrue(m.module_root_matches(str(alias),selected))
            self.assertFalse(m.module_root_matches(str(root/'other'),selected))

    def test_unit_properties_do_not_copy_unrequested_environment(self):
        result = m.properties('MainPID=12\nEnvironment=API_TOKEN=secret\nActiveState=active\n')
        self.assertEqual(result, {'MainPID':'12', 'ActiveState':'active'})

    def test_wm_instances_preserve_escaped_names_and_ignore_non_units(self):
        result = m.wm_units(r'''wayland-wm@Hyprland.service loaded active running Main service
wayland-wm@tamlinux\x2dhyprland.desktop.service loaded inactive dead Main service
wayland-wm@Hyprland.service loaded active running Duplicate
tamlinux-shell.service loaded active running Shell
2 loaded units listed.
''')
        self.assertEqual(result, ['wayland-wm@Hyprland.service',
                                 r'wayland-wm@tamlinux\x2dhyprland.desktop.service'])

    def test_absent_bus_owner_is_not_activated(self):
        from unittest.mock import patch
        with patch.object(m, 'command', return_value={'exit': 1, 'stdout': '', 'stderr': ''}) as call:
            self.assertEqual(m.bus_owner('org.freedesktop.secrets'),
                             {'exit': 1, 'name': 'org.freedesktop.secrets'})
        self.assertEqual(call.call_count, 1)
        self.assertIn('GetNameOwner', call.call_args.args[0])


class GraphicsEvidence(unittest.TestCase):
    def fixture(self, renderer='AMD Radeon Graphics (radeonsi, renoir, ACO)', mode='hardware', env=None):
        layers = {'DP-1': {'levels': {'0': [
            {'pid': 12, 'w': 1920, 'h': 1080, 'namespace': name} for name in
            ['tamlinux-bar-DP-1-0', 'tamlinux-background', 'tamlinux-notifications']]}}}
        log = 'qt.rhi.general: OpenGL VENDOR: AMD RENDERER: '+renderer+' VERSION: 4.6 Mesa'
        return m.graphics_evidence(12, env or {}, log, layers, ['DP-1'], mode, (), True)

    def test_hardware_requires_context_and_all_surfaces(self):
        self.assertTrue(self.fixture()['passed'])
        missing = m.graphics_evidence(12, {}, '', {}, ['DP-1'], 'hardware')
        self.assertFalse(missing['passed'])
        other_pid = m.graphics_evidence(99, {}, 'OpenGL VENDOR: AMD RENDERER: radeonsi VERSION: 4.6',
             {'DP-1': {'levels': {'0': [{'pid': 12, 'w': 1, 'h': 1, 'namespace': 'tamlinux-background'}]}}},
             ['DP-1'], 'hardware')
        self.assertFalse(other_pid['passed'])

    def test_software_vm_is_explicitly_distinct_from_hardware(self):
        self.assertFalse(self.fixture(renderer='llvmpipe (LLVM 21)')['passed'])
        vm = self.fixture(renderer='llvmpipe (LLVM 21)', mode='vm')
        self.assertTrue(vm['passed'])
        self.assertTrue(vm['softwareRendererObserved'])
        for key in ['QT_QUICK_BACKEND', 'LIBGL_ALWAYS_SOFTWARE', 'QSG_RHI_BACKEND']:
            with self.subTest(key=key):
                self.assertFalse(self.fixture(env={key: 'software'})['passed'])

    def test_context_error_is_not_hidden_by_later_renderer(self):
        r=m.graphics_evidence(12, {}, 'EGL not available\nOpenGL VENDOR: AMD RENDERER: radeonsi VERSION: 4.6',
                              {}, [], 'hardware', ['renoir'])
        self.assertFalse(r['checks']['noContextErrors'])
        self.assertFalse(r['checks']['rendererMatches'])
