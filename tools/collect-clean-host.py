#!/usr/bin/env python3
"""Read native package/repository ownership and bounded egress observations.

This collector never changes package databases, services, configuration or
repositories. Its raw report remains partial evidence until bound to a complete
selected artifact tuple by the independence gate.
"""
import argparse
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import time

INHERITED=re.compile('omarchy',re.I)
CRITICAL=[
 '/usr/bin/Hyprland','/usr/bin/hyprctl','/usr/bin/uwsm','/usr/bin/uwsm-app',
 '/usr/bin/quickshell','/usr/bin/qs','/usr/bin/xdg-terminal-exec',
 '/usr/bin/foot','/usr/share/applications/foot.desktop',
 '/usr/lib/tamlinux/asdcontrol','/usr/bin/tam-theme-set-browser-policy',
 '/usr/lib/tamlinux/browser_policy.py','/usr/lib/tamlinux/hyprland-reload-guard',
 '/usr/bin/tam-session',
 '/usr/share/polkit-1/actions/org.tamlinux.native.policy',
 '/usr/lib/tmpfiles.d/tamlinux.conf','/usr/share/libalpm/hooks/50-tamlinux-hyprland-pause.hook',
 '/usr/share/libalpm/hooks/50-tamlinux-hyprland-resume.hook',
 '/etc/pam.d/hyprlock','/usr/share/pacman/keyrings/archlinux.gpg',
 '/usr/share/pacman/keyrings/archlinux-trusted','/usr/share/pacman/keyrings/archlinux-revoked',
]


def sha(path):
    with path.open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()


def inside(root,name):
    """Resolve image links within the supplied root, never through host /usr."""
    parts=list(Path(name).parts[1:]);current=root;traversals=0
    while parts:
        part=parts.pop(0)
        if part=='.':continue
        if part=='..':
            if current==root:raise ValueError('Path escapes inspected root')
            current=current.parent;continue
        current=current/part
        if current.is_symlink():
            traversals+=1
            if traversals>40:raise ValueError('Image symlink loop')
            target=Path(os.readlink(current));current=root if target.is_absolute() else current.parent
            parts=list(target.parts[1:] if target.is_absolute() else target.parts)+parts
    return current


def pacman_configuration(root,allowed=('core','extra')):
    visited=set();active=set();files=[];repositories=set();findings=[];values=[]
    def read(name,section=''):
        path=inside(root,name)
        if path in active:raise ValueError('Cyclic pacman include')
        if len(active)>64 or len(visited)>128:raise ValueError('Pacman include limit exceeded')
        if not path.is_file():raise ValueError('Missing pacman configuration include')
        if not path.resolve().is_relative_to(root):raise ValueError('Configuration leaves inspected root')
        if path.stat().st_size>1024*1024:raise ValueError('Configuration exceeds size limit')
        active.add(path)
        if path not in visited:
            info=path.stat();files.append({'path':name,'sha256':sha(path),'uid':info.st_uid,'mode':oct(stat.S_IMODE(info.st_mode))})
            visited.add(path)
        for line_number,line in enumerate(path.read_text().splitlines(),1):
            text=line.split('#',1)[0].strip()
            if not text:continue
            if INHERITED.search(text):findings.append({'path':name,'line':line_number,'reason':'inherited active configuration'})
            if text.startswith('[') and text.endswith(']'):
                section=text[1:-1]
                if section!='options':repositories.add(section)
                continue
            key,separator,value=text.partition('=')
            if separator and key.strip()=='Include':
                pattern=value.strip()
                if not pattern.startswith('/') or '..' in Path(pattern).parts:
                    raise ValueError('Include must be an absolute image path')
                matches=sorted(glob.glob(str(root/pattern.lstrip('/'))))
                if not matches:raise ValueError('Unresolved pacman include')
                for match in matches:section=read('/'+Path(match).relative_to(root).as_posix(),section)
            elif separator:
                if key.strip() in ('Server','SigLevel','LocalFileSigLevel','RemoteFileSigLevel','IgnorePkg'):
                    values.append({'section':section,'key':key.strip(),'value':value.strip()})
        active.remove(path)
        return section
    read('/etc/pacman.conf')
    unexpected=sorted(repositories-set(allowed))
    if unexpected:findings.append({'reason':'undeclared repositories','repositories':unexpected})
    # Record all trust controls, including permissive ones; never infer trust
    # merely from a familiar repository name or an existing keyring file.
    return {'files':files,'repositories':sorted(repositories),'controls':values,'findings':findings}


def package_database(root):
    packages=[];owners={};errors=[]
    for directory in sorted(inside(root,'/var/lib/pacman/local').iterdir()):
        if directory.is_symlink():raise ValueError('Redirected package database directory')
        if not directory.is_dir():continue
        desc=directory/'desc';listing=directory/'files'
        if desc.is_symlink() or listing.is_symlink():raise ValueError('Redirected package metadata')
        if not desc.is_file():continue
        if desc.stat().st_size>1024*1024 or (listing.exists() and listing.stat().st_size>16*1024*1024):
            raise ValueError('Package metadata exceeds limit')
        fields={};key=None
        for line in desc.read_text().splitlines():
            if line.startswith('%') and line.endswith('%'):key=line.strip('%');fields[key]=[]
            elif line and key:fields[key].append(line)
        try:name=fields['NAME'][0];version=fields['VERSION'][0]
        except (KeyError,IndexError):raise ValueError('Incomplete native package metadata')
        packages.append({'name':name,'version':version,'metadataSha256':sha(desc)})
        if INHERITED.search(name):errors.append({'package':name,'reason':'inherited installed package'})
        if listing.is_file():
            in_files=False
            for line in listing.read_text().splitlines():
                if line.startswith('%'):in_files=line=='%FILES%';continue
                if in_files and line and not line.endswith('/'):
                    if line.startswith('/') or '..' in Path(line).parts:raise ValueError('Unsafe package-owned path')
                    owners.setdefault('/'+line,[]).append(name)
    return packages,owners,errors


def collect(root,allowed=('core','extra')):
    root=root.resolve(strict=True)
    os_release=inside(root,'/etc/os-release')
    if not os_release.is_file():raise ValueError('Missing native OS identity')
    identity={}
    for line in os_release.read_text().splitlines():
        key,separator,value=line.partition('=')
        if separator and key in ('ID','ID_LIKE','NAME'):identity[key]=value.strip('"')
    if identity.get('ID')!='arch':raise ValueError('Expected clean Arch host')
    repositories=pacman_configuration(root,allowed)
    packages,owners,findings=package_database(root)
    if any(INHERITED.search(v) for v in identity.values()):findings.append({'reason':'inherited active OS metadata'})
    for row in repositories['files']:
        if row['uid']!=0 or int(row['mode'],8) & 0o022:
            findings.append({'path':row['path'],'reason':'untrusted native repository configuration permissions'})
    files=[]
    for name in CRITICAL:
        path=inside(root,name)
        row={'path':name,'packages':owners.get(name,[]),'present':path.is_file()}
        if row['present']:
            info=path.stat();row.update(uid=info.st_uid,mode=oct(stat.S_IMODE(info.st_mode)),sha256=sha(path))
            if len(row['packages'])!=1:findings.append({'path':name,'reason':'missing or ambiguous native package owner'})
            if info.st_uid!=0 or info.st_mode & 0o022:findings.append({'path':name,'reason':'untrusted native endpoint permissions'})
        else:findings.append({'path':name,'reason':'missing native endpoint'})
        files.append(row)
    keyrings=[]
    for path in sorted(inside(root,'/usr/share/pacman/keyrings').glob('*')):
        if path.is_symlink():raise ValueError('Redirected public keyring artifact')
        if not path.is_file():continue
        name='/'+path.relative_to(root).as_posix()
        keyrings.append({'path':name,'sha256':sha(path),'packages':owners.get(name,[])})
        if INHERITED.search(path.name):findings.append({'path':name,'reason':'inherited native keyring'})
    # Post-install verification remains required for hooks, service policy,
    # effective authentication/portals and package removal transactions.
    return {'os':identity,'repositories':repositories,'packages':packages,
        'criticalFiles':files,'keyrings':keyrings,'findings':findings,
        'scope':'Read actual native database, active pacman includes and selected file ownership; no service/authentication/removal acceptance.'}


def egress_observations():
    observations=[]
    start=time.monotonic()
    try:
        with socket.create_connection(('1.1.1.1',443),timeout=3):outcome='connected'
    except OSError as error:outcome=type(error).__name__
    observations.append({'kind':'tcp-connect','endpoint':'1.1.1.1:443','attempted':True,
                         'outcome':outcome,'elapsedSeconds':round(time.monotonic()-start,3)})
    args=['/usr/bin/curl','--silent','--show-error','--connect-timeout','3','--max-time','5',
          '--output','/dev/null','--write-out','%{http_code} %{size_download} %{remote_ip}',
          'https://archlinux.org/']
    start=time.monotonic();result=subprocess.run(args,capture_output=True,text=True,timeout=8,
        env={'PATH':'/usr/bin:/bin','LANG':'C'})
    observations.append({'kind':'dns-https','endpoint':'https://archlinux.org/','attempted':True,
        'exit':result.returncode,'transfer':result.stdout.strip(),'stderr':result.stderr[:500],
        'elapsedSeconds':round(time.monotonic()-start,3),'clientSha256':sha(Path('/usr/bin/curl'))})
    return {'observations':observations,'scope':'Bounded explicit probes to independent endpoints. This does not trace every application or establish absence of inherited fallback attempts.'}


def active_keyring():
    directory=Path('/etc/pacman.d/gnupg')
    files=[]
    for name in ('pubring.gpg','pubring.kbx','trustdb.gpg'):
        path=directory/name
        if path.is_file():files.append({'path':str(path),'sha256':sha(path)})
    args=['/usr/bin/gpg','--options','/dev/null','--homedir',str(directory),
          '--no-auto-check-trustdb','--lock-never','--with-colons','--list-keys']
    result=subprocess.run(args,capture_output=True,text=True,timeout=15,
                          env={'PATH':'/usr/bin:/bin','LANG':'C'})
    fingerprints=[];inherited=[];primary=None;need_primary=False
    for line in result.stdout.splitlines():
        fields=line.split(':')
        if fields[0]=='pub':need_primary=True;primary=None
        elif fields[0]=='fpr' and need_primary:
            primary=fields[9];fingerprints.append(primary);need_primary=False
        elif fields[0]=='uid' and INHERITED.search(fields[9]):
            inherited.append(primary)
    return {'files':files,'exit':result.returncode,'primaryFingerprints':sorted(set(fingerprints)),
            'inheritedUidKeys':sorted(set(p for p in inherited if p)),
            'scope':'Read existing native public keys without trust-database refresh or key retrieval; staged archive signature checks remain separate.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('/'))
    parser.add_argument('--allowed-repository',action='append')
    parser.add_argument('--egress',action='store_true',help='Observe bounded actual probes on the current host')
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if args.egress and args.root.resolve()!=Path('/'):
        parser.error('Network observations apply only to the currently running root')
    native=collect(args.root,tuple(args.allowed_repository or ('core','extra')))
    report={'schema':1,'stage':'Develop; partial raw observations','candidateReady':False,
        'collectorSha256':sha(Path(__file__).resolve()),'native':native,
        'activeNativeKeyring':active_keyring() if args.root.resolve()==Path('/') else None,
        'egress':egress_observations() if args.egress else None,
        'limits':'Bind these observations to one complete artifact tuple and required-case proofs; this report alone does not close I02/I05.'}
    with args.report.open('x') as handle:
        os.fchmod(handle.fileno(),0o600)
        handle.write(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'packages':len(native['packages']),'criticalFiles':len(native['criticalFiles']),
        'findings':len(native['findings'])+len(native['repositories']['findings']),
        'egressObserved':args.egress,'candidateReady':False}))


if __name__=='__main__':
    import sys
    try:main()
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        sys.exit('collect-clean-host: '+str(error))
