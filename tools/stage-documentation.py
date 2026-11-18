#!/usr/bin/env python3
"""Stage optional documentation from hash-pinned native archives, never live files."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile


def _default_archwiki_preprocessor():
    candidate = Path(__file__).resolve().parents[2] / 'tam/tools/build-archwiki-tam.py'
    return candidate if candidate.is_file() else None


def stage(destination, sources, cache, archwiki_preprocessor=None):
    destination = Path(destination)
    root = destination / 'placed/usr/share/doc'
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('expected a real unpublished bundle directory')
    if sources.get('format') != 1 or not isinstance(sources.get('archives'), list):
        raise ValueError('unsupported documentation source list')
    recorded = {'info': [], 'arch-wiki': []}
    archwiki_archives = {}
    has_archwiki_pair = (
        any(s.get('collection') == 'archwiki' for s in sources['archives'])
        and any(s.get('collection') == 'archwiki-lite' for s in sources['archives'])
    )
    total = 0
    for source in sources['archives']:
        kind = source['collection']
        if kind not in ('info', 'archwiki', 'archwiki-lite'):
            raise ValueError('unsupported native documentation collection')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+\-]*', source['package']):
            raise ValueError('invalid documentation package name')
        filename = source['archive']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+\-]*\.pkg\.tar\.(zst|xz|gz)', filename):
            raise ValueError('invalid native archive name')
        archive = Path(cache) / filename
        fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not __import__('stat').S_ISREG(before.st_mode) or hashlib.file_digest(stream, 'sha256').hexdigest() != source['sha256']:
                raise ValueError('documentation archive hash differs: ' + filename)
            stream.seek(0)
            # bsdtar converts compression to a tar stream, without extracting
            # or executing package hooks. Python validates every destination.
            process = subprocess.Popen(['/usr/bin/bsdtar', '-cf', '-', '@/proc/self/fd/' + str(stream.fileno())],
                                       pass_fds=(stream.fileno(),), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            prefix = 'usr/share/info/' if kind == 'info' else 'usr/share/doc/arch-wiki/'
            collection = 'info' if kind == 'info' else 'arch-wiki'
            count = 0
            try:
                with tarfile.open(fileobj=process.stdout, mode='r|') as packed:
                    for entry in packed:
                        name = entry.name.removeprefix('./')
                        license_prefix = 'usr/share/licenses/' + source['package'] + '/'
                        is_license = name.startswith(license_prefix)
                        if not name.startswith(prefix) and not is_license:
                            continue
                        relative = PurePosixPath('licenses/' + source['package'] + '/' + name[len(license_prefix):] if is_license else name[len(prefix):])
                        if relative.is_absolute() or '..' in relative.parts:
                            raise ValueError('unsafe documentation archive path')
                        if entry.isdir():
                            continue
                        if not entry.isfile() or entry.size > 64 * 1024 * 1024:
                            raise ValueError('unsupported documentation archive entry')
                        if kind == 'info' and str(relative) == 'dir':
                            continue
                        if has_archwiki_pair and kind in ('archwiki', 'archwiki-lite') and not is_license:
                            count += 1
                            continue
                        total += entry.size
                        if total > 2 * 1024 * 1024 * 1024:
                            raise ValueError('documentation exceeds size limit')
                        target = root / collection / relative
                        if any(parent.is_symlink() for parent in target.parents):
                            raise ValueError('redirected documentation destination')
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with target.open('xb') as out:
                            with packed.extractfile(entry) as incoming:
                                __import__('shutil').copyfileobj(incoming, out)
                        target.chmod(0o644)
                        if not is_license:
                            count += 1
                if process.wait() != 0:
                    raise ValueError('could not read documentation archive')
            finally:
                process.stdout.close()
                if process.poll() is None:
                    process.terminate()
                process.wait()
                process.stderr.close()
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_ctime_ns) != (after.st_size, after.st_ctime_ns):
                raise ValueError('documentation archive changed during staging')
        if not count:
            raise ValueError('native archive contains no requested documentation: ' + filename)
        if kind in ('archwiki', 'archwiki-lite'):
            archwiki_archives[kind] = archive
        recorded[collection].append({key: source[key] for key in ('package', 'version', 'archive', 'sha256')})
    if has_archwiki_pair:
        preprocessor = Path(archwiki_preprocessor) if archwiki_preprocessor else _default_archwiki_preprocessor()
        if preprocessor is None or not preprocessor.is_file():
            raise ValueError('missing Arch Wiki tam pre-processor script')
        tam_out = root / 'arch-wiki/tam'
        subprocess.run(
            [
                '/usr/bin/python3',
                str(preprocessor),
                '--docs', str(archwiki_archives['archwiki']),
                '--lite', str(archwiki_archives['archwiki-lite']),
                '--output', str(tam_out),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    info = root / 'info'
    if recorded['info']:
        manuals = sorted(path for path in info.iterdir() if re.search(r'\.info(?:\.(?:gz|xz|bz2|zst))?$', path.name))
        for manual in manuals:
            subprocess.run(['/usr/bin/install-info', '--info-dir=' + str(info), str(manual)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for collection, archives in recorded.items():
        if archives:
            (root / collection / 'SOURCE.json').write_text(json.dumps({'format': 1, 'archives': archives}, indent=2) + '\n')
    return recorded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--sources-json', required=True)
    parser.add_argument('--native-archives', default='/var/cache/pacman/pkg', type=Path)
    args = parser.parse_args()
    try:
        stage(args.destination, json.loads(args.sources_json), args.native_archives)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError, tarfile.TarError) as error:
        parser.exit(1, 'documentation staging: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
