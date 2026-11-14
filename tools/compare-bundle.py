#!/usr/bin/env python3
"""Explain file-list differences between a bundle and selected old outputs."""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def files(root):
    result=set()
    for path in root.rglob('*'):
        if not (path.is_symlink() or path.is_file()):continue
        name=str(path.relative_to(root))
        # Nix's wrapper retains its original in a hidden sibling. The
        # logical command/helper is already included under its normal name.
        if path.name.startswith('.') and path.name.endswith('-wrapped'):continue
        if name.startswith('share/man/') and name.endswith('.gz'):name=name[:-3]
        # Compare old immutable product documentation with its renamed path.
        if name.startswith('share/tamlinux/') and name.endswith('/README.md'):name=name[:-3]
        result.add(name)
    return result


def explanation(path, added):
    if not added:
        if path.startswith(('share/fonts/opentype/AtkinsonHyperlegible-',
                            'share/fonts/opentype/NerdFonts/AtkynsonMono/',
                            'share/fonts/truetype/NerdFonts/JetBrainsMono/')):
            return 'third-party fonts move to native dependencies'
        if path=='share/tamlinux/source-revision':return 'source identity is recorded in BUNDLE'
    else:
        if path in ('BUNDLE','MANIFEST'):return 'bundle identity and file manifest'
        if path=='share/man/index.db':return 'manual index is switched with the pages'
        if path.startswith('share/systemd/user/'):return 'product user units move out of Home Manager'
        if path.startswith('share/tamlinux/knowledge/'):return 'new pages in the pinned corpus'
        if path=='share/tamlinux/plugins/README':return 'plugin documentation from product sources'
    return 'UNEXPLAINED'


def compare(bundle, baselines):
    old=set().union(*(files(root) for root in baselines));new=files(bundle)
    groups=defaultdict(list)
    for added,paths in ((False,old-new),(True,new-old)):
        for path in sorted(paths):groups[('added' if added else 'removed')+': '+explanation(path,added)].append(path)
    return {'baselineFiles':len(old),'bundleFiles':len(new),'commonFiles':len(old&new),
            'differences':dict(sorted(groups.items())),
            'explained':not any('UNEXPLAINED' in key for key in groups)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--baseline',type=Path,action='append',required=True)
    parser.add_argument('--details',action='store_true',help='print each differing path')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    for path in (args.bundle,*args.baseline):
        if not path.is_dir():parser.error('not a directory: '+str(path))
    report=compare(args.bundle,args.baseline)
    if args.json:print(json.dumps(report,indent=2))
    else:
        print(f"{report['baselineFiles']} old files, {report['bundleFiles']} bundle files, {report['commonFiles']} common paths")
        for reason,paths in report['differences'].items():
            print(f'{len(paths):4} {reason}')
            if args.details:
                for path in paths:print('     '+path)
    return 0 if report['explained'] else 1


if __name__=='__main__':raise SystemExit(main())
