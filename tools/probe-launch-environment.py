#!/usr/bin/env python3
"""Exercise production Util with real Quickshell Process and execDetached children.

Uses isolated offscreen QML and unavailable buses. Does not load the desktop,
change the manager environment, or exercise graphics rendering.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

KEYS = ['__EGL_VENDOR_LIBRARY_FILENAMES', 'LIBGL_DRIVERS_PATH']
MARKER = 'TAMLINUX_GRAPHICS_PROVIDER_ENV'
SAVED = ['TAMLINUX_HOST_' + key for key in KEYS]
SOFTWARE = ['QT_QUICK_BACKEND', 'LIBGL_ALWAYS_SOFTWARE', 'QSG_RHI_BACKEND']


def probe(provider, modules):
    cases = [
        ('absent', {}, {}),
        ('empty', dict.fromkeys(KEYS, ''), dict.fromkeys(KEYS, '')),
        ('caller', dict(zip(KEYS, ['/usr/share/glvnd/egl_vendor.d/50_mesa.json', '/caller/dri with spaces:$x;=yes'])),
         dict(zip(KEYS, ['/usr/share/glvnd/egl_vendor.d/50_mesa.json', '/caller/dri with spaces:$x;=yes']))),
        ('mixed', {KEYS[0]: ''}, {KEYS[0]: ''}),
        ('stale-markers', dict.fromkeys(SAVED, '/stale'), {}),
        ('retained-markers', {MARKER: ' '.join(KEYS), **dict.fromkeys(KEYS, '/injected'),
                              SAVED[0]: '', SAVED[1]: '/original/dri'},
         {KEYS[0]: '', KEYS[1]: '/original/dri'}),
        ('retained-absent', {MARKER: ' '.join(KEYS), **dict.fromkeys(KEYS, '/injected')}, {}),
        ('unwrapped', {KEYS[0]: '/caller/vendor', SAVED[1]: '/stale', MARKER: 'PATH MALICIOUS'},
         {KEYS[0]: '/caller/vendor'}),
    ]
    rows = []
    with tempfile.TemporaryDirectory(prefix='tamlinux-launch-env-') as temporary:
        root = Path(temporary)
        runtime = root / 'runtime'; runtime.mkdir(mode=0o700)
        dump = root / 'child.py'
        dump.write_text('import json,os,sys\nfrom pathlib import Path\n'
                        'Path(sys.argv[1]).write_text(json.dumps(dict(os.environ)))\n')
        for name, supplied, expected in cases:
            work = root / name; work.mkdir()
            env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'TZ') if key in os.environ}
            env.update(QT_STYLE_OVERRIDE='Fusion', QT_QPA_PLATFORMTHEME='')
            env.update(HOME=str(work), XDG_CONFIG_HOME=str(work / 'config'),
                       XDG_CACHE_HOME=str(work / 'cache'), XDG_STATE_HOME=str(work / 'state'),
                       XDG_DATA_HOME=str(work / 'data'), XDG_RUNTIME_DIR=str(runtime),
                       QT_QPA_PLATFORM='offscreen', QML_IMPORT_PATH=str(modules),
                       DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent/tamlinux-session',
                       DBUS_SYSTEM_BUS_ADDRESS='unix:path=/nonexistent/tamlinux-system',
                       TAMLINUX_PROBE_OTHER='unchanged', **supplied)
            # The unwrapped case checks that stale/unknown markers cannot strip PATH
            # or restore old backups, even without the delivery wrapper.
            executable = provider.parent / 'qs' if name == 'unwrapped' else provider
            argv = lambda output: json.dumps(['/usr/bin/python3', str(dump), str(work / output)])
            qml = work / 'shell.qml'
            qml.write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import Tam.Commons
ShellRoot {
  Process {
    id: child
    environment: Util.hostEnvironment({"TAMLINUX_PROBE_EXPLICIT": "retained"})
    command: %s
    running: true
    onExited: function(code) {
      if (code !== 0) Qt.exit(2)
      Quickshell.execDetached(Util.hostArgv(%s))
      finish.start()
    }
  }
  Timer { id: finish; interval: 500; onTriggered: Qt.quit() }
  Timer { interval: 5000; running: true; onTriggered: Qt.exit(3) }
  Component.onCompleted: console.log("TAMLINUX_PROVIDER_ENV " + JSON.stringify({
    vendor: Quickshell.env("__EGL_VENDOR_LIBRARY_FILENAMES"),
    dri: Quickshell.env("LIBGL_DRIVERS_PATH"),
    marker: Quickshell.env("TAMLINUX_GRAPHICS_PROVIDER_ENV")
  }))
}
''' % (argv('process.json'), argv('detached.json')))
            result = subprocess.run([str(executable), '--no-color', '-p', str(qml)], env=env,
                                    capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
            checks = {'exit': result.returncode == 0}
            children = {}
            for kind in ('process', 'detached'):
                path = work / f'{kind}.json'
                data = json.loads(path.read_text()) if path.exists() else {}
                children[kind] = {key: data[key] for key in KEYS + SAVED + [MARKER] if key in data}
                checks[kind] = (children[kind] == expected and data.get('TAMLINUX_PROBE_OTHER') == 'unchanged'
                                and data.get('PATH') == env['PATH'])
                if kind == 'process':
                    checks['explicitOverride'] = data.get('TAMLINUX_PROBE_EXPLICIT') == 'retained'
            if name != 'unwrapped':
                checks['providerOverridesCaller'] = '/share/glvnd/egl_vendor.d/50_mesa.json' in output and '/lib/dri' in output
            row = {'case': name, 'checks': checks, 'children': children,
                   'outputDigest': hashlib.sha256(output.encode()).hexdigest(),
                   'passed': all(checks.values())}
            if not row['passed']: row['output'] = output[-6000:]
            rows.append(row)
    return {'schema': 1, 'provider': str(provider), 'modules': str(modules), 'cases': rows,
            'passed': all(row['passed'] for row in rows),
            'limits': 'Real offscreen child environments; no desktop services or graphical rendering.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', type=Path, required=True)
    parser.add_argument('--modules', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = probe(args.provider.absolute(), args.modules.resolve())
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{sum(row['passed'] for row in report['cases'])}/{len(report['cases'])} launch environment cases passed")
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
