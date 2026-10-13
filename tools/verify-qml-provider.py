#!/usr/bin/env python3
"""Load selected Quickshell module imports offscreen with isolated empty state.

This executes the explicit provider, never the desktop's QML. It proves import
registration, not graphical workflows, capabilities or physical acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def collect(provider, qml_root):
    provider = provider.resolve(strict=True)
    qml_root = qml_root.resolve(strict=True)
    records = []
    for definition in sorted((qml_root / 'Quickshell').rglob('qmldir')):
        match = re.search(r'^module ([A-Za-z][A-Za-z0-9_.]*)$', definition.read_text(), re.M)
        if not match:
            raise ValueError(f'Missing/invalid module definition: {definition}')
        name = match.group(1)
        records.append({'name': name, 'qmldir': str(definition), 'qmldirDigest': sha(definition)})
    if not records:
        raise ValueError('No Quickshell module definitions found')
    with tempfile.TemporaryDirectory(prefix='tamlinux-qml-provider-') as directory:
        root = Path(directory)
        runtime = root / 'runtime'
        runtime.mkdir(mode=0o700)
        env = {'HOME': str(root), 'PATH': '/nonexistent', 'QT_QPA_PLATFORM': 'offscreen',
               'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_CACHE_HOME': str(root / 'cache'),
               'XDG_STATE_HOME': str(root / 'state'), 'XDG_DATA_HOME': str(root / 'data'),
               'XDG_RUNTIME_DIR': str(runtime), 'QML_IMPORT_PATH': str(qml_root),
               'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/nonexistent/tamlinux-session',
               'DBUS_SYSTEM_BUS_ADDRESS': 'unix:path=/nonexistent/tamlinux-system',
               'QT_QUICK_BACKEND': 'software', 'LC_ALL': 'C'}
        for index, record in enumerate(records):
            source = ('import QtQuick\nimport Quickshell\n'
                      f"import {record['name']} as Probe\n"
                      'ShellRoot { Timer { interval: 1; running: true; repeat: false; '
                      'onTriggered: { console.log("TAMLINUX_MODULE_OK"); Qt.quit(); } } }\n')
            case = root / f'module-{index}.qml'
            case.write_text(source)
            try:
                result = subprocess.run([str(provider), '--no-color', '-p', str(case)], env=env,
                                        capture_output=True, text=True, timeout=10)
                output = result.stdout + result.stderr
                status = result.returncode
            except subprocess.TimeoutExpired as error:
                output = ((error.stdout or b'') + (error.stderr or b'')).decode(errors='replace')
                status = 'deadline'
            record.update({'configDigest': sha(case), 'exit': status,
                           'passed': status == 0 and 'TAMLINUX_MODULE_OK' in output,
                           'outputDigest': hashlib.sha256(output.encode()).hexdigest()})
            if not record['passed']:
                record['error'] = output[-2000:]
                # One unresolved base module makes every subsequent fixture
                # invalid. Keep the first concrete error and finish promptly.
                break
    for record in records:
        if 'passed' not in record:
            record.update({'passed': False, 'exit': 'not-run',
                           'error': 'Earlier module import failed'})
    return {'schema': 1, 'runner': {'name': 'tamlinux-qml-provider', 'sourceDigest': sha(Path(__file__))},
            'provider': {'path': str(provider), 'sha256': sha(provider)}, 'qmlRoot': str(qml_root),
            'imports': records, 'passed': all(r['passed'] for r in records),
            'limits': 'Offscreen import registration with isolated state and unavailable buses. No desktop QML, service actions, fresh graphical login, rendering or physical acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', type=Path, required=True)
    parser.add_argument('--qml-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        if not args.provider.is_absolute() or not os.access(args.provider, os.X_OK):
            raise ValueError('Provider must be an explicit absolute executable')
        report = collect(args.provider, args.qml_root)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(2, str(error) + '\n')
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f"{sum(r['passed'] for r in report['imports'])}/{len(report['imports'])} module imports passed; {args.report}")
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
