"""Finite native staging, deterministic sources and explicit trust limits."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
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
        base=self.product/m.DEFAULTS;root=base/'root'
        hook=root/'usr/lib/systemd/system-sleep/tamlinux-hook';hook.parent.mkdir(parents=True)
        hook.write_text('#!/bin/bash\n');hook.chmod(0o755)
        conf=root/'usr/share/example/conf.avail/50-tamlinux.conf';conf.parent.mkdir(parents=True);conf.write_text('x\n')
        link=root/'usr/share/example/conf.default/50-tamlinux.conf';link.parent.mkdir(parents=True)
        link.symlink_to('../conf.avail/50-tamlinux.conf')
        self.origins={'usr/lib/systemd/system-sleep/tamlinux-hook':{'mode':'0755','sha256':hashlib.sha256(b'#!/bin/bash\n').hexdigest()},
            'usr/share/example/conf.avail/50-tamlinux.conf':{'mode':'0644','sha256':hashlib.sha256(b'x\n').hexdigest()},
            'usr/share/example/conf.default/50-tamlinux.conf':{'link':'../conf.avail/50-tamlinux.conf'}}
        self.write_origins()

    def write_origins(self):
        (self.product/m.DEFAULTS/'origins.json').write_text(json.dumps({'schema':1,'files':self.origins}))

    def test_same_selected_sources_produce_same_digest_bound_recipe_and_archive(self):
        a=m.prepare(self.product,self.base/'a','development')
        b=m.prepare(self.product,self.base/'b','development')
        self.assertEqual(a,b);self.assertFalse(a['candidateReady'])
        self.assertIn(a['sourceSha256'],(self.base/'a/PKGBUILD').read_text())
        with tarfile.open(self.base/'a/tamlinux-native-source.tar') as archive:
            self.assertEqual(len(archive.getmembers()),len(m.FILES)+len(self.origins)+1)
            self.assertTrue(all(p.name.startswith('tamlinux-native/') and p.uid==0 and p.mtime==0 for p in archive.getmembers()))

    def test_existing_destination_is_preserved(self):
        destination=self.base/'existing';destination.mkdir();(destination/'personal').write_text('keep')
        with self.assertRaises(FileExistsError):m.prepare(self.product,destination,'development')
        self.assertEqual((destination/'personal').read_text(),'keep')

    def test_recipe_delivers_explicit_session_without_any_graphical_login_files(self):
        stage=self.base/'stage'
        m.prepare(self.product,stage,'development')
        source=self.base/'source';source.mkdir()
        with tarfile.open(stage/'tamlinux-native-source.tar') as archive:
            archive.extractall(source,filter='data')
        # package() consumes the built provider, without running build() here.
        (source/'tamlinux-native/asdcontrol/asdcontrol').write_text('fixture provider\n')
        package=self.base/'package';package.mkdir()
        result=subprocess.run(['bash','-eu','-c','source "$1"; package','package',str(stage/'PKGBUILD')],
                              env={**os.environ,'srcdir':str(source),'pkgdir':str(package)},
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse((package/'usr/share/sddm').exists())
        self.assertFalse((package/'usr/lib/sddm').exists())
        self.assertFalse((package/'usr/share/wayland-sessions').exists())
        self.assertFalse((package/'usr/lib/tamlinux/pam-transaction.py').exists())
        self.assertEqual((package/'usr/bin/tam-session').read_bytes(),
                         (self.product/m.FILES['integration/session']).read_bytes())
        self.assertTrue(os.access(package/'usr/bin/tam-session', os.X_OK))
        self.assertFalse((package/'usr/bin/tamlinux-session').exists())
        self.assertFalse((package/'etc').exists())
        self.assertFalse((package/'usr/local').exists())

    def test_no_display_manager_splash_or_login_pam_transaction_is_selected(self):
        stage=self.base/'stage';result=m.prepare(self.product,stage,'develop-console')
        self.assertEqual(result['manifest']['productRevision'],'develop-console')
        self.assertFalse(any('sddm' in path or 'pam-transaction' in path
                             for path in result['manifest']['files']))
        with tarfile.open(stage/'tamlinux-native-source.tar') as archive:
            self.assertFalse(any('sddm' in entry.name or 'pam-transaction' in entry.name
                                 for entry in archive.getmembers()))
        dependencies=subprocess.check_output(
            ['bash','-eu','-c','source "$1"; printf "%s\\n" "${depends[@]}"',
             'dependencies',str(stage/'PKGBUILD')],text=True).splitlines()
        self.assertNotIn('sddm',dependencies)
        self.assertNotIn('plymouth',dependencies)
        self.assertIn('uwsm',dependencies)

    def test_destination_inside_product_is_refused(self):
        with self.assertRaises(ValueError):m.prepare(self.product,self.product/'stage','development')
        self.assertFalse((self.product/'stage').exists())

    def test_redirected_source_is_refused_before_any_staging(self):
        path=self.product/next(iter(m.FILES.values()));path.unlink()
        outside=self.base/'outside';outside.write_text('unselected');path.symlink_to(outside)
        with self.assertRaises(ValueError):m.prepare(self.product,self.base/'stage','development')
        self.assertFalse((self.base/'stage').exists())

    def test_defaults_keep_modes_links_and_manifest(self):
        result=m.prepare(self.product,self.base/'stage','development')
        with tarfile.open(self.base/'stage/tamlinux-native-source.tar') as archive:
            hook=archive.getmember('tamlinux-native/defaults/root/usr/lib/systemd/system-sleep/tamlinux-hook')
            link=archive.getmember('tamlinux-native/defaults/root/usr/share/example/conf.default/50-tamlinux.conf')
            self.assertEqual(hook.mode,0o755);self.assertTrue(link.issym())
            self.assertEqual(link.linkname,'../conf.avail/50-tamlinux.conf')
        self.assertIn('defaults/root/usr/share/example/conf.default/50-tamlinux.conf',result['manifest']['links'])
        self.assertIn('defaults/LICENSE',result['manifest']['files'])

    def test_unrecorded_default_is_refused_before_staging(self):
        extra=self.product/m.DEFAULTS/'root/usr/lib/sysctl.d/99-unrecorded.conf'
        extra.parent.mkdir(parents=True);extra.write_text('vm.swappiness=1\n')
        with self.assertRaises(ValueError):m.prepare(self.product,self.base/'stage','development')
        self.assertFalse((self.base/'stage').exists())

    def test_changed_mode_or_bytes_is_refused(self):
        (self.product/m.DEFAULTS/'root/usr/lib/systemd/system-sleep/tamlinux-hook').chmod(0o644)
        with self.assertRaises(ValueError):m.prepare(self.product,self.base/'stage','development')

    def test_etc_path_or_escaping_link_is_refused(self):
        etc=self.product/m.DEFAULTS/'root/etc/example.conf';etc.parent.mkdir(parents=True);etc.write_text('x\n')
        self.origins['etc/example.conf']={'mode':'0644','sha256':hashlib.sha256(b'x\n').hexdigest()};self.write_origins()
        with self.assertRaises(ValueError):m.prepare(self.product,self.base/'a','development')
        etc.unlink();del self.origins['etc/example.conf']
        link=self.product/m.DEFAULTS/'root/usr/share/example/conf.default/50-tamlinux.conf'
        outside=self.base/'outside.conf';outside.write_text('x\n')
        link.unlink();link.symlink_to(outside);self.origins['usr/share/example/conf.default/50-tamlinux.conf']={'link':str(outside)}
        self.write_origins()
        with self.assertRaises(ValueError):m.prepare(self.product,self.base/'b','development')
