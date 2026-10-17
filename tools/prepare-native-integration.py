#!/usr/bin/env python3
"""Stage a finite owned native source bundle and digest-bound Arch recipe."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]
FILES={
 'theme-browser-policy':'desktop/native/theme-browser-policy',
 'browser_policy.py':'desktop/native/browser_policy.py',
 'pam-transaction.py':'desktop/native/pam-transaction.py',
 'hyprland-reload-guard':'commands/tam-hyprland-reload-guard/tam-hyprland-reload-guard',
 'guard-LICENSE':'commands/tam-hyprland-reload-guard/LICENSE',
 **{'asdcontrol/'+name:'desktop/native/providers/asdcontrol/'+name for name in
    ('asdcontrol.cpp','Makefile','LICENSE','origins.json')},
 **{'integration/'+name:'desktop/native/integration/'+name for name in
    ('session','tamlinux.desktop','tamlinux.conf','org.tamlinux.native.policy',
     '50-tamlinux-hyprland-pause.hook','50-tamlinux-hyprland-resume.hook','LICENSE')},
 **{'integration/sddm/'+name:'desktop/native/integration/sddm/'+name for name in
    ('Main.qml','metadata.desktop','hyprland.lua','20-tamlinux.conf')},
 'defaults/LICENSE':'desktop/native/defaults/LICENSE-defaults',
 'defaults/convert.py':'desktop/native/defaults/convert.py',
 'defaults/native_recovery.py':'desktop/migration/recovery.py',
}
DEFAULTS='desktop/native/defaults'


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


def prepare(product,destination,revision):
    if destination.resolve().is_relative_to(product.resolve()):
        raise ValueError("Keep native staging outside the maintained product tree")
    files={}
    for name,relative in FILES.items():
        source=product/relative
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(product.resolve()):raise ValueError('Expected maintained source: '+relative)
        files[name]=source.read_bytes()
    special=defaults(product)
    files.update({name:data for name,(mode,data) in special.items() if mode!='link'})
    manifest={'schema':1,'stage':'Develop; no candidate promotion', 'productRevision':revision,
        'origin':'https://github.com/greenermoose/tamlinux','files':
        {name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())},
        'links':{name:target for name,(mode,target) in sorted(special.items()) if mode=='link'},
        'scope':'Owned login registration and SDDM greeter/vendor configuration, explicit browser/Apple authorization, reload hooks, transient elevation cleanup, vendor defaults, checkpointed native conversion and the candidate-bound SDDM PAM transaction.',
        'pending':['native root/security/service recovery beyond browser policies','KMS bridge','separate boot handoff','physical authentication/device proof',
                   'explicit tam-native-defaults transaction, service reloads and effective native-defaults verification before Desktop Test',
                   'provisioning must run systemctl preset for systemd-oomd']}
    files['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    destination.mkdir(mode=0o700,parents=True,exist_ok=False)
    archive=destination/'tamlinux-native-source.tar'
    with tarfile.open(archive,'w') as handle:
        for name in sorted({**files,**special}):
            entry=tarfile.TarInfo('tamlinux-native/'+name);entry.mtime=0;entry.uid=entry.gid=0
            mode,payload=special.get(name,(0o644,files.get(name)))
            if mode=='link':
                entry.type=tarfile.SYMTYPE;entry.linkname=payload;entry.mode=0o777
                handle.addfile(entry);continue
            entry.size=len(payload);entry.mode=mode
            handle.addfile(entry,io.BytesIO(payload))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    recipe=(ROOT/'contracts/providers/recipes/tamlinux-native/PKGBUILD.in').read_text().replace('@SOURCE_SHA256@',digest)
    (destination/'PKGBUILD').write_text(recipe)
    result={'schema':1,'sourceSha256':digest,'recipeSha256':hashlib.sha256(recipe.encode()).hexdigest(),
            'manifest':manifest,'candidateReady':False}
    (destination/'selection.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--revision',required=True)
    args=parser.parse_args()
    try:
        result=prepare(args.product.resolve(strict=True),args.destination.absolute(),args.revision)
    except (OSError,ValueError) as error:parser.exit(2,str(error)+'\n')
    print(json.dumps({k:result[k] for k in ('sourceSha256','recipeSha256','candidateReady')}))
