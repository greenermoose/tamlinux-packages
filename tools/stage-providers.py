#!/usr/bin/env python3
"""Verify and stage selected native archives; never install or execute them.

No package database, caller PATH or network is consulted. A successful partial
stage is not a complete native closure, clean-host proof or promotion authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile

INHERITED = re.compile(r'omarchy|omacom|omacom-io|basecamp/omarchy', re.I)
HASH = re.compile(r'[0-9a-f]{64}')
FINGERPRINT = re.compile(r'[0-9A-F]{40,64}')


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Invalid relative artifact path')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or str(p) != value or value == '.':
        raise ValueError(f'Invalid relative artifact path: {value}')
    return value


def checked(path, digest):
    if not isinstance(digest, str) or not HASH.fullmatch(digest):
        raise ValueError(f'Missing/invalid SHA-256 for {path.name}')
    if not path.is_file() or sha(path) != digest:
        raise ValueError(f'Missing/changed artifact: {path.name}')
    return path


def run(tool, args):
    if not tool.is_absolute() or not tool.is_file() or not os.access(tool, os.X_OK):
        raise ValueError('Inspection tools must be explicit absolute executables')
    # Tools are selected by the caller. They are not supplied by an archive.
    result = subprocess.run([str(tool), *map(str, args)], capture_output=True,
                            text=True, timeout=30, env={'PATH': '/nonexistent', 'LC_ALL': 'C'})
    if result.returncode:
        raise ValueError(f'{tool.name} rejected input: {result.stderr.strip()[:500]}')
    if len(result.stdout) > 16 * 1024 * 1024:
        raise ValueError('Inspection output exceeds limit')
    return result.stdout


def fields(text):
    result = {}
    for line in text.splitlines():
        if line.startswith('#') or not line.strip():
            continue
        key, separator, value = line.partition(' = ')
        if not separator:
            raise ValueError('Malformed native package metadata')
        result.setdefault(key, []).append(value)
    return result


def one(metadata, name):
    values = metadata.get(name, [])
    if len(values) != 1:
        raise ValueError(f'Missing/duplicate package field: {name}')
    return values[0]


def inspect_archive(provider, archive, bsdtar):
    names = run(bsdtar, ['-tf', archive]).splitlines()
    normalized = [name.removeprefix('./').rstrip('/') for name in names]
    if len(normalized) != len(set(normalized)):
        raise ValueError('Duplicate archive paths')
    for name in normalized:
        relative(name)
    if '.PKGINFO' not in normalized or '.BUILDINFO' not in normalized:
        raise ValueError('Native artifact needs package and build metadata')
    metadata = fields(run(bsdtar, ['-xOf', archive, names[normalized.index('.PKGINFO')]]))
    build = fields(run(bsdtar, ['-xOf', archive, names[normalized.index('.BUILDINFO')]]))
    for field, expected in [('pkgname', provider['package']), ('pkgver', provider['version']),
                            ('arch', provider['architecture'])]:
        if one(metadata, field) != expected:
            raise ValueError(f'Package {field} does not match selected provider')
    if one(build, 'pkgname') != provider['package'] or one(build, 'pkgver') != provider['version']:
        raise ValueError('Build metadata does not match selected provider')
    if one(build, 'pkgbuild_sha256sum') != provider['recipeSha256']:
        raise ValueError('Build recipe does not match selected provider')
    for name in provider['requiredFiles']:
        if relative(name) not in normalized:
            raise ValueError(f'Missing required provider file: {name}')
    for key in ('pkgname', 'pkgbase', 'url', 'depend', 'provides', 'conflict', 'replaces'):
        if any(INHERITED.search(value) for value in metadata.get(key, [])):
            raise ValueError(f'Inherited active package metadata: {key}')
    if '.INSTALL' in normalized:
        install = run(bsdtar, ['-xOf', archive, names[normalized.index('.INSTALL')]])
        if INHERITED.search(install):
            raise ValueError('Inherited native install script')
    return {'package': provider['package'], 'version': provider['version'],
            'architecture': provider['architecture'], 'dependencies': metadata.get('depend', []),
            'recipeSha256': provider['recipeSha256'], 'requiredFiles': provider['requiredFiles'],
            'fileCount': len(normalized), 'installScript': '.INSTALL' in normalized}


def verify_signature(provider, archive, signature, keyring, gpgv, temporary):
    checked(signature, provider['signature']['sha256'])
    expected = provider['signature']['fingerprint']
    if not FINGERPRINT.fullmatch(expected):
        raise ValueError('Invalid selected signing fingerprint')
    status = run(gpgv, ['--homedir', temporary, '--keyring', keyring, '--status-fd', '1',
                       signature, archive])
    if re.search(r'\[GNUPG:\] (EXPKEYSIG|EXPSIG|REVKEYSIG|KEYREVOKED|BADSIG|ERRSIG)\b', status):
        raise ValueError('Signature/key is expired, revoked or invalid')
    valid = [line.split()[2] for line in status.splitlines()
             if line.startswith('[GNUPG:] VALIDSIG ')]
    if valid != [expected]:
        raise ValueError('Signature does not match the selected signing key')
    return expected


def stage(manifest_path, caches, destination, bsdtar, gpgv, keyring=None):
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema') != 1 or manifest.get('target') != 'arch-hyprland':
        raise ValueError('Unsupported provider manifest')
    providers = manifest.get('providers')
    if not isinstance(providers, list) or not providers:
        raise ValueError('Empty provider selection')
    ids = [p['id'] for p in providers]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z][a-z0-9-]*', i) for i in ids):
        raise ValueError('Invalid/duplicate provider IDs')
    selected = [p for p in providers if p['status'] == 'selected']
    if any(p['status'] not in ('selected', 'pending') for p in providers):
        raise ValueError('Unknown provider status')
    if not selected:
        raise ValueError('No selected artifacts to stage')
    signed = any(p['trust'] == 'arch-signature' for p in selected)
    if signed:
        if keyring is None:
            raise ValueError('An explicit selected keyring is required')
        checked(keyring, manifest['keyring']['binarySha256'])
    if destination.exists() or destination.is_symlink():
        raise ValueError('Stage destination already exists; choose a new destination')
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = []
    # Publish only after every selected artifact verifies. No half-stage appears
    # under the requested name when a signature, metadata or copy fails.
    with tempfile.TemporaryDirectory(prefix='.provider-stage-', dir=destination.parent) as temp:
        temporary = Path(temp)
        payload = temporary / 'payload'
        payload.mkdir()
        gnupg = temporary / 'gnupg'
        gnupg.mkdir(mode=0o700)
        for p in selected:
            if INHERITED.search(p['updateChannel']):
                raise ValueError('Inherited provider update channel')
            filename = relative(p['archive'])
            if '/' in filename:
                raise ValueError('Provider archive must be a basename')
            found = [cache / filename for cache in caches if (cache / filename).is_file()]
            if not found:
                raise ValueError(f'Missing selected provider archive: {filename}')
            archive = checked(found[0], p['sha256'])
            package_dir = payload / p['id']
            package_dir.mkdir()
            # Inspect the staged bytes, not a mutable original after inspection.
            copy = package_dir / filename
            shutil.copyfile(archive, copy)
            checked(copy, p['sha256'])
            record = inspect_archive(p, copy, bsdtar)
            record.update({'id': p['id'], 'archive': f"{p['id']}/{filename}",
                           'sha256': p['sha256'], 'origin': p['origin'],
                           'updateChannel': p['updateChannel'], 'trust': p['trust']})
            if p['trust'] == 'arch-signature':
                sigfile = relative(p['signature']['file'])
                if '/' in sigfile:
                    raise ValueError('Signature must be a basename')
                source = archive.parent / sigfile
                checked(source, p['signature']['sha256'])
                sigcopy = package_dir / sigfile
                shutil.copyfile(source, sigcopy)
                record['signingFingerprint'] = verify_signature(p, copy, sigcopy, keyring, gpgv, gnupg)
                record['signatureSha256'] = p['signature']['sha256']
            elif p['trust'] == 'reviewed-local-build':
                # A matching BUILDINFO recipe binds the recipe identity. It
                # does not establish a clean build or a distributor signature.
                recipe_files = p['recipeFiles']
                if not recipe_files:
                    raise ValueError('Local build needs recorded recipe inputs')
                digests = {}
                for name, digest in recipe_files.items():
                    relative(name)
                    original = checked(manifest_path.parent / name, digest)
                    target = package_dir / 'recipe' / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, target)
                    checked(target, digest)
                    digests[name] = digest
                if p['recipeSha256'] not in digests.values():
                    raise ValueError('Recipe inputs do not include selected build recipe')
                record['recipeFiles'] = digests
                record['limits'] = 'Unsigned local artifact; clean rebuild and installation trust remain pending'
            else:
                raise ValueError('Unsupported artifact trust policy')
            records.append(record)
        report = {'schema': 1, 'target': manifest['target'], 'manifestSha256': sha(manifest_path),
                  'selectedArtifactsVerified': True, 'providers': records,
                  'pendingProviders': [{'id': p['id'], 'reason': p['reason']}
                                       for p in providers if p['status'] == 'pending'],
                  'candidateReady': False,
                  'tools': {'bsdtar': {'path': str(bsdtar), 'sha256': sha(bsdtar)},
                            'gpgv': {'path': str(gpgv), 'sha256': sha(gpgv)}},
                  'limits': 'Partial provider stage only. Dependency closure, build provenance, Lua/static-QML/runtime capabilities, native policies, clean-host and I01-I09 acceptance remain required.'}
        if signed:
            report['keyringSha256'] = sha(keyring)
        (payload / 'manifest.json').write_bytes(manifest_path.read_bytes())
        if sha(payload / 'manifest.json') != report['manifestSha256']:
            raise ValueError('Manifest changed during staging')
        (payload / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        os.rename(payload, destination)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--cache', type=Path, action='append', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--bsdtar', type=Path, required=True)
    parser.add_argument('--gpgv', type=Path, required=True)
    parser.add_argument('--keyring', type=Path)
    args = parser.parse_args()
    try:
        report = stage(args.manifest.resolve(), [p.resolve() for p in args.cache],
                       args.destination.absolute(), args.bsdtar, args.gpgv, args.keyring)
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(2, f'{error}\n')
    print(f"Verified/staged {len(report['providers'])} native artifacts; "
          f"{len(report['pendingProviders'])} provider selections pending; candidateReady=false. "
          f"Report: {args.destination / 'report.json'}")


if __name__ == '__main__':
    main()
