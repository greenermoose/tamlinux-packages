#!/usr/bin/env python3
"""Gather and freeze one resumable Tamlinux candidate. Never promotes or installs.

The personal stage wrapper supplies authorization and human records. This
public helper owns only source selection, packaging and the frozen result.
"""
from __future__ import annotations
import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ('libtam', 'tam', 'tamlinux-tools', 'tamlinux')
WORD = re.compile(r'(?:please\s+)?package(?:\s+up)?\s+and\s+test\s+(?:the\s+next\s+version\s+of\s+tamlinux|tamlinux\s+(?P<version>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)))[.!]?', re.I)


class WorkflowError(Exception):
    pass


def run(*args, cwd=None):
    try:
        return subprocess.check_output(list(map(str, args)), cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as exc:
        raise WorkflowError(str(args[0])+' failed: '+exc.output[-4000:]) from exc


def git(repo, *args):
    return run('git', '-C', repo, *args)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT/'tools'/f'{name}.py')
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def dirty(repo):
    changed = subprocess.check_output(['git','-C',str(repo),'diff','HEAD','--name-only','--no-renames','-z'])
    extra = subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','-z'])
    return sorted(set(p.decode() for p in (changed+extra).split(b'\0') if p))


def within(path, scopes):
    return any(path == scope or path.startswith(scope.rstrip('/')+'/') for scope in scopes)


class Workflow:
    def __init__(self, workspace, state=None, registrar=None, inclusions=None):
        self.registrar = registrar
        self.inclusions = inclusions
        self.workspace = Path(workspace).resolve()
        self.packages = self.workspace/'tamlinux-packages'
        self.state = Path(state or Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'tamlinux/candidate-workflow')
        self.state.mkdir(parents=True, exist_ok=True)

    def requested_contents(self, version):
        items = self.inclusions(version) if self.inclusions else []
        if not isinstance(items, list):
            raise WorkflowError('candidate inclusions must be a list')
        for item in items:
            if (item.get('repo') not in COMPONENTS or
                    not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,127}', item.get('name', '')) or
                    not re.fullmatch(r'[A-Za-z0-9_.+-]+', item.get('output', '')) or
                    (item.get('revision') is not None and not re.fullmatch(r'[0-9a-f]{40}', item['revision']))):
                raise WorkflowError('invalid requested component identity')
            for key in ('sourcePath', 'artifact'):
                path = item.get(key)
                if not isinstance(path, str) or not path or Path(path).is_absolute() or '..' in Path(path).parts:
                    raise WorkflowError('invalid requested component path')
            versions = item.get('versions')
            if versions is not None:
                if (item['name'] != 'tam' or item['repo'] != 'tam' or item['output'] != 'tam' or
                        item['artifact'] != 'bin/tam' or not isinstance(versions, dict) or
                        set(versions) != {'command', 'corpus'} or
                        any(not isinstance(value, str) or not re.fullmatch(
                            r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)', value)
                            for value in versions.values())):
                    raise WorkflowError('invalid tam command/corpus constraint')
        return items

    def verify_tam_versions(self, items, pins=None):
        for item in items:
            expected = item.get('versions')
            if not expected:
                continue
            repo = self.workspace/'tam'
            try:
                header = git(repo, 'show', pins['tam']+':src/version.h') if pins else (repo/'src/version.h').read_text()
                corpus = git(repo, 'show', pins['tam']+':knowledge/version') if pins else (repo/'knowledge/version').read_text().strip()
            except (OSError, WorkflowError) as exc:
                raise WorkflowError('tam: cannot read the selected command/corpus versions') from exc
            command = re.search(r'^#define\s+TAM_COMMAND_VERSION\s+"([^"\n]+)"', header, re.M)
            actual = {'command': command[1] if command else 'unavailable', 'corpus': corpus}
            if actual != expected:
                raise WorkflowError('tam: requested '+expected['command']+' ('+expected['corpus']+
                                    '), selected '+actual['command']+' ('+actual['corpus']+
                                    '); select matching source or explicitly revise the inclusion')

    def verify_inclusion_sources(self, items, pins):
        for item in items:
            repo = self.workspace/item['repo']
            revision = pins[item['repo']]
            if item.get('revision'):
                result = subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor',
                                         item['revision'], revision], capture_output=True)
                if result.returncode:
                    raise WorkflowError(item['name'] + ': selected source omits its recorded revision')
            source = item['sourcePath']
            if source != '.':
                try:
                    git(repo, 'cat-file', '-e', revision + ':' + source)
                except WorkflowError as exc:
                    raise WorkflowError(item['name'] + ': missing from selected source') from exc
        self.verify_tam_versions(items, pins)

    def verify_inclusion_outputs(self, items, record):
        for item in items:
            roots = [Path(path) for result in record.get('outputs', [])
                     for path in result.get('outputs', {}).values()
                     if re.fullmatch(r'[a-z0-9]+-' + re.escape(item['output']) + r'-[0-9].*', Path(path).name)]
            files = [root/item['artifact'] for root in roots]
            if not files or not any(file.exists() and
                    (not item['artifact'].startswith('bin/') or
                     (file.is_file() and os.access(file, os.X_OK))) for file in files):
                raise WorkflowError(item['name'] + ': requested artifact absent from built ' + item['output'])
            if item.get('versions'):
                # Inspect the package itself, independent of development corpus overrides.
                if len(roots) != 1:
                    raise WorkflowError('tam: expected one built package for version verification')
                knowledge = roots[0]/'share/tamlinux/knowledge'
                try:
                    corpus = (knowledge/'version').read_text().strip()
                    result = subprocess.run([str(roots[0]/'bin/tam'), '--version'], capture_output=True,
                        text=True, check=True, timeout=10,
                        env={**os.environ, 'TAM_KNOWLEDGE_DIR': str(knowledge), 'TAM_DATADIR': str(knowledge)})
                except (OSError, subprocess.SubprocessError) as exc:
                    raise WorkflowError('tam: cannot verify built command/corpus versions') from exc
                command = re.search(r'^tam command ([0-9]+\.[0-9]+\.[0-9]+)(?:\s|$)', result.stdout, re.M)
                reported_corpus = re.search(r'^knowledge corpus ([0-9]+\.[0-9]+\.[0-9]+)(?:\s|$)', result.stdout, re.M)
                expected = item['versions']
                if (not command or not reported_corpus or command[1] != expected['command'] or
                        corpus != expected['corpus'] or reported_corpus[1] != expected['corpus']):
                    raise WorkflowError('tam: built package does not match requested '+expected['command']+
                                        ' ('+expected['corpus']+')')

    def owner_scopes(self, repo, foreign=False):
        session = os.environ.get('TAM_WORK_SESSION') or os.environ.get('CODEX_THREAD_ID') or os.environ.get('CLAUDE_SESSION_ID')
        scopes = []
        registry = self.workspace/'worktrees/coordination'
        for path in registry.glob('*.json'):
            value = json.loads(path.read_text())
            if value.get('status') != 'active' or value.get('repo') != repo.name:
                continue
            ours = bool(session) and value.get('session') == session
            if ours != foreign:
                prefix = repo.name+'/'
                scopes.extend(s.removeprefix(prefix) for s in value.get('scopes', []))
        return scopes

    def registered_trials(self):
        trials = Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'tamlinux/development/trials'
        result=[]
        for path in trials.glob('*.json'):
            value=json.loads(path.read_text());repo=Path(value['repo'])
            if repo.name not in COMPONENTS or repo.resolve()!=(self.workspace/repo.name).resolve():
                raise WorkflowError('trial belongs to another workspace')
            paths=run('git','-C',repo,'ls-files','-co','--exclude-standard','-z','--',*value['scopes']).split('\0')
            present={p for p in paths if p and ((repo/p).exists() or (repo/p).is_symlink())}
            if present!=set(value['files']):
                raise WorkflowError('trial source changed; rebuild/try or stop '+value['component'])
            for relative,entry in value['files'].items():
                file=repo/relative
                actual=['link',os.readlink(file)] if file.is_symlink() else [file.stat().st_mode & 0o777,hashlib.sha256(file.read_bytes()).hexdigest()]
                if actual!=entry:raise WorkflowError('trial source changed; rebuild/try or stop '+value['component'])
            result.append(value)
        return result

    def component_versions(self, name, repo, paths):
        # Version choices belong to the component's development task. Gathering
        # must not silently publish changed tam code/pages under an old version.
        if name!='tam' or not (self.packages/'flake.lock').exists():return
        lock=json.loads((self.packages/'flake.lock').read_text());nodes=lock['nodes']
        node=nodes[lock.get('root','root')]['inputs'].get('tam')
        before=nodes[node].get('locked',{}).get('rev') if node else None
        if not before:return
        changed=set(paths)|set(git(repo,'diff','--name-only',before,'--').splitlines())
        command=any(p.startswith(('src/','bin/','completions/','man/')) and p!='src/version.h' for p in changed)
        generated={'knowledge/version','knowledge/coverage.json','knowledge/.build_id'}
        corpus=any(p.startswith('knowledge/') and p not in generated and not p.startswith('knowledge/index.') for p in changed)
        if command:
            current=(repo/'src/version.h').read_text()
            old=git(repo,'show',before+':src/version.h')
            version=lambda text:re.search(r'#define TAM_COMMAND_VERSION\s+"([^" ]+)"',text).group(1)
            if version(current)==version(old) or version(current) not in (repo/'tests/run.sh').read_text():
                raise WorkflowError('tam: finalize the command version and matching tests under its component rules before packaging')
        if corpus and (repo/'knowledge/version').read_text().strip()==git(repo,'show',before+':knowledge/version'):
            raise WorkflowError('tam: finalize the corpus version under its component rules before packaging')

    def inspect(self):
        result = {}
        legacy=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'tamlinux/dev-trials'
        if list(legacy.glob('*.json')):
            raise WorkflowError('Legacy app trials remain: use their recorded restore command once before migration to tam-dev, preserving any later launcher edits')
        trials = self.registered_trials()
        for name in COMPONENTS:
            repo = self.workspace/name
            if git(repo, 'branch', '--show-current') != 'develop':
                raise WorkflowError(name+': candidate sources must be on develop')
            changes = dirty(repo)
            self.component_versions(name,repo,changes)
            conflicts = [p for p in changes if within(p, self.owner_scopes(repo, foreign=True))]
            if conflicts:
                raise WorkflowError(name+': changes held by another session: '+', '.join(conflicts))
            owned = self.owner_scopes(repo)
            owned += [p for trial in trials if trial['repo']==str(repo) for p in trial['files']]
            unowned = [p for p in changes if not within(p, owned)]
            if unowned:
                raise WorkflowError(name+': unregistered or conflicting changes: '+', '.join(unowned))
            result[name] = {'revision':git(repo,'rev-parse','HEAD'),'paths':changes,
                            'diff':digest(git(repo,'diff','HEAD','--',*changes)) if changes else None,
                            'files':{p:hashlib.sha256((repo/p).read_bytes()).hexdigest()
                                     if (repo/p).is_file() else None for p in changes}}
        return result

    def claim(self, repo, paths):
        args = ['tam-work','begin','--allow-dirty','--note','Prepare selected candidate sources']
        if getattr(self,'_guard_id',None):args += ['--id',self._guard_id]
        for path in paths:
            args += ['--scope',path]
        run(*args, cwd=repo)

    @contextlib.contextmanager
    def assembly_guard(self,state):
        # Keep the caller's shared claims intact. Only this temporary claim is
        # exclusive, and its identity survives an interrupted preparation.
        active=self.state/'active.json'
        ident=state.get('buildClaim') or 'candidate-build-'+str(time.time_ns())
        state['buildClaim']=ident;save(active,state)
        run('tam-work','begin','--exclusive','--allow-dirty','--id',ident,
            '--note','Build and freeze the selected candidate',cwd=self.packages)
        self._guard_id=ident
        try:yield
        finally:
            run('tam-work','finish','--id',ident,'--note','Candidate build stopped or frozen',cwd=self.packages)
            self._guard_id=None
            state.pop('buildClaim',None);save(active,state)

    def frozen_outputs(self,revision,record,restore=False):
        expected={p for item in record['outputs'] for p in item['outputs'].values()}
        targets=record['verification']['builtTargets']
        if not targets or any(not re.fullmatch(r'\.#[A-Za-z0-9_.-]+',target) for target in targets):
            raise WorkflowError('invalid frozen build target set')
        refs=['git+file://'+str(self.packages)+'?rev='+revision+'#'+target[2:] for target in targets]
        nix=module('prepare-candidate').nix()
        if restore:
            available=subprocess.run([nix,'path-info',*sorted(expected)],capture_output=True).returncode==0
            if available:return
            print('restore: realize missing outputs from the frozen assembly',flush=True)
            run(nix,'build','--no-link',*refs)
        actual=set(run(nix,'path-info','--no-write-lock-file',*refs).splitlines())
        if actual!=expected:
            raise WorkflowError('committed assembly outputs differ from recorded build evidence; preserve this delivery and prepare a new candidate')

    def commit(self, repo, paths, message, trailers):
        if not dirty(repo):
            return git(repo,'rev-parse','HEAD')
        run('git','-C',repo,'add','--',*paths)
        run('git','-C',repo,'commit','--only','-m',message+'\n\n'+trailers,'--',*paths)
        return git(repo,'rev-parse','HEAD')

    def publish_sources(self, pins):
        for name,revision in pins.items():
            self.publish(self.workspace/name, revision)
        return pins

    def resume_source(self, repo, intent):
        head=git(repo,'rev-parse','HEAD')
        if head!=intent['parent']:
            if git(repo,'rev-parse','HEAD^')!=intent['parent'] or git(repo,'log','-1','--format=%s')!=intent['message']:
                raise WorkflowError(repo.name+': unexpected source commit after interruption')
        for path, entry in intent['files'].items():
            source=repo/path
            actual=[source.stat().st_mode & 0o777, hashlib.sha256(source.read_bytes()).hexdigest()] if source.is_file() else None
            if head==intent['parent'] and path in intent.get('writes',{}) and actual==intent['originals'][path]:
                source.parent.mkdir(parents=True,exist_ok=True)
                temporary=source.with_name(source.name+'.candidate-tmp')
                temporary.write_text(intent['writes'][path]);temporary.chmod(entry[0]);temporary.replace(source)
                actual=entry
            if actual!=entry:
                raise WorkflowError(repo.name+': interrupted source changed: '+path)
        if head==intent['parent']:
            if not set(dirty(repo)).issubset(intent['files']):
                raise WorkflowError(repo.name+': unrelated changes after interruption')
            return self.commit(repo,list(intent['files']),intent['message'],intent['trailers'])
        if dirty(repo):
            raise WorkflowError(repo.name+': new dirty changes after interrupted commit')
        return head

    def publish(self, repo, revision):
        # A normal fast-forward push refuses a concurrent remote divergence.
        # No branch switching and no force rewind.
        run('git','-C',repo,'fetch','-q','origin','develop')
        remote = git(repo,'rev-parse','origin/develop')
        if subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',revision,remote],capture_output=True).returncode==0:
            return
        run('git','-C',repo,'merge-base','--is-ancestor',remote,revision)
        run('git','-C',repo,'push','origin',revision+':refs/heads/develop')

    def cancel(self, version):
        with (self.state/'operation.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            path=self.state/'active.json'
            if not path.exists():raise WorkflowError('no active candidate request')
            state=json.loads(path.read_text())
            if version!=state['version']:raise WorkflowError('cancel must name the reserved candidate')
            state['phase']='cancelled'
            save(path,state);save(self.state/(version+'.json'),state)
            print('Cancelled request '+version+'; sources, artifacts and the reserved number are preserved.')
            return state

    def prepare(self, version='next', word=None, resume=False, trailers=''):
        with (self.state/'operation.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            return self._prepare(version,word,resume,trailers)

    def _prepare(self, version, word, resume, trailers):
        active = self.state/'active.json'
        if resume:
            if not active.exists():
                raise WorkflowError('no transaction to resume')
            state = json.loads(active.read_text())
            if version not in ('next',state['version']):
                raise WorkflowError('resume names a different candidate')
            if state['phase']=='cancelled':raise WorkflowError('request was cancelled; start a new request')
            if state['host'] != os.uname().nodename:
                raise WorkflowError('request belongs to another host')
            if word is not None and word != state.get('word'):
                raise WorkflowError('resume cannot replace the original request')
            if self.inclusions and self.requested_contents(state['version']) != state.get('inclusions', []):
                raise WorkflowError('requested contents changed; preserve this candidate and make a new request')
        else:
            request = WORD.fullmatch((word or '').strip())
            if not request:
                raise WorkflowError('say Package up and test Tamlinux <version>, or Package and test the next version of Tamlinux')
            requested_version = request['version']
            if requested_version:
                if version not in ('next', requested_version):
                    raise WorkflowError('spoken version differs from the command version')
                version = requested_version
            if active.exists() and json.loads(active.read_text()).get('phase') not in ('frozen','cancelled'):
                raise WorkflowError('an unfinished candidate exists; use --resume')
            selected = self.inspect()
            for name,item in selected.items():
                print(f"select: {name} {item['revision'][:12]} ({len(item['paths'])} registered dirty paths)",flush=True)
            parent = git(self.packages,'rev-parse','HEAD')
            assembly_paths=dirty(self.packages)
            if any(within(p,self.owner_scopes(self.packages, foreign=True)) for p in assembly_paths):
                raise WorkflowError('assembly edits held by another session')
            if any(not within(p,self.owner_scopes(self.packages)) for p in assembly_paths):
                raise WorkflowError('unregistered assembly edits; finish or claim the intended work')
            assembly_selection={'revision':parent,'paths':assembly_paths,
                                'files':{p:hashlib.sha256((self.packages/p).read_bytes()).hexdigest()
                                         if (self.packages/p).is_file() else None for p in assembly_paths}}
            current = (self.packages/'VERSION').read_text().strip()
            major,minor,patch = map(int,current.split('.'))
            existing = [int(p.stem.rsplit('.',1)[1]) for p in (self.packages/'deliveries').glob(f'tamlinux-{major}.{minor}.*.json')]
            reservations=[int(p.stem.rsplit('.',1)[1]) for p in self.state.glob(f'{major}.{minor}.*.json')]
            chosen = f'{major}.{minor}.{max([patch,*existing,*reservations])+1}'
            if version not in ('next',chosen):
                raise WorkflowError('next unused version is '+chosen)
            included = self.requested_contents(chosen)
            self.verify_tam_versions(included)
            state = {'schema':1,'version':chosen,'word':word,'host':os.uname().nodename,
                     'inclusions':included,
                     'selected':selected,'assemblySelection':assembly_selection,'parentAssembly':parent,'phase':'selected','steps':{},
                     'requestId':digest({'parent':parent,'selected':selected,'inclusions':included,
                                         'host':os.uname().nodename,'word':word})}
            save(active,state)  # version reservation before any source mutation
            save(self.state/(chosen+'.json'),state)
        version = state['version']
        self.current = state
        def phase(name, function):
            if name in state['steps']:
                print(name+': reuse completed phase',flush=True)
                return state['steps'][name]['result']
            started = time.monotonic()
            state['phase']=name;save(active,state)
            state.pop('blocker',None)
            try:
                result=function()
            except (Exception,SystemExit) as exc:
                state['blocker']=str(exc);save(active,state)
                if isinstance(exc,SystemExit):raise WorkflowError(str(exc)) from exc
                raise
            state['steps'][name]={'seconds':round(time.monotonic()-started,3),'result':result}
            save(active,state)
            return result
        if not trailers.strip():
            raise WorkflowError('runtime provenance trailers are required')
        if state['phase']=='frozen':
            self.verify_frozen(state)
            return state

        def sources():
            pins={}
            for name, selected in state['selected'].items():
                repo=self.workspace/name
                paths=selected['paths'][:]
                # Refuse changes after selection, including extra untracked work.
                # A completed source commit is discoverable after interruption.
                expected=state.setdefault('sourceCommits',{}).get(name)
                if expected:
                    if git(repo,'rev-parse','HEAD')!=expected or dirty(repo):
                        raise WorkflowError(name+': sources moved after finalization')
                    pins[name]=expected;continue
                intent=state.setdefault('sourceIntents',{}).get(name)
                if intent:
                    pins[name]=self.resume_source(repo,intent)
                    state['sourceCommits'][name]=pins[name];save(active,state)
                    continue
                if git(repo,'rev-parse','HEAD') != selected['revision']:
                    raise WorkflowError(name+': HEAD moved during selection; inspect transaction')
                if dirty(repo)!=selected['paths']:
                    raise WorkflowError(name+': selected dirty paths changed')
                for p,sha in selected['files'].items():
                    actual=hashlib.sha256((repo/p).read_bytes()).hexdigest() if (repo/p).is_file() else None
                    if actual!=sha:
                        raise WorkflowError(name+': source changed after selection: '+p)
                writes={}
                if name=='tamlinux':
                    paths=list(dict.fromkeys([*paths,'VERSION']))
                    writes['VERSION']=version+'\n'
                if paths:
                    record=f'docs/ai/{version}-candidate-selection.md'
                    paths=list(dict.fromkeys([*paths,record,'AI_PROVENANCE.md']))
                    self.claim(repo,paths)
                    writes[record]=('# Candidate source selection\n\nSelected registered development changes for '+version+'.\n\n'
                                    '- Transcript: Retained privately by the author.\n- Request: '+state['word']+'\n\n'+trailers+'\n')
                    index=repo/'AI_PROVENANCE.md'
                    writes['AI_PROVENANCE.md']=(index.read_text() if index.exists() else '# AI provenance\n')+f'\nCandidate {version}: [source selection]({record}).\n'
                    originals={p:[(repo/p).stat().st_mode & 0o777,hashlib.sha256((repo/p).read_bytes()).hexdigest()]
                                 if (repo/p).is_file() else None for p in paths}
                    files=dict(originals)
                    for p,text in writes.items():files[p]=[originals[p][0] if originals[p] else 0o644,hashlib.sha256(text.encode()).hexdigest()]
                    intent={'parent':selected['revision'],'message':'Select sources for Tamlinux '+version,
                            'trailers':trailers,'files':files,'originals':originals,'writes':writes}
                    state['sourceIntents'][name]=intent;save(active,state)
                    pins[name]=self.resume_source(repo,intent)
                else:pins[name]=selected['revision']
                state['sourceCommits'][name]=pins[name];save(active,state)
            return pins
        def assembly_sources():
            selected=state.get('assemblySelection',{'paths':[]})
            if not selected['paths']:return state['parentAssembly']
            intent=state.get('assemblySourceIntent')
            if not intent:
                if git(self.packages,'rev-parse','HEAD')!=selected['revision'] or dirty(self.packages)!=selected['paths']:
                    raise WorkflowError('assembly changed after selection')
                for p,expected in selected['files'].items():
                    if (hashlib.sha256((self.packages/p).read_bytes()).hexdigest() if (self.packages/p).is_file() else None)!=expected:
                        raise WorkflowError('assembly source changed: '+p)
                self.claim(self.packages,selected['paths'])
                intent={'parent':selected['revision'],'message':'Select assembly sources for Tamlinux '+version,
                        'trailers':trailers,'files':{p:[(self.packages/p).stat().st_mode & 0o777,expected]
                                                  if expected is not None else None for p,expected in selected['files'].items()}}
                state['assemblySourceIntent']=intent;save(active,state)
            return self.resume_source(self.packages,intent)
        state['parentAssembly']=phase('assembly-sources',assembly_sources)
        pins=phase('sources',sources)
        self.verify_inclusion_sources(state.get('inclusions', []), pins)
        for name,rev in pins.items():
            git(self.workspace/name,'cat-file','-e',rev+'^{commit}')
        def publish_selected():
            if self.registrar:
                for name,intent in state.get('sourceIntents',{}).items():
                    for record in intent['files']:
                        if record.startswith('docs/ai/') and record.endswith('-candidate-selection.md'):
                            self.registrar(name,record)
            return self.publish_sources(pins)
        phase('published-sources', publish_selected)
        prepare=module('prepare-candidate')
        def pin():
            paths=['VERSION','flake.nix','flake.lock',f'deliveries/tamlinux-{version}.json']
            self.claim(self.packages,paths)
            current=(self.packages/'VERSION').read_text().strip()
            if current!=version:
                prepare.cmd_version(self.packages,argparse.Namespace(version=version))
            locked=prepare.lock_inputs(self.packages)
            changed=[name+'='+rev for name,rev in pins.items() if locked[name]['locked'].get('rev')!=rev]
            if changed:prepare.cmd_pin(self.packages,argparse.Namespace(pins=changed))
            return prepare.fingerprint(self.packages)
        fingerprint=phase('pins',pin)
        if prepare.fingerprint(self.packages)!=fingerprint:
            raise WorkflowError('assembly inputs changed after pinning')
        native=phase('native',lambda:self.native(pins['tamlinux'],state))
        def assemble_locked():
            args=argparse.Namespace(product=str(self.workspace/'tamlinux'),evidence=None,target=None,
                 parent=state['parentAssembly'],scope='Selected development state for '+version,build=None,
                 extra=None,native_archive=native['archive'])
            prepare.cmd_verify(self.packages,args)
            prepare.cmd_build(self.packages,args)
            extra=self.state/(version+'-native.json')
            save(extra,{'nativePackage':native['package'],'nativeRequirement':native['requirement'],
                        'inclusions':state.get('inclusions', []),
                        'readiness':{'nativeInstallationRequired':True}})
            args.extra=str(extra)
            delivery=self.packages/f'deliveries/tamlinux-{version}.json'
            if not delivery.exists():prepare.cmd_record(self.packages,args)
            else:
                data=json.loads(delivery.read_text())
                if data['verification']['fingerprint']!=fingerprint:
                    raise WorkflowError('existing delivery differs from selected inputs')
            data = json.loads(delivery.read_text())
            if data.get('inclusions', []) != state.get('inclusions', []):
                raise WorkflowError('delivery inclusions differ from the frozen selection')
            self.verify_inclusion_outputs(state.get('inclusions', []), data)
            state['deliverySha256']=hashlib.sha256(delivery.read_bytes()).hexdigest();save(active,state)
            record=f'docs/ai/{version}-candidate-preparation.md'
            self.claim(self.packages,[record,'AI_PROVENANCE.md'])
            note=self.packages/record;note.parent.mkdir(parents=True,exist_ok=True)
            text=('# Candidate preparation '+version+'\n\nPrepared exact committed sources and verified package outputs.\n\n'
                  '- Transcript: Retained privately by the author.\n- Request: '+state['word']+'\n\n'+trailers+'\n')
            if note.exists() and note.read_text()!=text:
                raise WorkflowError('existing assembly provenance differs')
            note.write_text(text)
            index=self.packages/'AI_PROVENANCE.md'
            entry=f'\nCandidate {version}: [preparation]({record}).\n'
            existing=index.read_text() if index.exists() else '# AI provenance\n'
            if entry not in existing:index.write_text(existing+entry)
            revision=self.commit(self.packages,['VERSION','flake.nix','flake.lock',str(delivery.relative_to(self.packages)),record,'AI_PROVENANCE.md'],
                                 'Prepare Tamlinux '+version+' candidate',trailers)
            if self.registrar:self.registrar('tamlinux-packages',record)
            self.frozen_outputs(revision,json.loads(delivery.read_text()))
            self.publish(self.packages,revision)
            return revision
        def assemble():
            with self.assembly_guard(state):return assemble_locked()
        delivery=self.packages/f'deliveries/tamlinux-{version}.json'
        if 'assembly' not in state['steps'] and delivery.exists() and not dirty(self.packages):
            revision=git(self.packages,'rev-parse','HEAD')
            if (git(self.packages,'log','-1','--format=%s')=='Prepare Tamlinux '+version
                    and git(self.packages,'rev-parse','HEAD^')==state['parentAssembly']
                    and hashlib.sha256(delivery.read_bytes()).hexdigest()==state.get('deliverySha256')):
                with self.assembly_guard(state):
                    self.frozen_outputs(revision,json.loads(delivery.read_text()))
                    self.publish(self.packages,revision)
                state['steps']['assembly']={'seconds':0,'result':revision};save(active,state)
        state['assembly']=phase('assembly',assemble)
        state['phase']='frozen';state.pop('blocker',None);save(active,state)
        save(self.state/(version+'.json'),state)
        self.verify_frozen(state)
        return state

    def verify_frozen(self,state):
        revision=state['assembly'];version=state['version']
        delivery=git(self.packages,'show',revision+':deliveries/tamlinux-'+version+'.json')
        if hashlib.sha256((delivery+'\n').encode()).hexdigest()!=state['deliverySha256']:
            raise WorkflowError('frozen delivery identity differs')
        record=json.loads(delivery)
        if record.get('outputs'):self.frozen_outputs(revision,record,restore=True)
        items = state.get('inclusions', [])
        if record.get('inclusions', []) != items:
            raise WorkflowError('frozen delivery inclusions differ')
        if items:
            self.verify_inclusion_sources(items, {name: pin['rev'] for name, pin in record['components'].items()})
            self.verify_inclusion_outputs(items, record)
        return revision

    def native(self, revision, state):
        native=module('prepare-native-integration')
        with tempfile.TemporaryDirectory(prefix='tamlinux-native-source-') as temp:
            archive=subprocess.check_output(['git','-C',str(self.workspace/'tamlinux'),'archive',revision])
            import io
            with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:bundle.extractall(temp,filter='data')
            staging=self.state/'native'/state['version']
            if staging.exists():
                # An incomplete makepkg can resume its own build tree.
                selection=json.loads((staging/'selection.json').read_text())
            else:selection=native.prepare(Path(temp),staging,revision)
        requirement={'payloadId':selection['payloadId'],'interface':selection['interface']}
        # Reuse the exact archive and original provenance of a compatible native layer.
        for path in sorted((self.packages/'deliveries').glob('*.json'),reverse=True):
            previous=json.loads(path.read_text())
            if previous.get('nativeRequirement')!=requirement:continue
            pkg=previous['nativePackage']
            found=list((self.state/'native').rglob(pkg['archive']))
            for archive in found:
                module('native-package-check').verify(previous,archive)
                return {'requirement':requirement,'package':pkg,'archive':str(archive)}
        files=list(staging.glob('tamlinux-native-*.pkg.tar.zst'))
        if not files:
            run('makepkg','--noconfirm',cwd=staging)
            files=list(staging.glob('tamlinux-native-*.pkg.tar.zst'))
        if len(files)!=1:raise WorkflowError('native build did not produce one archive')
        archive=files[0]
        package={'name':'tamlinux-native','version':state['version']+'-0.1','archive':archive.name,
                 'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'productRevision':revision,
                 'payloadId':selection['payloadId']}
        result={'requirement':requirement,'package':package,'archive':str(archive)}
        module('native-package-check').verify({'nativePackage':package,'nativeRequirement':requirement},archive)
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version',nargs='?',default='next')
    parser.add_argument('--workspace',type=Path,default=ROOT.parent)
    parser.add_argument('--word')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--trailers-file',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=Workflow(args.workspace).prepare(args.version,args.word,args.resume,args.trailers_file.read_text())
        print(json.dumps(result,indent=2));return 0
    except (WorkflowError,OSError,ValueError,KeyError,subprocess.CalledProcessError) as exc:
        print('candidate-workflow: '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
