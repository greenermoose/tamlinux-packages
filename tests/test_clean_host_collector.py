"""Repository parsing, actual database owners and root-contained image links."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('host_collector',ROOT/'tools/collect-clean-host.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class HostCollector(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.write('/etc/os-release','ID=arch\nNAME="Arch Linux"\n')
        self.write('/etc/pacman.conf','[options]\nSigLevel = Required DatabaseOptional\n[core]\nInclude = /etc/pacman.d/mirrorlist\n[extra]\nServer = https://archive.archlinux.org/repos/$repo/os/$arch\n')
        self.write('/etc/pacman.d/mirrorlist','Server = https://archive.archlinux.org/repos/$repo/os/$arch\n')
        self.package('hyprland','0.56.2-4.1',['usr/bin/Hyprland','usr/bin/hyprctl'])

    def write(self,name,data):
        path=self.root/name.lstrip('/');path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(data);return path

    def package(self,name,version,files):
        base='/var/lib/pacman/local/'+name+'-'+version
        self.write(base+'/desc','%NAME%\n'+name+'\n\n%VERSION%\n'+version+'\n')
        self.write(base+'/files','%FILES%\n'+'\n'.join(files)+'\n')

    def test_repeated_mirror_include_is_permitted_across_repo_sections(self):
        self.write('/etc/pacman.conf','[core]\nInclude = /etc/pacman.d/mirrorlist\n[extra]\nInclude = /etc/pacman.d/mirrorlist\n')
        result=m.pacman_configuration(self.root)
        self.assertEqual(result['repositories'],['core','extra'])
        self.assertEqual(result['findings'],[])

    def test_active_inherited_server_and_unselected_repository_are_recorded(self):
        self.write('/etc/pacman.d/mirrorlist','# historical Omarchy comment\nServer = https://stable-mirror.omarchy.org/$repo/os/$arch\n')
        self.write('/etc/pacman.conf','[core]\nInclude = /etc/pacman.d/mirrorlist\n[unselected]\nServer = https://example.org/$repo\n')
        result=m.pacman_configuration(self.root)
        self.assertEqual(len(result['findings']),2)

    def test_include_cycle_fails_closed_without_external_execution(self):
        self.write('/etc/pacman.d/mirrorlist','Include = /etc/pacman.conf\n')
        with self.assertRaisesRegex(ValueError,'Cyclic'):m.pacman_configuration(self.root)

    def test_native_database_records_exact_package_version_and_owners(self):
        self.package('omarchy-settings','4.0.4-1',['etc/pam.d/sudo'])
        packages,owners,findings=m.package_database(self.root)
        self.assertIn({'package':'omarchy-settings','reason':'inherited installed package'},findings)
        self.assertEqual(owners['/usr/bin/Hyprland'],['hyprland'])
        self.assertTrue(any(p['name']=='hyprland' and p['version']=='0.56.2-4.1' for p in packages))

    def test_absolute_image_symlink_resolves_within_image_and_never_host_usr(self):
        expected=self.write('/usr/lib/owned','image payload')
        (self.root/'usr/bin').mkdir();(self.root/'usr/bin/provider').symlink_to('/usr/lib/owned')
        self.assertEqual(m.inside(self.root,'/usr/bin/provider'),expected)
        self.assertEqual(m.inside(self.root,'/usr/bin/provider').read_text(),'image payload')

    def test_path_escape_and_symlink_loop_are_refused(self):
        with self.assertRaises(ValueError):m.inside(self.root,'/../../outside')
        (self.root/'loop').symlink_to('/loop')
        with self.assertRaisesRegex(ValueError,'loop'):m.inside(self.root,'/loop')

    def test_missing_native_endpoint_remains_a_finding(self):
        result=m.collect(self.root)
        self.assertTrue(any(x['reason']=='missing native endpoint' for x in result['findings']))
        self.assertEqual(result['os']['ID'],'arch')

    def test_terminal_binary_and_desktop_entry_are_collected(self):
        self.assertIn('/usr/bin/foot', m.CRITICAL)
        self.assertIn('/usr/share/applications/foot.desktop', m.CRITICAL)
        self.package('foot', '1', ['usr/bin/foot', 'usr/share/applications/foot.desktop'])
        self.write('/usr/bin/foot', '#!/bin/sh\n')
        self.write('/usr/share/applications/foot.desktop', '[Desktop Entry]\nExec=foot\n')
        result = m.collect(self.root)
        rows = {row['path']: row for row in result['criticalFiles']}
        for path in ('/usr/bin/foot', '/usr/share/applications/foot.desktop'):
            self.assertTrue(rows[path]['present'])
            self.assertEqual(rows[path]['packages'], ['foot'])

    def test_non_arch_identity_is_refused(self):
        self.write('/etc/os-release','ID=other\n')
        with self.assertRaisesRegex(ValueError,'Arch'):m.collect(self.root)
