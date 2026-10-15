#!/usr/bin/env python3
"""Observe the running desktop without changing units, settings or applications.

The report distinguishes mapped files from configured resources and Fontconfig
resolution. It remains partial evidence until bound to a complete gate tuple.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ENV_KEYS = {
    'HOME', 'PATH', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME',
    'XDG_RUNTIME_DIR', 'WAYLAND_DISPLAY', 'DISPLAY', 'XDG_CURRENT_DESKTOP',
    'XDG_SESSION_TYPE', 'HYPRLAND_INSTANCE_SIGNATURE', 'QML_IMPORT_PATH',
    'QML2_IMPORT_PATH', 'QT_QUICK_BACKEND', 'QT_QPA_PLATFORM', 'QSG_RHI_BACKEND', 'QSG_INFO',
    '__EGL_VENDOR_LIBRARY_FILENAMES', 'LIBGL_DRIVERS_PATH', 'TAMLINUX_GRAPHICS_PROVIDER_ENV',
    'TAMLINUX_QUICKSHELL', 'TAMLINUX_QUICKSHELL_IPC', 'TAMLINUX_SHELL_DIR',
    'TAMLINUX_PLUGINS_DIR', 'TAMLINUX_BAR_LAYOUT', 'TAMLINUX_STAY_AWAKE_FILE',
    'TAMLINUX_MENU_EXTENSION', 'TAMLINUX_MENU_DEFAULT', 'TAMLINUX_BIN',
    'EDITOR', 'TERMINAL', 'BROWSER', 'LIBGL_ALWAYS_SOFTWARE', 'GSK_RENDERER'
}
UNITS = ['tamlinux-shell.service',
         'tam-crash-watch.service', 'tamlinux-monitor-watch.service',
         'xdg-desktop-portal.service', 'xdg-desktop-portal-hyprland.service',
         'xdg-desktop-portal-gtk.service']
PROPERTIES = ['LoadState', 'ActiveState', 'SubState', 'MainPID', 'FragmentPath',
              'ExecStart', 'EnvironmentFiles', 'ControlGroup']
BUS_NAMES = ['org.freedesktop.Notifications', 'org.freedesktop.portal.Desktop',
             'org.freedesktop.impl.portal.desktop.hyprland',
             'org.freedesktop.impl.portal.desktop.gtk', 'org.freedesktop.secrets']
INHERITED = re.compile('omarchy', re.I)


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def command(args, env=None):
    result = subprocess.run(args, capture_output=True, text=True, timeout=20, env=env)
    return {'argv': args, 'exit': result.returncode, 'stdout': result.stdout,
            'stderr': result.stderr[:2000]}


def properties(text):
    result = {}
    for line in text.splitlines():
        key, separator, value = line.partition('=')
        if separator and key in PROPERTIES:
            result[key] = value
    return result


def wm_units(text):
    """Keep actual instance names, including systemd's escaped desktop IDs."""
    return sorted({line.split()[0] for line in text.splitlines()
                   if line.split() and re.fullmatch(r'wayland-wm@[A-Za-z0-9_.:@\\-]+\.service',
                                                    line.split()[0])})


def bus_owner(name):
    # GetNameOwner does not activate an absent endpoint. Resolve its unique
    # name before asking for the PID, so a replacement cannot be substituted.
    owner = command(['busctl', '--user', 'call', 'org.freedesktop.DBus',
                     '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'GetNameOwner', 's', name])
    row = {'exit': owner['exit'], 'name': name}
    match = re.fullmatch(r's "(:[0-9]+\.[0-9]+)"\s*', owner['stdout'])
    if not match:
        return row
    unique = match[1]
    pid_result = command(['busctl', '--user', 'call', 'org.freedesktop.DBus',
                          '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                          'GetConnectionUnixProcessID', 's', unique])
    pid_match = re.fullmatch(r'u ([0-9]+)\s*', pid_result['stdout'])
    row.update(uniqueName=unique, pidExit=pid_result['exit'])
    if pid_result['exit'] == 0 and pid_match:
        pid = int(pid_match[1])
        row.update(pid=pid, executable=file_identity(Path('/proc')/str(pid)/'exe'))
    return row


def environment(data):
    result = {}
    inherited = []
    for field in data.split(b'\0'):
        key, separator, value = field.partition(b'=')
        if not separator:
            continue
        name = key.decode('utf-8', errors='replace')
        # Never emit credentials or arbitrary application environment values.
        if name.startswith('OMARCHY_'):
            inherited.append(name)
        if name in ENV_KEYS:
            result[name] = value.decode('utf-8', errors='replace')
    return result, sorted(inherited)


def mapped_paths(text):
    result = set()
    for line in text.splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith('/'):
            result.add(fields[5])
    return sorted(result)


def file_identity(path):
    row = {'path': str(path), 'present': path.exists(), 'symlink': path.is_symlink()}
    if path.is_symlink():
        row['link'] = os.readlink(path)
    if path.exists():
        row['resolved'] = str(path.resolve())
        if path.is_file():
            row['sha256'] = sha(path)
    return row


def process(pid, proc=Path('/proc')):
    base = proc / str(pid)
    info = base.stat()
    if info.st_uid != os.getuid():
        raise ValueError('Selected desktop process belongs to a different user')
    env, inherited = environment((base/'environ').read_bytes())
    maps = mapped_paths((base/'maps').read_text())
    files = []
    for name in maps:
        deleted = name.endswith(' (deleted)')
        row = {'path': name, 'deleted': deleted}
        if not deleted:
            row.update(file_identity(Path(name)))
        files.append(row)
    # Recheck process start identity to reject PID reuse during collection.
    executable = file_identity(base/'exe')
    return {'pid': pid, 'uid': info.st_uid, 'executable': executable,
            'environment': env, 'inheritedVariableNames': inherited,
            'mappedFiles': files}


def resolve_commands(names, path, selected):
    result = []
    for name in names:
        actual = shutil.which(name, path=path)
        expected = selected/'bin'/name
        result.append({'name': name, 'path': actual,
                       'resolved': str(Path(actual).resolve()) if actual else None,
                       'expected': str(expected.resolve()),
                       'matchesSelected': bool(actual and Path(actual).resolve() == expected.resolve())})
    return result


def module_root_matches(value, expected):
    return any(Path(entry).is_absolute() and Path(entry).resolve() == expected.resolve()
               for entry in value.split(':') if entry)



def graphics_evidence(pid, env, log, layers, outputs, mode, renderer_tokens=(), require_notifications=False):
    """Use this shell PID's startup context and visible surfaces, never registration."""
    renderers = re.findall(r"OpenGL VENDOR:.*?RENDERER:\s*(.*?)\s+VERSION:", log)
    overrides = {key: env[key] for key in
                 ('QT_QUICK_BACKEND', 'LIBGL_ALWAYS_SOFTWARE', 'QSG_RHI_BACKEND') if key in env}
    software = any(re.search(r'llvmpipe|softpipe|swrast|swiftshader|software rasterizer', value, re.I)
                   for value in renderers)
    errors = bool(re.search(r'EGL not available|Failed to initialize graphics backend|Failed to create.*OpenGL', log, re.I))
    surfaces = {}
    for output in outputs:
        records = [row for level in layers.get(output, {}).get('levels', {}).values() for row in level
                   if row.get('pid') == pid and row.get('w', 0) > 0 and row.get('h', 0) > 0]
        names = [row.get('namespace', '') for row in records]
        surfaces[output] = {'bar': any(name.startswith('tamlinux-bar-') for name in names),
                            'background': 'tamlinux-background' in names,
                            'notifications': 'tamlinux-notifications' in names}
    checks = {'noSoftwareOverrides': not overrides, 'openGLContextObserved': bool(renderers),
              'noContextErrors': not errors,
              'rendererMatches': bool(renderers) and all(token.lower() in ' '.join(renderers).lower() for token in renderer_tokens),
              'hardwareRenderer': bool(renderers) and not software if mode == 'hardware' else True,
              'allOutputSurfaces': bool(outputs) and all(value['bar'] and value['background']
                  and (value['notifications'] or not require_notifications) for value in surfaces.values())}
    return {'mode': mode, 'shellPid': pid, 'renderers': renderers, 'softwareRendererObserved': software,
            'softwareOverrides': overrides, 'contextLogDigest': hashlib.sha256(log.encode()).hexdigest(),
            'requiredRendererTokens': list(renderer_tokens), 'notificationsRequired': require_notifications,
            'outputs': surfaces, 'checks': checks, 'passed': all(checks.values()),
            'limits': 'VM rendering is not hardware proof. Notification surfaces require a live popup; this collector sends none.'}

def collect(generation, commands, shell, plugins, graphics_mode="hardware", renderer_tokens=(), require_notifications=False):
    discovery = command(['systemctl', '--user', 'list-units', '--all', '--plain',
                         '--no-legend', '--no-pager', 'wayland-wm@*.service'])
    discovered = wm_units(discovery['stdout']) if discovery['exit'] == 0 else []
    unit_records = {}
    for unit in UNITS + discovered:
        observation = command(['systemctl', '--user', 'show', unit,
                               '--property='+','.join(PROPERTIES)])
        unit_records[unit] = {'exit': observation['exit'], 'properties': properties(observation['stdout']),
                              'stderr': observation['stderr']}
    pid = int(unit_records['tamlinux-shell.service']['properties'].get('MainPID', '0'))
    if pid <= 0:
        raise ValueError('No running Tamlinux shell; log into the selected account first')
    before = Path('/proc')/str(pid)/'stat'
    identity = before.read_text().rsplit(')', 1)[1].split()[19]
    runtime = process(pid)
    env = runtime['environment']
    home = Path(env.get('HOME', ''))
    if not home.is_absolute():
        raise ValueError('Running shell has no absolute HOME')
    config = Path(env.get('XDG_CONFIG_HOME') or home/'.config')
    state = Path(env.get('XDG_STATE_HOME') or home/'.local/state')
    current = home/'.local/state/home-manager/gcroots/current-home'
    path = env.get('PATH', '')
    names = sorted(p.name for p in (commands/'bin').iterdir()
                   if not p.name.startswith('.') and os.access(p, os.X_OK))
    resolution = resolve_commands(names, path, commands)
    plugin_records = []
    for expected in sorted((plugins/'share/tamlinux/plugins').glob('fred.*/manifest.json')):
        actual = config/'tamlinux/plugins'/expected.parent.name/'manifest.json'
        row = file_identity(actual)
        row['id'] = expected.parent.name
        row['matchesSelected'] = actual.is_file() and sha(actual) == sha(expected)
        plugin_records.append(row)
    resources = [config/'tamlinux/session/hyprland.lua', config/'uwsm/env.d/10-tamlinux.sh',
                 config/'tamlinux/hypr/monitors.lua', config/'tamlinux/shell/layout.json',
                 config/'tamlinux/shell/settings.json', state/'tamlinux/current/theme',
                 state/'tamlinux/current/theme.name', state/'tamlinux/current/background',
                 config/'fontconfig/conf.d/99-tamlinux-monospace.conf',
                 config/'xdg-desktop-portal/hyprland-portals.conf']
    fonts = []
    for family in ('Tamlinux Icons', 'JetBrainsMono Nerd Font', 'monospace'):
        observation = command(['fc-match', '--format=%{family}\n%{file}\n', family])
        lines = observation['stdout'].splitlines()
        fonts.append({'requested': family, 'exit': observation['exit'],
                      'family': lines[0] if lines else None,
                      'file': file_identity(Path(lines[1])) if len(lines) > 1 else None})
    findings = []
    active_wm = [name for name in discovered
                 if unit_records[name]['properties'].get('ActiveState') == 'active'
                 and int(unit_records[name]['properties'].get('MainPID', '0')) > 0]
    compositor = process(int(unit_records[active_wm[0]]['properties']['MainPID'])) if len(active_wm) == 1 else None
    if discovery['exit'] != 0 or len(active_wm) != 1:
        findings.append('Exactly one running UWSM compositor instance was not established')
    elif compositor['inheritedVariableNames']:
        findings.append('Running compositor retains inherited environment variables')
    if compositor and any(INHERITED.search(str(row.get('resolved', row['path'])))
                          for row in compositor['mappedFiles']):
        findings.append('Running compositor maps inherited paths')
    if not current.exists() or current.resolve() != generation.resolve():
        findings.append('Active Home Manager generation differs from the selection')
    if runtime['inheritedVariableNames']:
        findings.append('Running shell retains inherited environment variables')
    if any(INHERITED.search(str(row.get('resolved', row['path']))) for row in runtime['mappedFiles']):
        findings.append('Running shell maps inherited paths')
    if any(not row['matchesSelected'] for row in resolution):
        findings.append('Command resolution differs from selected output')
    if len(plugin_records) != 8 or any(not row['matchesSelected'] for row in plugin_records):
        findings.append('Selected eight-plugin payload does not match installed manifests')
    if not module_root_matches(env.get('QML_IMPORT_PATH', ''), shell/'share/tamlinux/shell/modules'):
        findings.append('Owned QML module root absent from running shell environment')
    awake = env.get('TAMLINUX_STAY_AWAKE_FILE')
    if awake != str(state/'tamlinux/stay-awake'):
        findings.append('Stay Awake reader differs from canonical XDG state')
    selected_qs = env.get('TAMLINUX_QUICKSHELL')
    actual_qs = Path('/proc').joinpath(str(pid), 'exe').resolve()
    expected_qs = Path(selected_qs).resolve() if selected_qs else None
    wrapped_qs = expected_qs.with_name('.quickshell-wrapped').resolve() if expected_qs else None
    if actual_qs not in (expected_qs, wrapped_qs):
        findings.append('Running Quickshell differs from selected executable')
    log = command(['journalctl', '--user', '-b', '-u', 'tamlinux-shell.service', '_PID='+str(pid),
                   '--no-pager', '-o', 'cat'])
    layer_observation = command(['hyprctl', 'layers', '-j'], env=env)
    monitor_observation = command(['hyprctl', 'monitors', '-j'], env=env)
    try:
        layers = json.loads(layer_observation['stdout']) if layer_observation['exit'] == 0 else {}
        monitors = json.loads(monitor_observation['stdout']) if monitor_observation['exit'] == 0 else []
        outputs = [row['name'] for row in monitors if not row.get('disabled', False)]
    except (ValueError, KeyError, TypeError):
        layers, outputs = {}, []
    graphics = graphics_evidence(pid, env, log['stdout'] if log['exit'] == 0 else '', layers,
                                 outputs, graphics_mode, renderer_tokens, require_notifications)
    if not graphics['passed']:
        findings.append('Shell graphics evidence failed: '+', '.join(key for key, passed in graphics['checks'].items() if not passed))
    if before.read_text().rsplit(')', 1)[1].split()[19] != identity:
        raise ValueError('Desktop PID was replaced during collection')
    return {'schema': 1, 'stage': 'Develop; partial runtime observations', 'candidateReady': False,
            'collectorSha256': sha(Path(__file__).resolve()),
            'selection': {k: str(v) for k, v in [('generation', generation), ('commands', commands),
                                               ('shell', shell), ('plugins', plugins)]},
            'generation': file_identity(current), 'shellProcess': runtime, 'units': unit_records,
            'wmUnitDiscovery': {'exit': discovery['exit'], 'instances': discovered, 'active': active_wm},
            'compositorProcess': compositor, 'sessionBusOwners': [bus_owner(name) for name in BUS_NAMES],
            'commands': resolution, 'plugins': plugin_records,
            'configuredResources': [file_identity(p) for p in resources],
            'fontconfigResolution': fonts, 'graphics': graphics, 'findings': findings,
            'limits': 'Mapped files establish actual process mappings; configured resources and fc-match are separate observations, not proof that all QML/assets/fonts loaded or workflows passed. Bind to a complete source/native/consumer/recovery/capability tuple.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('generation', 'commands', 'shell', 'plugins', 'report'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--graphics-mode', choices=('hardware', 'vm'), default='hardware')
    parser.add_argument('--renderer-token', action='append', default=[], help='Required renderer substring (repeatable)')
    parser.add_argument('--require-notifications', action='store_true', help='Require visible notification surfaces on every output')
    args = parser.parse_args()
    for name in ('generation', 'commands', 'shell', 'plugins'):
        path = getattr(args, name)
        if not path.is_absolute() or not path.is_dir():
            parser.error('Selected output must be an existing absolute directory: '+name)
    report = collect(args.generation, args.commands, args.shell, args.plugins, args.graphics_mode, args.renderer_token, args.require_notifications)
    with args.report.open('x') as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'commands': len(report['commands']), 'plugins': len(report['plugins']),
                      'mappedFiles': len(report['shellProcess']['mappedFiles']),
                      'findings': report['findings'], 'candidateReady': False}))
    if not report['graphics']['passed']:
        parser.exit(1, 'Shell graphics acceptance failed; see the retained report.\n')


if __name__ == '__main__':
    import sys
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit('collect-session-runtime: '+str(error))
