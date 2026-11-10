#!/usr/bin/env python3
"""Stage a finite owned native source bundle and digest-bound Arch recipe."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]
FILES={
 'theme-browser-policy':'desktop/native/theme-browser-policy',
 'browser_policy.py':'desktop/native/browser_policy.py',
 'hyprland-reload-guard':'commands/tam-hyprland-reload-guard/tam-hyprland-reload-guard',
 'guard-LICENSE':'commands/tam-hyprland-reload-guard/LICENSE',
 **{'asdcontrol/'+name:'desktop/native/providers/asdcontrol/'+name for name in
    ('asdcontrol.cpp','Makefile','LICENSE','origins.json')},
 **{'integration/'+name:'desktop/native/integration/'+name for name in
    ('session','tamlinux.conf','org.tamlinux.native.policy',
     '50-tamlinux-hyprland-pause.hook','50-tamlinux-hyprland-resume.hook','LICENSE')},
 'defaults/LICENSE':'desktop/native/defaults/LICENSE-defaults',
 'defaults/convert.py':'desktop/native/defaults/convert.py',
 'defaults/native_recovery.py':'desktop/migration/recovery.py',
 'console/console-welcome.py':'desktop/session/console-welcome.py',
 'console/version':'VERSION',
 'console/cultivar':'CULTIVAR',
}
DEFAULTS='desktop/native/defaults'


def bundle_sources(lock, repos):
    """Export the rollback tool and core library from explicit locked commits."""
    selected={}
    lines=lock.read_text().splitlines()
    if not lines or lines[0]!='format 1':raise ValueError('Unsupported bundle lock format')
    for line in lines[1:]:
        if not line.strip() or line.startswith('#'):continue
        fields=line.split()
        if len(fields)!=4 or fields[0]!='component' or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',fields[3]):
            raise ValueError('Invalid component lock line')
        if fields[1] in selected:raise ValueError('Duplicate locked component')
        selected[fields[1]]=fields[3]
    files={};modes={};pins={}
    for name,dest in (('libtam','bundle-lib'),('tamlinux-tools','bundle-tool')):
        if name not in selected:raise ValueError('Missing bundle build pin: '+name)
        commit=selected[name];repo=repos/name
        result=subprocess.run(['git','-C',str(repo),'archive','--format=tar',commit],
                              check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
            for entry in archive:
                relative=Path(entry.name)
                if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe source archive path')
                if not entry.isfile():
                    if entry.isdir():continue
                    raise ValueError('Bundle tool sources must be regular files: '+entry.name)
                if relative.parts[0] not in ('Makefile','LICENSE','include','src','data','man'):continue
                path=dest+'/'+entry.name
                files[path]=archive.extractfile(entry).read()
                # Git records the executable bit, not an archive process's
                # umask-derived group-write bits.
                modes[path]=0o755 if entry.mode & 0o111 else 0o644
        pins[name]=commit
    return files,modes,pins


def defaults(product):
    """Return the recorded vendor defaults tree: name -> (mode, bytes) or ('link', target)."""
    base=product/DEFAULTS;root=(base/'root').resolve()
    recorded=json.loads((base/'origins.json').read_text())['files']
    present={str(p.relative_to(base/'root')) for p in (base/'root').rglob('*') if p.is_symlink() or p.is_file()}
    if present!=set(recorded):raise ValueError('Defaults tree differs from origins.json: '+', '.join(sorted(present^set(recorded))))
    selected={}
    for relative,entry in sorted(recorded.items()):
        if not relative.startswith(('usr/lib/','usr/share/')) or '..' in relative.split('/'):raise ValueError('Defaults must stay in vendor locations: '+relative)
        path=base/'root'/relative
        if 'link' in entry:
            target=os.readlink(path)
            if target!=entry['link'] or not path.resolve().is_relative_to(root) or not path.resolve().is_file():raise ValueError('Unexpected defaults link: '+relative)
            selected['defaults/root/'+relative]=('link',target)
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Expected maintained source: '+relative)
        data=path.read_bytes();mode=path.stat().st_mode&0o7777
        if hashlib.sha256(data).hexdigest()!=entry['sha256'] or format(mode,'04o')!=entry['mode']:raise ValueError('Defaults digest or mode differs: '+relative)
        selected['defaults/root/'+relative]=(mode,data)
    return selected


def prepare(product,destination,revision,bundle_lock=None,repos=None):
    if destination.resolve().is_relative_to(product.resolve()):
        raise ValueError("Keep native staging outside the maintained product tree")
    files={}
    for name,relative in FILES.items():
        source=product/relative
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(product.resolve()):raise ValueError('Expected maintained source: '+relative)
        files[name]=source.read_bytes()
    version = files.pop('console/version').decode('ascii').strip()
    files.pop('console/cultivar')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Native package requires a plain product version')
    special=defaults(product)
    files.update({name:data for name,(mode,data) in special.items() if mode!='link'})
    bundle_modes={};bundle_pins={}
    if bundle_lock is not None:
        if repos is None:raise ValueError('Bundle adapter build needs --repos with the locked local sources')
        extra,bundle_modes,bundle_pins=bundle_sources(bundle_lock,repos)
        files.update(extra)
        for name in ('tamlinux.sh','50-tamlinux.conf','20-tamlinux-bundle.conf'):
            path=product/'desktop/native/integration/bundle'/name
            if path.is_symlink() or not path.is_file():raise ValueError('Missing bundle adapter integration: '+name)
            files['bundle-integration/'+name]=path.read_bytes()
    # Candidate labels and source revision are provenance, not native behavior.
    # This identity also covers the recipe, dependencies, modes and symlinks.
    recipe_template=(ROOT/'contracts/providers/recipes/tamlinux-native/PKGBUILD.in').read_bytes()
    identity={'files':{name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())},
              'special':{name:[mode, payload if mode=='link' else hashlib.sha256(payload).hexdigest()]
                         for name,(mode,payload) in sorted(special.items())},
              'recipe':hashlib.sha256(recipe_template).hexdigest(),
              'bundleSources':bundle_pins,'bundleModes':bundle_modes,
              'preparer':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    payload_id=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    manifest={'schema':2,'payloadId':payload_id,'interface':1,'stage':'Develop; no candidate promotion', 'productRevision':revision,
        'origin':'https://github.com/greenermoose/tamlinux','files':
        {name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())},
        'links':{name:target for name,(mode,target) in sorted(special.items()) if mode=='link'},
        'scope':'Console welcome and explicit desktop entry, browser/Apple authorization, reload hooks, transient elevation cleanup, vendor defaults and checkpointed native conversion. No display manager, greeter or graphical-login PAM transaction.',
        'pending':['native root/security/service recovery beyond browser policies','KMS bridge','separate boot handoff','physical authentication/device proof',
                   'explicit tam-native-defaults transaction, service reloads and effective native-defaults verification before Desktop Test',
                   'provisioning must run systemctl preset for systemd-oomd']}
    if bundle_pins:
        manifest['bundleSources']=bundle_pins
        manifest['bundleSlot']='/usr/lib/tamlinux'
    files['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    destination.mkdir(mode=0o700,parents=True,exist_ok=False)
    archive=destination/'tamlinux-native-source.tar'
    with tarfile.open(archive,'w') as handle:
        for name in sorted({**files,**special}):
            entry=tarfile.TarInfo('tamlinux-native/'+name);entry.mtime=0;entry.uid=entry.gid=0
            mode,payload=special.get(name,(bundle_modes.get(name,0o644),files.get(name)))
            if mode=='link':
                entry.type=tarfile.SYMTYPE;entry.linkname=payload;entry.mode=0o777
                handle.addfile(entry);continue
            entry.size=len(payload);entry.mode=mode
            handle.addfile(entry,io.BytesIO(payload))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    recipe=(ROOT/'contracts/providers/recipes/tamlinux-native/PKGBUILD.in').read_text().replace('@SOURCE_SHA256@',digest).replace('@PRODUCT_VERSION@', version).replace('@PKGREL@','0.2' if bundle_pins else '0.1')
    (destination/'PKGBUILD').write_text(recipe)
    result={'schema':2,'payloadId':payload_id,'interface':1,'sourceSha256':digest,'recipeSha256':hashlib.sha256(recipe.encode()).hexdigest(),
            'manifest':manifest,'candidateReady':False}
    (destination/'selection.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--revision',required=True)
    parser.add_argument('--bundle-lock',type=Path,help='include tam-bundle and its environment from these exact source pins')
    parser.add_argument('--repos',type=Path,help='local clones holding the locked libtam and tamlinux-tools sources')
    args=parser.parse_args()
    try:
        result=prepare(args.product.resolve(strict=True),args.destination.absolute(),args.revision,args.bundle_lock,args.repos)
    except (OSError,ValueError,subprocess.CalledProcessError) as error:parser.exit(2,str(error)+'\n')
    print(json.dumps({k:result[k] for k in ('sourceSha256','recipeSha256','candidateReady')}))
