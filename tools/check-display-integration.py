#!/usr/bin/env python3
"""Bind workspace user packages to the reviewed native display provider pair.

Read-only; never starts a compositor or installs an archive. This source/build
check is a prerequisite for candidate selection, not physical acceptance.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('display_provider_inspector', ROOT / 'tools/stage-providers.py')
PROVIDERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROVIDERS)
MARKERS = {
    'hyprland': ('usr/bin/Hyprland', [b'input_output_preserved=', b'monotonic_ns=',
                                    b'compositor-wide', b'inhibit state unchanged']),
    'aquamarine': ('usr/lib/libaquamarine.so.0.15.1', [b'Async commit failed output=',
                                                   b'crtc={} status={} in_flight={} test={}']),
}
PRODUCT_FILES = {
    'plugins': ['desktop/plugins/fred.workspaces/' + name for name in
                ('manifest.json', 'Workspaces.qml', 'ActionQueue.js', 'tam-desktop-mode')],
    'shell': ['desktop/shell/host/' + name for name in
              ('hyprland_backend.py', 'compositor_commands.py')],
}


def source(product, revision, path):
    return subprocess.check_output(['git', '-C', str(product), 'show', revision + ':' + path], timeout=30)


def verify_native(root, archives):
    selection = json.loads((root / 'contracts/providers/selection.json').read_text())
    result = {}
    for name, archive in archives.items():
        provider = next(p for p in selection['providers'] if p['id'] == name)
        PROVIDERS.checked(archive, provider['sha256'])
        if archive.name != provider['archive']:
            raise ValueError('Native archive name differs: ' + name)
        for relative, digest in provider['recipeFiles'].items():
            PROVIDERS.checked(root / 'contracts/providers' / relative, digest)
        PROVIDERS.inspect_archive(provider, archive, Path('/usr/bin/bsdtar'))
        member, markers = MARKERS[name]
        payload = subprocess.check_output(['/usr/bin/bsdtar', '-xOf', str(archive), member], timeout=30)
        if not payload.startswith(b'\x7fELF') or any(marker not in payload for marker in markers):
            raise ValueError('Native display correction/guard payload absent: ' + name)
        result[name] = {key: provider[key] for key in
                        ('version', 'archive', 'sha256', 'recipeSha256', 'sourceRevision')}
    if set(result) != set(MARKERS):
        raise ValueError('Both native display providers are required')
    return result


def verify(root, product, plugins, shell, archives):
    revision = (shell / 'share/tamlinux/source-revision').read_text().strip()
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('User package has no exact product revision')
    files = {}
    for package, paths in PRODUCT_FILES.items():
        for path in paths:
            installed = (plugins / 'share/tamlinux/plugins' / path.removeprefix('desktop/plugins/')) if package == 'plugins' else (shell / 'share/tamlinux' / path.removeprefix('desktop/'))
            expected = source(product, revision, path)
            if installed.is_symlink() or installed.read_bytes() != expected:
                raise ValueError('User package differs from selected source: ' + path)
            files[path] = hashlib.sha256(expected).hexdigest()
    # Native recipe patches must be the corrections reviewed with this source.
    for name, patch in (('hyprland', 'hyprland-output-workspace-logging.patch'),
                        ('aquamarine', 'aquamarine-commit-attribution.patch')):
        expected = source(product, revision, 'desktop/native/providers/display/' + patch)
        if (root / 'contracts/providers/recipes' / name / patch).read_bytes() != expected:
            raise ValueError('Native correction differs from selected product: ' + name)
    return {'schema': 1, 'productRevision': revision, 'userFiles': files,
            'nativeProviders': verify_native(root, archives),
            'physicalAcceptance': 'pending exact-candidate Test', 'installed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('product', 'plugins', 'shell', 'hyprland', 'aquamarine'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(ROOT, args.product, args.plugins, args.shell,
                        {name: getattr(args, name) for name in MARKERS})
    except (OSError, ValueError, StopIteration, subprocess.SubprocessError) as error:
        parser.exit(1, 'display-integration: ' + str(error) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
