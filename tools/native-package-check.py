#!/usr/bin/env python3
"""Verify a recorded native package before an update or rollback; never install it."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def member(archive, name):
    return subprocess.run(['bsdtar', '-xOf', str(archive), name], check=True,
                          capture_output=True, timeout=10).stdout


def verify(record, archive):
    native = record['nativePackage']
    if archive.name != native['archive'] or not archive.is_file() or archive.is_symlink():
        raise ValueError('native archive name or file does not match the delivery record')
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != native['sha256']:
        raise ValueError('native archive digest differs from the delivery record')
    info = member(archive, '.PKGINFO').decode('utf-8')
    values = dict(line.split(' = ', 1) for line in info.splitlines() if ' = ' in line)
    if values.get('pkgname') != native['name'] or values.get('pkgver') != native['version']:
        raise ValueError('native package identity differs from the delivery record')
    manifest = json.loads(member(archive, 'usr/share/tamlinux/native-integration.json'))
    if manifest['productRevision'] != native['productRevision']:
        raise ValueError('native package product revision differs from the delivery record')
    required = record.get('readiness', {}).get('nativeInstallationRequired', False)
    if required:
        if native['productRevision'] != record['components']['tamlinux']['rev']:
            raise ValueError('native package is not from the selected product revision')
        if native['version'].split('-', 1)[0] != record['version']:
            raise ValueError('native package version differs from the candidate version')
        issue = member(archive, 'usr/lib/issue.d/70-tamlinux.issue').decode('utf-8')
        if 'Welcome to Tamlinux!' not in issue or record['version'] not in issue:
            raise ValueError('native package does not contain the candidate welcome')
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text())
        digest = verify(record, args.archive)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f'native-package-check: {error}\n')
    print(f"verified {args.archive.name} sha256 {digest}; no installation performed")


if __name__ == '__main__':
    main()
