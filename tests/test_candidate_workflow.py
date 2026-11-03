"""Real Git selection, version reservation and interrupted commits."""
import importlib.util
import json
import contextlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('workflow',Path(__file__).parents[1]/'tools/candidate-workflow.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)

class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'XDG_STATE_HOME':str(self.root/'state'),'TAM_WORK_SESSION':'test-session'})
        self.env.start();self.addCleanup(self.env.stop)
        for name in (*w.COMPONENTS,'tamlinux-packages'):
            repo=self.root/name;repo.mkdir();self.git(repo,'init','-q','-b','develop')
            self.git(repo,'config','user.name','Fixture');self.git(repo,'config','user.email','fixture@example.invalid')
            (repo/'VERSION').write_text('0.6.1\n');(repo/'source').write_text('original\n')
            self.git(repo,'add','--','VERSION','source');self.git(repo,'commit','-qm','Initial')
            remote=self.root/(name+'.git');subprocess.run(['git','init','--bare','-q',str(remote)],check=True)
            self.git(repo,'remote','add','origin',str(remote));self.git(repo,'push','-q','-u','origin','develop')
        self.flow=w.Workflow(self.root);self.flow.claim=lambda *args:None
        self.flow.assembly_guard=lambda state:contextlib.nullcontext()
        self.packages=self.root/'tamlinux-packages';(self.packages/'deliveries').mkdir()

    def git(self,repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()

    def test_unregistered_changes_refused_before_version_reservation(self):
        (self.root/'tamlinux/source').write_text('unowned')
        with self.assertRaisesRegex(w.WorkflowError,'unregistered'):
            self.flow.prepare(word='Package and test the next version of Tamlinux',trailers='AI-Tool: fixture')
        self.assertFalse((self.flow.state/'active.json').exists())

    def test_trial_registration_cannot_take_another_sessions_dirty_work(self):
        repo=self.root/'tamlinux';(repo/'source').write_text('other session work')
        registry=self.root/'worktrees/coordination';registry.mkdir(parents=True)
        (registry/'other.json').write_text(json.dumps({'status':'active','repo':'tamlinux',
                'session':'another-session','scopes':['tamlinux/source']}))
        with patch.object(self.flow,'registered_trials',return_value=[{'repo':str(repo),'files':['source']}]):
            with self.assertRaisesRegex(w.WorkflowError,'held by another session'):
                self.flow.inspect()

    def test_invalid_word_does_not_allocate_version(self):
        with self.assertRaises(w.WorkflowError):self.flow.prepare(word='Implement the plan',trailers='fixture')
        self.assertFalse((self.flow.state/'active.json').exists())

    def test_include_quoted_or_mismatched_requests_do_not_allocate(self):
        for version, word in (
                ('0.6.2', 'Include tam-desktop-test in Tamlinux 0.6.2'),
                ('0.6.2', '"Package up and test Tamlinux 0.6.2"'),
                ('0.6.2', 'What if I say Package up and test Tamlinux 0.6.2?'),
                ('0.6.2', 'Package up and test Tamlinux 0.6.3'),
                ('0.6.1', 'Package up and test Tamlinux 0.6.1')):
            with self.subTest(word=word):
                with self.assertRaises(w.WorkflowError):
                    self.flow.prepare(version, word, trailers='fixture')
                self.assertFalse((self.flow.state/'active.json').exists())

    def test_named_request_selects_only_the_spoken_version(self):
        with patch.object(self.flow, 'claim', side_effect=w.WorkflowError('stop after allocation')):
            with self.assertRaisesRegex(w.WorkflowError, 'stop after allocation'):
                self.flow.prepare('0.6.2', 'Package up and test Tamlinux 0.6.2', trailers='fixture')
        state = json.loads((self.flow.state/'active.json').read_text())
        self.assertEqual(state['version'], '0.6.2')
        self.assertEqual(state['word'], 'Package up and test Tamlinux 0.6.2')

    def inclusion(self):
        return {'name': 'tam-desktop-test', 'repo': 'tamlinux',
                'revision': self.git(self.root/'tamlinux', 'rev-parse', 'HEAD'),
                'sourcePath': 'commands/tam-desktop-test', 'output': 'tamlinux-commands',
                'artifact': 'bin/tam-desktop-test'}

    def test_old_source_pin_cannot_satisfy_new_inclusion(self):
        repo = self.root/'tamlinux'
        before = self.git(repo, 'rev-parse', 'HEAD')
        path = repo/'commands/tam-desktop-test/Makefile'
        path.parent.mkdir(parents=True); path.write_text('install:\n\ttrue\n')
        self.git(repo, 'add', '--', 'commands/tam-desktop-test/Makefile')
        self.git(repo, 'commit', '-qm', 'Finished requested command')
        with self.assertRaisesRegex(w.WorkflowError, 'omits its recorded revision'):
            self.flow.verify_inclusion_sources([self.inclusion()], {'tamlinux': before})

    def test_recipe_entry_without_built_command_does_not_satisfy_inclusion(self):
        item = self.inclusion()
        output = self.root/'hash-tamlinux-commands-0.6.2'
        output.mkdir()
        record = {'outputs': [{'outputs': {'out': str(output)}}]}
        with self.assertRaisesRegex(w.WorkflowError, 'artifact absent'):
            self.flow.verify_inclusion_outputs([item], record)
        command = output/'bin/tam-desktop-test'
        command.parent.mkdir(); command.mkdir()
        with self.assertRaisesRegex(w.WorkflowError, 'artifact absent'):
            self.flow.verify_inclusion_outputs([item], record)
        command.rmdir(); command.write_text('#!/bin/sh\nexit 0\n')
        command.chmod(0o755)
        self.flow.verify_inclusion_outputs([item], record)

    def test_failed_phase_reuses_reserved_version_and_source_commits(self):
        outer=self
        class Prepare:
            def read_version(self,root):return (root/'VERSION').read_text().strip()
            def cmd_version(self,root,args):(root/'VERSION').write_text(args.version+'\n')
            def lock_inputs(self,root):return {n:{'locked':{'rev':outer.git(outer.root/n,'rev-parse','HEAD')}} for n in w.COMPONENTS}
            def fingerprint(self,root):return 'stable-recipe'
            def cmd_verify(self,root,args):pass
            def cmd_build(self,root,args):raise w.WorkflowError('simulated build interruption')
        self.flow.native=lambda *args:{'archive':'/fixture/archive','package':{},'requirement':{}}
        with patch.object(w,'module',return_value=Prepare()):
            with self.assertRaisesRegex(w.WorkflowError,'simulated build'):
                self.flow.prepare(word='Package and test the next version of Tamlinux',trailers='AI-Tool: fixture')
            state=json.loads((self.flow.state/'active.json').read_text());self.assertEqual(state['version'],'0.6.2')
            head=self.git(self.root/'tamlinux','rev-parse','HEAD')
            with patch.object(self.flow,'publish_sources',side_effect=AssertionError('repeated publication')):
                with self.assertRaisesRegex(w.WorkflowError,'simulated build'):
                    self.flow.prepare('0.6.2',resume=True,trailers='AI-Tool: fixture')
            self.assertEqual(self.git(self.root/'tamlinux','rev-parse','HEAD'),head)

    def test_interrupted_commit_recognized_and_newer_edits_refused(self):
        repo=self.root/'tamlinux';parent=self.git(repo,'rev-parse','HEAD');file=repo/'source';file.write_text('selected')
        intent={'parent':parent,'message':'Select candidate','trailers':'AI-Tool: fixture',
                'files':{'source':[0o644,w.hashlib.sha256(file.read_bytes()).hexdigest()]}}
        revision=self.flow.resume_source(repo,intent);self.assertEqual(self.flow.resume_source(repo,intent),revision)
        file.write_text('later')
        with self.assertRaisesRegex(w.WorkflowError,'source changed'):self.flow.resume_source(repo,intent)

    def test_frozen_resume_does_not_follow_new_heads(self):
        repo=self.packages;version='0.6.2';delivery=repo/f'deliveries/tamlinux-{version}.json'
        delivery.write_text('{"version":"0.6.2"}\n');self.git(repo,'add','--',str(delivery.relative_to(repo)));self.git(repo,'commit','-qm','Frozen')
        state={'schema':1,'phase':'frozen','version':version,'word':'Package and test the next version of Tamlinux',
               'host':os.uname().nodename,'assembly':self.git(repo,'rev-parse','HEAD'),
               'deliverySha256':w.hashlib.sha256(delivery.read_bytes()).hexdigest()}
        w.save(self.flow.state/'active.json',state);(repo/'source').write_text('newer work')
        with patch.object(self.flow,'inspect',side_effect=AssertionError('new inspection')):
            self.assertEqual(self.flow.prepare(version,resume=True,trailers='fixture'),state)

    def test_frozen_result_cannot_cross_hosts(self):
        w.save(self.flow.state/'active.json',{'phase':'frozen','version':'0.6.2','host':'other'})
        with self.assertRaisesRegex(w.WorkflowError,'another host'):self.flow.prepare('0.6.2',resume=True,trailers='fixture')

    def test_cancel_preserves_sources_and_consumes_number(self):
        selected={n:{'revision':self.git(self.root/n,'rev-parse','HEAD'),'paths':[],'files':{}} for n in w.COMPONENTS}
        state={'phase':'sources','version':'0.6.2','host':os.uname().nodename}
        w.save(self.flow.state/'active.json',state)
        self.flow.cancel('0.6.2')
        original=self.git(self.root/'tamlinux','rev-parse','HEAD')
        with patch.object(self.flow,'inspect',return_value=selected), patch.object(self.flow,'claim',side_effect=w.WorkflowError('stop after allocation')):
            with self.assertRaises(w.WorkflowError):
                self.flow.prepare(word='Package and test the next version of Tamlinux',trailers='fixture')
        self.assertEqual(json.loads((self.flow.state/'active.json').read_text())['version'],'0.6.3')
        self.assertEqual(self.git(self.root/'tamlinux','rev-parse','HEAD'),original)

    def test_partial_generated_write_recovers_without_losing_original_text(self):
        repo=self.root/'tamlinux';parent=self.git(repo,'rev-parse','HEAD')
        file=repo/'source';original=file.read_text();wanted=original+'selected addition\n'
        intent={'parent':parent,'message':'Select candidate','trailers':'fixture',
                'files':{'source':[0o644,w.hashlib.sha256(wanted.encode()).hexdigest()]},
                'originals':{'source':[0o644,w.hashlib.sha256(original.encode()).hexdigest()]},'writes':{'source':wanted}}
        self.flow.resume_source(repo,intent)
        self.assertEqual(file.read_text(),wanted)

    def test_complete_request_freezes_one_candidate_and_resume_runs_no_builds(self):
        import io
        import shutil
        import tarfile
        from test_prepare_candidate import FAKE_NIX
        from test_native_integration import NativeStaging
        template=NativeStaging();template.setUp();self.addCleanup(template.doCleanups)
        product=self.root/'tamlinux'
        shutil.copytree(template.product,product,dirs_exist_ok=True,symlinks=True)
        (product/'VERSION').write_text('0.6.1\n')
        tests=product/'desktop/tests';tests.mkdir()
        prepare=w.module('prepare-candidate')
        for name in prepare.FOCUSED_TESTS:
            (tests/name).write_text('import unittest\nclass Check(unittest.TestCase):\n def test_ok(self):self.assertTrue(True)\n')
        command = product/'commands/tam-desktop-test/Makefile'
        command.parent.mkdir(parents=True)
        command.write_text('install:\n\ttrue\n')
        paths=subprocess.check_output(['git','-C',str(product),'ls-files','-co','--exclude-standard','-z']).split(b'\0')
        self.git(product,'add','--',*[p.decode() for p in paths if p]);self.git(product,'commit','-qm','Controlled product fixture')
        pins={name:self.git(self.root/name,'rev-parse','HEAD') for name in w.COMPONENTS}
        required = [self.inclusion()]
        self.flow.inclusions = lambda version: required
        nodes={name:{'locked':{'owner':'greenermoose','repo':name,'rev':rev,'type':'github'},
                     'original':{'owner':'greenermoose','repo':name,'rev':rev,'type':'github'}} for name,rev in pins.items()}
        nodes['root']={'inputs':{name:name for name in pins}}
        (self.packages/'flake.lock').write_text(json.dumps({'root':'root','nodes':nodes}))
        (self.packages/'flake.nix').write_text('\n'.join(f'"github:greenermoose/{name}/{rev}"' for name,rev in pins.items()))
        self.git(self.packages,'add','--','flake.nix','flake.lock');self.git(self.packages,'commit','-qm','Assembly fixture')
        # Real fixture output files let the full workflow verify inclusion,
        # without contacting a daemon, building Nix packages or installing anything.
        output_root = self.root/'store'
        for target in prepare.DEFAULT_TARGETS:
            (output_root/('hash-'+target[2:]+'-0.6.2')).mkdir(parents=True)
        installed = output_root/'hash-tamlinux-commands-0.6.2/bin/tam-desktop-test'
        installed.parent.mkdir(); installed.write_text('#!/bin/sh\nexit 0\n'); installed.chmod(0o755)
        fake_code = FAKE_NIX.replace('f"/nix/store/{i}"',
            'str(Path(os.environ["FAKE_NIX_OUTPUT_ROOT"])/f"hash-{targets[i][2:]}-0.6.2")').replace(
            "f'/nix/store/{i}'", 'str(Path(os.environ["FAKE_NIX_OUTPUT_ROOT"])/f"hash-{targets[i].rsplit(chr(35),1)[1]}-0.6.2")')
        fake=self.root/'nix';fake.write_text('#!'+w.sys.executable+'\n'+fake_code);fake.chmod(0o755)
        log=self.root/'nix.log'
        native_calls=[]
        def native(revision,state):
            native_calls.append(revision)
            selected=w.module('prepare-native-integration').prepare(product,self.root/'native-stage',revision)
            manifest=selected['manifest'];archive=self.root/'native.pkg.tar'
            files={'.PKGINFO':b'pkgname = tamlinux-native\npkgver = 0.6.2-0.1\n',
                   'usr/share/tamlinux/native-integration.json':json.dumps(manifest).encode()}
            with tarfile.open(archive,'w') as bundle:
                for name,data in files.items():
                    entry=tarfile.TarInfo(name);entry.size=len(data);bundle.addfile(entry,io.BytesIO(data))
            return {'archive':str(archive),'requirement':{'payloadId':selected['payloadId'],'interface':1},
                    'package':{'name':'tamlinux-native','version':'0.6.2-0.1','archive':archive.name,
                               'sha256':w.hashlib.sha256(archive.read_bytes()).hexdigest(),
                               'productRevision':revision,'payloadId':selected['payloadId']}}
        self.flow.native=native
        with patch.dict(os.environ,{'PREPARE_CANDIDATE_NIX':str(fake),'FAKE_NIX_LOG':str(log),
                                   'FAKE_NIX_OUTPUT_ROOT':str(output_root)}):
            result=self.flow.prepare('0.6.2', word='Package up and test Tamlinux 0.6.2',trailers='AI-Tool: fixture')
            self.assertEqual(result['phase'],'frozen');self.assertEqual(result['version'],'0.6.2')
            delivery = json.loads((self.packages/'deliveries/tamlinux-0.6.2.json').read_text())
            self.assertEqual(delivery['inclusions'], required)
            before=log.read_text();head=self.git(self.packages,'rev-parse','HEAD')
            (product/'source').write_text('new development after selection')
            resumed=self.flow.prepare('0.6.2',resume=True,trailers='AI-Tool: fixture')
            self.assertEqual(resumed['assembly'],head)
            self.assertEqual(log.read_text().count('build --no-link'),before.count('build --no-link'))
            self.assertEqual(log.read_text().count('flake update'),before.count('flake update'))
            self.assertEqual(len(native_calls),1)
            self.assertEqual(before.count('build --no-link'),1)
            required.append({**required[0], 'name': 'another-command'})
            with self.assertRaisesRegex(w.WorkflowError, 'requested contents changed'):
                self.flow.prepare('0.6.2', resume=True, trailers='fixture')
