#!/usr/bin/env python3
"""Stage a finite owned native source bundle and digest-bound Arch recipe."""
import argparse
import hashlib
import io
import json
from pathlib import Path
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
    ('session','tamlinux.desktop','tamlinux.conf','org.tamlinux.native.policy',
     '50-tamlinux-hyprland-pause.hook','50-tamlinux-hyprland-resume.hook','LICENSE')},
}


def prepare(product,destination,revision):
    if destination.resolve().is_relative_to(product.resolve()):
        raise ValueError("Keep native staging outside the maintained product tree")
    files={}
    for name,relative in FILES.items():
        source=product/relative
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(product.resolve()):raise ValueError('Expected maintained source: '+relative)
        files[name]=source.read_bytes()
    manifest={'schema':1,'stage':'Develop; no candidate promotion', 'productRevision':revision,
        'origin':'https://github.com/greenermoose/tamlinux','files':
        {name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())},
        'scope':'Owned login registration, explicit browser/Apple authorization, reload hooks and transient elevation cleanup.',
        'pending':['native root/security/service recovery beyond browser policies','KMS bridge','separate boot handoff','physical authentication/device proof']}
    files['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    destination.mkdir(mode=0o700,parents=True,exist_ok=False)
    archive=destination/'tamlinux-native-source.tar'
    with tarfile.open(archive,'w') as handle:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo('tamlinux-native/'+name);entry.size=len(data)
            entry.mode=0o644;entry.mtime=0;entry.uid=entry.gid=0
            handle.addfile(entry,io.BytesIO(data))
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
