"""Probe real package outputs with isolated state and no workstation tools on PATH.

Host IPC is recorded. Both bus addresses are deliberately unavailable, so these
development checks cannot change the live desktop or system timezone.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commands', type=Path, required=True)
    parser.add_argument('--shell', type=Path, required=True)
    args = parser.parse_args()
    checks = []
    with tempfile.TemporaryDirectory(prefix='tamlinux-installed-helpers-') as temporary:
        root = Path(temporary)
        host_bin = root / 'host-bin'
        host_bin.mkdir()
        log = root / 'calls.jsonl'
        network = root / 'network-attempt'
        data = root / 'data/tamlinux'
        data.mkdir(parents=True)
        shell = (args.shell / 'share/tamlinux/shell').resolve(strict=True)
        (data / 'shell').symlink_to(shell, target_is_directory=True)
        recorder = host_bin / 'qs'
        recorder.write_text(f'#!{sys.executable}\n' + '''
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['TEST_CALL_LOG'], 'a') as out:
    out.write(json.dumps(args) + '\\n')
if args[6:8] == ['menu', 'open']:
    payload = json.loads(args[8])
    pathlib.Path(payload['selectionFile']).write_text('UTC')
    pathlib.Path(payload['doneFile']).touch()
else:
    print('pong')
''')
        recorder.chmod(0o755)
        curl = host_bin / 'curl'
        curl.write_text(f'#!{sys.executable}\nimport os, pathlib, sys\n'
                        'pathlib.Path(os.environ["TEST_NETWORK_LOG"]).touch()\n'
                        'sys.exit(99)\n')
        curl.chmod(0o755)
        launch_log = root / 'launches.jsonl'
        launch_recorder = f'#!{sys.executable}\n' + '''
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['TEST_LAUNCH_LOG'], 'a') as out:
    out.write(json.dumps({'name': name, 'args': args, 'cwd': os.getcwd()}) + '\\n')
if name == 'uwsm-app':
    assert args[0] == '--'
    os.execvp(args[1], args[1:])
elif name == 'xdg-terminal-exec':
    if args == ['--print-id']: print('foot.desktop')
    elif os.environ.get('TEST_EXEC_PRESENTATION'):
        i = args.index('-e')
        os.execvp(args[i+1], args[i+1:])
elif name == 'hyprctl':
    if args[:2] == ['clients', '-j']: print(os.environ.get('TEST_CLIENTS', '[]'))
    else: print('{}')
'''
        for name in ('uwsm-app', 'xdg-terminal-exec', 'hyprctl', 'nvim', 'code', 'chromium', 'codex'):
            path = host_bin / name
            path.write_text(launch_recorder)
            path.chmod(0o755)
        env = {'HOME': str(root / 'home'), 'XDG_DATA_HOME': str(root / 'data'),
               'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_STATE_HOME': str(root / 'state'),
               'XDG_CACHE_HOME': str(root / 'cache'), 'XDG_RUNTIME_DIR': str(root / 'runtime'),
               'TMPDIR': str(root), 'WAYLAND_DISPLAY': 'wayland-development-probe',
               'PATH': str(host_bin), 'LANG': 'C', 'TERM': 'xterm',
               'DBUS_SESSION_BUS_ADDRESS': 'unix:path=' + str(root / 'no-session-bus'),
               'DBUS_SYSTEM_BUS_ADDRESS': 'unix:path=' + str(root / 'no-system-bus'),
               'TEST_CALL_LOG': str(log), 'TEST_NETWORK_LOG': str(network),
               'TEST_LAUNCH_LOG': str(launch_log)}

        def run(name, *values, check=True):
            result = subprocess.run([str(args.commands / 'bin' / name), *values],
                                    env=env, cwd=root, text=True, capture_output=True, timeout=10)
            if check and result.returncode:
                raise AssertionError(f'{name} failed: {result.stderr}')
            return result

        payload = json.loads(run('tam-theme-payload').stdout)
        assert payload['palette']
        checks.append('theme helper executes with its packaged Python interpreter')

        assert run('tam-shell', 'menu', 'ping').stdout == 'pong\n'
        ipc = json.loads(log.read_text().splitlines()[-1])
        assert ipc == ['ipc', '-n', '-p', str(shell), 'call', '--', 'menu', 'ping']
        checks.append('IPC resolves the installed shell with packaged runtime tools')

        assert run('tam-menu-select', 'Choose', 'UTC', 'America/New_York').stdout == 'UTC'
        ipc = json.loads(log.read_text().splitlines()[-1])
        selection = json.loads(ipc[8])
        assert selection['options'] == ['UTC', 'America/New_York']
        assert not Path(selection['selectionFile']).exists()
        assert not Path(selection['doneFile']).exists()
        checks.append('menu selection resolves packaged IPC and Perl without host PATH')

        assert run('tam-agent', '--current').stdout == ''
        run('tam-agent', '--pick')
        ipc = json.loads(log.read_text().splitlines()[-1])
        assert ipc[6:] == ['menu', 'summon', 'setup.default.agent']
        checks.append('unset agent resolves the packaged menu without selecting an agent')

        for values in [('list', '--all', '--refresh'), ('info', 'fred.clock'), ('search', 'clock')]:
            result = run('tam-plugin', *values)
            assert 'fred.clock' in result.stdout
            assert 'omarchy' not in result.stdout.lower()
        assert not network.exists()
        checks.append('offline product catalog resolves installed registry and runtime tools')

        result = run('tam-notification-send', 'Probe', '--exec', 'xdg-open', 'file with spaces', check=False)
        assert result.returncode != 0  # The deliberately absent bus is the boundary.
        assert 'bus' in result.stderr.lower(), result.stderr
        assert 'command not found' not in result.stderr.lower(), result.stderr
        assert 'jq:' not in result.stderr.lower(), result.stderr
        checks.append('notification jq/busctl resolve before the deliberately absent bus')

        plugins = root / 'plugins/fred.probe'
        plugins.mkdir(parents=True)
        code = plugins / 'Main.qml'
        code.write_text('fixture')
        cache = root / 'cache/quickshell/qmlcache'
        cache.mkdir(parents=True)
        compiled = cache / (hashlib.sha1(str(code).encode()).hexdigest() + '.qmlc')
        compiled.write_text('compiled fixture')
        unrelated = cache / 'unrelated.qmlc'
        unrelated.write_text('other application')
        run('tam-qmlcache-purge', '-q', str(plugins.parent))
        assert not compiled.exists() and unrelated.exists() and code.exists()
        checks.append('cache purge resolves packaged find/hash tools and preserves unrelated files')

        assert run('tam-cmd-present', 'qs').returncode == 0
        assert run('tam-cmd-present', 'not-a-real-program', check=False).returncode != 0
        checks.append('command presence retains the declared host program boundary')

        assert run('tam-default-agent').stdout == ''
        agent_file = root / 'config/tamlinux/defaults/agent'
        assert not agent_file.exists()
        user_bin = root / 'home/.local/bin'
        user_bin.mkdir(parents=True)
        (user_bin / 'codex').symlink_to(host_bin / 'codex')
        run('tam-default-agent', 'codex')
        assert agent_file.read_text() == 'codex\n'
        assert run('tam-default-agent').stdout == run('tam-agent', '--current').stdout == 'codex\n'
        assert not (root / 'home/.config/tamlinux/defaults/agent').exists()
        checks.append('packaged agent setter/reader share isolated XDG state and resolve atomic file tools')

        prompt = 'literal prompt; $(touch NEVER) with spaces'
        run('tam-agent', '--inline', '--prompt', prompt)
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['name'] == 'codex' and launch['args'] == ['--approve-for-me', '--', prompt]
        assert not (root / 'NEVER').exists()
        checks.append('packaged agent launcher preserves prompt argv at the recorded application boundary')

        for name in ('openclaw', 'hermes'):
            stub = host_bin / name
            stub.write_text('#!/bin/sh\nmise use -g pipx:hermes-agent\n')
            stub.chmod(0o755)
            agent_file.write_text(name + '\n')
            before = launch_log.read_text()
            for flags in ((name,), ('--installed', name), ('--install', name)):
                assert run('tam-default-agent', *flags, check=False).returncode != 0
            assert run('tam-agent', '--inline', '--prompt', prompt, check=False).returncode != 0
            assert launch_log.read_text() == before and agent_file.read_text() == name + '\n'
        checks.append('retired OpenClaw and Hermes selections/stubs cannot install, launch or alter state')

        agent_file.write_text('codex\n')
        result = run('tam-default-agent', '--install', check=False)
        assert result.returncode != 0 and agent_file.read_text() == 'codex\n'
        assert not (root / 'home/.hermes').exists()
        checks.append('invalid agent installation request preserves selection without invoking an installer')

        env['PULSE_SERVER'] = 'unix:' + str(root / 'no-pulse-server')
        env['PIPEWIRE_REMOTE'] = 'tamlinux-development-unavailable'
        result = run('tam-audio-input-set-default', '42', 'development-microphone', check=False)
        assert result.returncode == 0, result.stderr
        assert 'command not found' not in result.stderr.lower(), result.stderr
        checks.append('packaged microphone routing reaches isolated unavailable PipeWire/Pulse boundaries')

        result = run('tam-audio-output-set-default', '42', 'development-speaker', check=False)
        assert result.returncode == 0 and 'command not found' not in result.stderr.lower(), result.stderr
        checks.append('packaged output routing reaches unavailable sound servers with complete client tools')
        result = run('tam-audio-output-sink', 'alsa_output.development')
        assert result.stdout == 'alsa_output.development\n'
        result = run('tam-audio-output-sink', 'idle_development_dsp')
        assert result.stdout == 'idle_development_dsp\n'
        assert 'command not found' not in result.stderr.lower(), result.stderr
        checks.append('output resolver executes real packaged Pulse/awk with physical and idle DSP fallback')
        result = run('tam-audio-sink-availability', check=False)
        assert 'command not found' not in result.stderr.lower(), result.stderr
        checks.append('sink availability resolves packaged tuning and client tool chain without live services')
        result = run('tam-audio-tuning', 'status')
        assert 'Installed:    no' in result.stdout and 'command not found' not in result.stderr.lower()
        audio_data = args.commands / 'share/tamlinux/audio'
        for relative in ('LICENSE', 'speaker-tuning.service', 'filter-chain-host.conf',
                         'tunings/dell-xps-2026/tuning.conf', 'tunings/dell-xps-2026/filter-chain.conf'):
            assert (audio_data / relative).is_file(), relative
        assert 'omarchy' not in (audio_data / 'speaker-tuning.service').read_text().lower()
        assert not (root / 'config/pipewire').exists()
        checks.append('tuning reads immutable packaged assets, owned unit identity and isolated XDG state')
        empty_tunings = root / 'empty-audio/tunings'
        empty_tunings.mkdir(parents=True)
        env['TAMLINUX_AUDIO_DATA'] = str(empty_tunings.parent)
        result = run('tam-audio-tuning', 'on')
        assert 'No speaker tuning matches' in result.stdout
        assert not (root / 'config/pipewire').exists()
        del env['TAMLINUX_AUDIO_DATA']
        checks.append('unmatched tuning activation has no state or service effects')
        run('tam-osd', '-i', 'volume-high', '-m', 'quotes \" and $(literal message)' , '-p', '42')
        payload = json.loads(json.loads(log.read_text().splitlines()[-1])[8])
        assert payload['value'] == '42' and payload['progressText'] == '42%'
        checks.append('OSD reaches recorded shell IPC through packaged jq and sibling launchers')
        result = run('tam-audio-output-volume', 'raise', check=False)
        assert result.returncode != 0 and 'Could not resolve an audio sink' in result.stderr
        assert 'command not found' not in result.stderr.lower(), result.stderr
        checks.append('volume controls fail safely at an unavailable server with complete packaged tools')

        assert run('tam-default-editor').stdout == 'nvim\n'
        assert run('tam-default-terminal').stdout == 'foot\n'
        assert not (root / 'state/tamlinux/defaults/editor').exists()
        checks.append('fresh terminal/editor default readers need no workstation state')

        assert run('tam-cmd-terminal-cwd').stdout == env['HOME'] + '\n'
        run('tam-launch-terminal', 'nvim', 'file with spaces')
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['args'] == ['--dir=' + env['HOME'], 'nvim', 'file with spaces']
        checks.append('terminal launch resolves packaged cwd/setsid with recorded host facilities')

        # The deliberately absent bus makes the toast fail after the preference
        # write. Verify the saved selection and the launcher's independent chain.
        run('tam-default-editor', 'code', check=False)
        assert run('tam-default-editor').stdout == 'code\n'
        run('tam-launch-config-editor', 'config with spaces.lua')
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['name'] == 'code' and launch['args'] == ['config with spaces.lua']
        checks.append('packaged editor setter/config launcher share owned state despite unavailable toast bus')

        run('tam-default-terminal', 'kitty', check=False)
        assert (root / 'config/xdg-terminals.list').read_text().endswith('kitty.desktop\n')
        assert not (root / 'home/.config').exists()
        checks.append('terminal selector writes only the configured XDG destination')

        run('tam-default-editor', 'nvim', check=False)
        run('tam-launch-editor', 'file with spaces')
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['args'] == ['--app-id=org.tamlinux.nvim', '-e', 'nvim', 'file with spaces']
        run('tam-launch-editor', '--inline', 'file with spaces')
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['name'] == 'nvim' and launch['args'] == ['file with spaces']
        checks.append('terminal and inline editor routes resolve packaged sibling helpers')

        env['TEST_EXEC_PRESENTATION'] = '1'
        run('tam-launch-floating-terminal-with-presentation', 'code', 'literal $(touch NEVER)')
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['name'] == 'code' and launch['args'] == ['literal $(touch NEVER)']
        assert not (root / 'NEVER').exists()
        run('tam-show-done')
        checks.append('presentation runs packaged bash/logo/done without reinterpreting argv')

        applications = root / 'data/applications'
        applications.mkdir()
        desktop = applications / 'chromium.desktop'
        desktop.write_text('[Desktop Entry]\nType=Application\nName=Chromium\n'
                           'Exec=chromium --profile-directory="Probe Profile" %U\n')
        (root / 'config/mimeapps.list').write_text(
            '[Default Applications]\nx-scheme-handler/http=chromium.desktop\n'
            'x-scheme-handler/https=chromium.desktop\ntext/html=chromium.desktop\n')
        env['XDG_DATA_DIRS'] = str(root / 'empty-providers')
        env['XDG_CURRENT_DESKTOP'] = 'generic'
        env['BROWSER'] = 'ignore-this-session-override'
        argv = json.loads(run('tam-browser-command', 'chromium.desktop').stdout)
        assert argv == ['chromium', '--profile-directory=Probe Profile']
        checks.append('browser resolver reads XDG desktop provider and preserves static argv')

        assert run('tam-default-browser').stdout == 'chromium\n'
        checks.append('browser default reader uses packaged XDG tools and isolated MIME handlers')

        literal = 'https://example.invalid/?q=$(touch NEVER)&x=a b'
        run('tam-launch-webapp', literal, '--name=App With Spaces')
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['name'] == 'chromium'
        assert launch['args'] == ['--profile-directory=Probe Profile', '--app=' + literal,
                                  '--name=App With Spaces']
        assert not (root / 'NEVER').exists()
        checks.append('webapp launch resolves packaged XDG/resolver/jq/setsid and retains literal URL argv')

        env['TEST_CLIENTS'] = json.dumps([{'class': 'Example', 'title': 'Example',
                                         'address': '0x123', 'initialClass': 'Example'}])
        run('tam-launch-or-focus-webapp', 'Example', literal)
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['name'] == 'hyprctl' and launch['args'][0] == 'dispatch'
        run('tam-hyprland-focus-app', 'Example')
        checks.append('focus wrappers resolve same-output helpers and record the host Hyprland boundary')

        result = run('tam-launch-browser', '--private', check=False)
        assert result.returncode != 0 and 'bus' in result.stderr.lower(), result.stderr
        assert 'command not found' not in result.stderr.lower(), result.stderr
        checks.append('browser launch resolves packaged tools before the deliberately unavailable user bus')

    print(json.dumps({'checks': checks, 'passed': len(checks),
                      'limits': 'Recorded host IPC and unavailable buses; no live desktop or clean-host installation proof.'}, indent=2))


if __name__ == '__main__':
    main()
