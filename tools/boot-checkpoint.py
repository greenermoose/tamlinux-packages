#!/usr/bin/env python3
"""Capture/verify a reviewed boot recovery set; never change installed state.

The caller supplies exact absolute paths and package archive hashes. Capture
preserves numeric ownership, modes, symlinks, ACLs and xattrs using GNU tar.
Read-only status commands accompany CLI capture. No package installation,
mount, firmware write, service change or image-generation command is executed.
Writers must be quiescent for the final checkpoint before a live transaction.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tarfile


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative(path):
    p = PurePosixPath(path)
    if not p.is_absolute() or '..' in p.parts or str(p) != path or p == PurePosixPath('/'):
        raise ValueError(f'Expected a canonical absolute non-root path: {path}')
    return str(p).removeprefix('/')


def inventory(root, paths):
    records = {}
    def visit(name):
        if name in records:
            return
        path = root / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            records[name] = {'type': 'absent'}
            return
        value = dict(mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, gid=info.st_gid)
        if stat.S_ISLNK(info.st_mode):
            value.update(type='symlink', target=os.readlink(path))
        elif stat.S_ISREG(info.st_mode):
            value.update(type='file', size=info.st_size, sha256=sha(path))
        elif stat.S_ISDIR(info.st_mode):
            value.update(type='directory')
        else:
            raise ValueError(f'Unsupported special file: {name}')
        records[name] = value
        if len(records) > 20000:
            raise ValueError('Checkpoint exceeds 20000 paths')
        if value['type'] == 'directory':
            for child in sorted(path.iterdir()):
                visit(str(child.relative_to(root)))
    for path in paths:
        name = relative(path)
        # Reject symlink ancestors, which could escape the reviewed scope.
        for ancestor in (root / name).parents:
            if ancestor == root:
                break
            if ancestor.is_symlink():
                raise ValueError(f'Symlink ancestor for {name}: {ancestor}')
        visit(name)
    return records


def verify(destination):
    if (destination / 'INCOMPLETE').exists():
        raise ValueError('Checkpoint is marked incomplete')
    record = json.loads((destination / 'checkpoint.json').read_text())
    archive = destination / 'state.tar'
    if sha(archive) != record['archiveSha256']:
        raise ValueError('Checkpoint archive hash mismatch')
    expected = {k: v for k, v in record['files'].items() if v['type'] != 'absent'}
    seen = set()
    with tarfile.open(archive) as source:
        for member in source:
            name = member.name.rstrip('/')
            if name not in expected or name in seen:
                raise ValueError(f'Unexpected/duplicate archive member: {name}')
            seen.add(name)
            value = expected[name]
            if (member.uid, member.gid, member.mode) != (value['uid'], value['gid'], value['mode']):
                raise ValueError(f'Archive metadata mismatch: {name}')
            if value['type'] == 'symlink':
                good = member.issym() and member.linkname == value['target']
            elif value['type'] == 'directory':
                good = member.isdir()
            else:
                stream = source.extractfile(member) if member.isfile() or member.islnk() else None
                good = stream is not None and hashlib.file_digest(stream, 'sha256').hexdigest() == value['sha256']
            if not good:
                raise ValueError(f'Archive content/type mismatch: {name}')
    if seen != set(expected):
        raise ValueError('Archive is missing checkpoint paths')
    for package in record['packages']:
        if sha(destination / 'packages' / package['archive']) != package['sha256']:
            raise ValueError(f'Retained package hash mismatch: {package["archive"]}')
    return record


def capture(spec, root, destination, tar=Path('/usr/bin/tar')):
    if destination.exists() or destination.is_symlink():
        raise ValueError('Checkpoint destination exists; choose a new one')
    if (root / 'var/lib/pacman/db.lck').exists():
        raise ValueError('A package transaction lock exists')
    for path in spec['paths']:
        scope = root / relative(path)
        if destination == scope or scope in destination.parents:
            raise ValueError('Checkpoint destination is inside a captured scope')
    before = inventory(root, spec['paths'])
    if sum(v.get('size', 0) for v in before.values()) > 8 * 1024**3:
        raise ValueError('Checkpoint exceeds 8 GiB')
    destination.mkdir(mode=0o700, parents=True)
    try:
        (destination / 'packages').mkdir()
        packages = []
        for value in spec['packages']:
            source = root / relative(value['path'])
            if not source.is_file() or source.is_symlink() or sha(source) != value['sha256']:
                raise ValueError(f'Missing/changed package archive: {value["path"]}')
            if (destination / 'packages' / source.name).exists():
                raise ValueError(f'Duplicate package archive basename: {source.name}')
            target = destination / 'packages' / source.name
            shutil.copyfile(source, target)
            if sha(target) != value['sha256']:
                raise ValueError('Package changed during checkpoint')
            packages.append(dict(archive=source.name, sha256=value['sha256']))
        names = [name for name, v in sorted(before.items()) if v['type'] != 'absent']
        subprocess.run([str(tar), '--acls', '--xattrs', '--numeric-owner', '--format=pax',
                        '--no-recursion', '-cpf', str(destination / 'state.tar'),
                        '-C', str(root), '--null', '-T', '-'],
                       input=b''.join(os.fsencode(n) + b'\0' for n in names),
                       check=True, capture_output=True, timeout=300)
        after = inventory(root, spec['paths'])
        if before != after:
            raise ValueError('Boot state changed during checkpoint; quiesce writers and retry')
        record = dict(schema=1, files=before, packages=packages,
                      archiveSha256=sha(destination / 'state.tar'),
                      spec=spec, restored=False, installedStateChanged=False)
        (destination / 'checkpoint.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        verify(destination)
        (destination / 'VERIFIED').write_text(record['archiveSha256'] + '\n')
        return record
    except BaseException:
        # Preserve failed evidence; never leave an apparent success marker.
        (destination / 'INCOMPLETE').write_text('Capture failed; this is not a rollback checkpoint.\n')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('capture', 'verify'))
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--spec', type=Path)
    args = parser.parse_args()
    if args.action == 'verify':
        record = verify(args.destination)
    else:
        if os.geteuid() != 0 or args.spec is None:
            parser.error('capture needs root and --spec; verify does not')
        observations = []
        commands = [
            ['/usr/bin/pacman', '-Q'], ['/usr/bin/pacman', '-Qqe'],
            ['/usr/bin/pacman', '-Qqd'], ['/usr/bin/efibootmgr', '-v'],
            ['/usr/bin/findmnt', '--json'],
            ['/usr/bin/systemctl', 'show', 'limine-snapper-sync.service',
             'snapper-cleanup.timer', 'snapper-cleanup.service',
             'snapper-timeline.timer', 'snapper-timeline.service',
             '-p', 'Id', '-p', 'LoadState', '-p', 'ActiveState',
             '-p', 'SubState', '-p', 'UnitFileState'],
        ]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=30, env={'PATH': '/usr/bin', 'LC_ALL': 'C'})
            observations.append(dict(argv=command, returncode=result.returncode,
                                     stdout=result.stdout, stderr=result.stderr))
            if result.returncode:
                raise ValueError(f'Cannot record recovery status: {command}')
        record = capture(json.loads(args.spec.read_text()), Path('/'), args.destination.absolute())
        (args.destination / 'observations.json').write_text(json.dumps(observations, indent=2) + '\n')
    summary = dict(archiveSha256=record['archiveSha256'], paths=len(record['files']),
                   packages=record['packages'], installedStateChanged=False)
    observations_file = args.destination / 'observations.json'
    if observations_file.is_file():
        summary['writerStates'] = [v for v in json.loads(observations_file.read_text())
                                   if v['argv'][0].endswith('/systemctl')]
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
