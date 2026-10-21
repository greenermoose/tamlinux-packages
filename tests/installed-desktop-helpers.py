"""Probe real package outputs with isolated state and no workstation tools on PATH.

Host IPC is recorded. Both bus addresses are deliberately unavailable, so these
development checks cannot change the live desktop or system timezone.
"""

import argparse
import base64
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
    parser.add_argument('--capture-fixtures', type=Path,
                        default=Path(__file__).resolve().parent / 'fixtures/capture')
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
    if args[:2] == ['-t', 'service']: args = args[2:]
    assert args[0] == '--'
    os.execvp(args[1], args[1:])
elif name == 'xdg-terminal-exec':
    if args == ['--print-id']: print('foot.desktop')
    elif os.environ.get('TEST_EXEC_PRESENTATION'):
        i = args.index('-e')
        os.execvp(args[i+1], args[i+1:])
elif name == 'hyprctl':
    if args[:2] == ['clients', '-j']: print(os.environ.get('TEST_CLIENTS', '[]'))
    elif args[0] == 'monitors': print(os.environ.get('TEST_MONITORS', '[]'))
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
               'TAMLINUX_QUICKSHELL_IPC': str(recorder),
               'TEST_CALL_LOG': str(log), 'TEST_NETWORK_LOG': str(network),
               'TEST_LAUNCH_LOG': str(launch_log)}

        def run(name, *values, check=True, extra_env=None):
            result = subprocess.run([str(args.commands / 'bin' / name), *values],
                                    env=env | (extra_env or {}), cwd=root, text=True, capture_output=True, timeout=10)
            if check and result.returncode:
                raise AssertionError(f'{name} failed: {result.stderr}')
            return result

        payload = json.loads(run('tam-theme-payload').stdout)
        assert payload['palette']
        checks.append('theme helper executes with its packaged Python interpreter')

        if (args.commands / 'share/tamlinux/assets').is_dir():
            current = root / 'state/tamlinux/current'
            assets = args.commands / 'share/tamlinux/assets'
            if (args.commands / 'bin/tam-theme-init').is_file():
                run('tam-theme-init')
                initialized = (current / 'theme').resolve()
                run('tam-theme-init')
                assert (current / 'theme').resolve() == initialized
                checks.append('fresh owned theme state initializes without application or root adapters and preserves its selection')
            run('tam-theme-set', 'Tokyo Night', extra_env={'TAMLINUX_THEME_OFFLINE': '1'})
            assert (current / 'theme').is_symlink()
            assert (current / 'theme.name').read_text() == 'tokyo-night\n'
            assert (current / 'theme/colors.toml').read_bytes() == (assets / 'themes/tokyo-night/colors.toml').read_bytes()
            assert '{{' not in (current / 'theme/shell.toml').read_text()
            checks.append('empty-state theme generation uses immutable templates and owned readers')
            selected = (current / 'theme').resolve()
            assert run('tam-theme-set', '../bad', check=False).returncode
            assert (current / 'theme').resolve() == selected
            run('tam-theme-set', 'nord', extra_env={'TAMLINUX_THEME_OFFLINE': '1'})
            run('tam-theme-set', 'tokyo-night', extra_env={'TAMLINUX_THEME_OFFLINE': '1'})
            assert run('tam-theme-current').stdout == 'Tokyo Night\n'
            checks.append('packaged switching returns to baseline and invalid names preserve selection')
            image = root / 'image with spaces.png'
            image.write_bytes(b'probe image')
            run('tam-theme-bg-set', str(image))
            run('tam-theme-refresh', extra_env={'TAMLINUX_THEME_OFFLINE': '1'})
            assert (current / 'background').resolve() == image
            assert run('tam-theme-bg-set', str(root / 'missing.png'), check=False).returncode
            assert (current / 'background').resolve() == image
            checks.append('packaged background writer and refresh share the effective owned link')
            fontconfig = root / 'fonts.conf'
            fontconfig.write_text('<fontconfig><dir>' + str(args.commands / 'share/fonts') +
                                  '</dir><cachedir>' + str(root / 'font-cache') + '</cachedir></fontconfig>')
            fontenv = {'FONTCONFIG_FILE': str(fontconfig)}
            fonts = run('tam-font-list', extra_env=fontenv).stdout
            assert 'JetBrainsMono Nerd Font' in fonts
            assert 'omarchy' not in fonts.lower()
            assert (args.commands / 'share/fonts/truetype/TamlinuxIcons.ttf').is_file()
            assert not (assets / 'fonts/source.ttf').exists()
            run('tam-font-set', 'JetBrainsMono Nerd Font', extra_env=fontenv)
            assert 'JetBrainsMono Nerd Font' in (root / 'config/fontconfig/conf.d/99-tamlinux-monospace.conf').read_text()
            checks.append('actual packaged monospace baseline and owned icon font resolve in isolated Fontconfig')
            run('tam-branding-about', 'reset')
            run('tam-branding-screensaver', 'reset')
            assert (root / 'config/tamlinux/branding/about.txt').read_text() == 'TAMLINUX\n'
            assert (root / 'config/tamlinux/branding/screensaver.txt').read_text() == 'TAMLINUX\n'
            checks.append('packaged About and screensaver restore owned default identity')
            assert run('tam-transcode-ascii', str(image), str(root / 'art.txt'), '--width', 'invalid', check=False).returncode
            assert not (root / 'art.txt').exists()
            checks.append('packaged image conversion rejects malformed numeric options before publication')
            logo = root / 'logo.svg'
            logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="white"/><rect x="4" y="4" width="8" height="8" fill="black"/></svg>')
            run('tam-transcode-ascii', str(logo), str(root / 'art.txt'), '--width', '8', '--height', '4')
            assert (root / 'art.txt').read_text().strip()
            assert any(0x2800 <= ord(c) <= 0x28ff for c in (root / 'art.txt').read_text())
            checks.append('actual packaged ImageMagick and UTF-8 gawk perform offline SVG to braille conversion')


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

        # The retired built-in mail integration must not be delivered.
        assert not (args.commands / 'bin/tam-webapp-handler-hey').exists()
        checks.append('retired HEY protocol handler is absent from command output')
        if (args.commands / 'bin/tam-webapp-handler-zoom').is_file():
            for scheme in ('zoommtg', 'zoomus'):
                run('tam-webapp-handler-zoom', scheme + '://zoom.us/join?confno=123456&pwd=literal%2Bpass')
                launch = json.loads(launch_log.read_text().splitlines()[-1])
                assert launch['name'] == 'chromium'
                assert launch['args'] == ['--profile-directory=Probe Profile',
                    '--app=https://app.zoom.us/wc/join/123456?pwd=literal%2Bpass']
            checks.append('both Zoom protocols resolve packaged sed and owned webapp/browser chain')

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

        run('tam-toggle-idle', 'stay-awake')
        stay_awake = root / 'state/tamlinux/stay-awake'
        assert stay_awake.exists()
        assert json.loads(run('tam-toggle-idle', 'status').stdout)['enabled'] is True
        run('tam-toggle-idle', 'allow-idle')
        assert not stay_awake.exists()
        checks.append('idle writer uses the paired shell XDG path and preserves prior states')

        name = 'Fixture City; literal "name"'
        run('tam-weather-location', '--set', name, '34.1,-118.5')
        location = root / 'state/tamlinux/settings/weather.json'
        assert json.loads(location.read_text()) == {'name': name, 'latitude': 34.1, 'longitude': -118.5}
        assert run('tam-weather-location').stdout == name + '\n'
        run('tam-weather-location', '--clear')
        assert not location.exists()
        assert len(list((root / 'state/tamlinux/settings-recovery').glob('weather.*/manifest.json'))) == 2
        checks.append('weather/tides shared location round-trips literal data without network and retains originals')

        assert run('tam-weather-location', '--set', 'Fixture', '91,0', check=False).returncode != 0
        checks.append('packaged location rejects invalid coordinates before writing')

        blocked_state = root / 'blocked-state/tamlinux/settings-recovery'
        blocked_state.parent.mkdir(parents=True)
        blocked_state.write_text('blocked')
        result = run('tam-toggle-idle', 'stay-awake', check=False,
                     extra_env={'XDG_STATE_HOME': str(root / 'blocked-state')})
        assert result.returncode != 0
        assert not (blocked_state.parent / 'stay-awake').exists()
        checks.append('packaged snapshot failure stops settings writes')

        fixtures = root / 'dns-fixtures'
        fixtures.mkdir()
        (fixtures / 'resolved.conf').write_text('[Resolve]\nDNS=8.8.8.8#dns.google\n')
        assert run('tam-dns', extra_env={'TAMLINUX_NM_DNS_CONF': str(fixtures / 'absent'),
                                        'TAMLINUX_RESOLVED_CONF': str(fixtures / 'resolved.conf')}).stdout == 'Google\n'
        assert run('tam-dns', 'invalid', check=False).returncode != 0
        checks.append('DNS read uses declared tools and invalid mutation stops before authorization')

        for name, arguments in [('tam-network-band', ('invalid',)),
                                ('tam-network-speedtest', ('invalid',)),
                                ('tam-bluetooth-device', ('pair', 'invalid'))]:
            assert run(name, *arguments, check=False).returncode != 0
        checks.append('radio/speedtest controls reject invalid requests without effectful calls')

        for name, arguments in [('tam-network-band', ()), ('tam-network-password', ('wlan-fixture',)),
                                ('tam-network-qr', ('wlan-fixture',)), ('tam-powerprofiles-list', ()),
                                ('tam-powerprofiles-set', ('battery', 'balanced'))]:
            result = run(name, *arguments, check=False)
            assert result.returncode != 0, (name, result.stdout, result.stderr)
            assert 'command not found' not in result.stderr.lower(), (name, result.stderr)
        assert not (root / 'state/tamlinux/powerprofiles/battery').exists()
        checks.append('network/power clients reach unavailable native services with complete runtime tools')

        run('tam-battery-status', '--shell')
        assert 'memory\t' in run('tam-system-stats', '--bar-widget').stdout
        assert 'command not found' not in run('tam-system-stats').stderr.lower()
        checks.append('battery/system telemetry runs without caller tools or a real battery service')

        result = run('tam-display-text-size')
        assert 'gtk text-scaling-factor: 1.0' in result.stdout, result.stdout
        result = run('tam-display-text-size', '16', check=False)
        assert result.returncode != 0, result.stderr
        assert 'command not found' not in result.stderr.lower(), result.stderr
        assert not (root / 'state/tamlinux/shell.toml').exists()
        checks.append('GTK schema/backend are delivered and failed service commit stops paired file changes')

        assert run('tam-display-text-size', '99', check=False).returncode != 0
        checks.append('text size validates the retained range before state mutation')

        assert json.loads(run('tam-toggle-nightlight', '--status').stdout)['enabled'] is False
        checks.append('night-light status uses the declared host IPC boundary without launching a daemon')

        # Device writers never see real hardware: only selectors/invalid requests
        # run with packaged clients. Host DPMS/sleep/lock boundaries are recorded.
        (root / 'runtime').mkdir(exist_ok=True)
        backlight = root / 'backlight'
        backlight.mkdir()
        (backlight / 'appletb_backlight').mkdir()
        (backlight / 'intel_backlight').mkdir()
        assert run('tam-hw-display', extra_env={'TAMLINUX_BACKLIGHT_PATH': str(backlight)}).stdout == 'intel_backlight\n'
        checks.append('packaged backlight selector uses supplied fixture and excludes Touch Bar')

        monitors = [{'name': 'eDP-1', 'focused': True, 'disabled': False, 'dpmsStatus': True,
                     'make': 'Fixture', 'model': 'LCD', 'scale': 2}]
        monitor_env = {'TEST_MONITORS': json.dumps(monitors)}
        assert run('tam-hyprland-monitor-focused', extra_env=monitor_env).stdout == 'eDP-1\n'
        assert run('tam-hyprland-monitor-laptop', extra_env=monitor_env).stdout == 'eDP-1\n'
        assert run('tam-hyprland-monitor-focused-apple', extra_env=monitor_env, check=False).returncode != 0
        assert run('tam-hyprland-monitor-external-active', extra_env=monitor_env, check=False).returncode != 0
        checks.append('packaged monitor selectors use complete jq/coreutils and recorded native IPC')

        before = launch_log.read_text()
        run('tam-brightness-display', 'on', extra_env=monitor_env)
        after = [json.loads(line) for line in launch_log.read_text()[len(before):].splitlines()]
        assert all(item['args'][0] != 'dispatch' for item in after)
        run('tam-brightness-display', 'off', extra_env=monitor_env)
        checks.append('packaged DPMS skips redundant enable and reaches recorded disable dispatcher')

        for name, values in [('tam-brightness-display', ('--monitor', 'eDP-1', 'invalid')),
                             ('tam-brightness-display-ddc', ('DP-2', 'invalid')),
                             ('tam-brightness-display-apple', ('invalid',)),
                             ('tam-brightness-keyboard', ('invalid',))]:
            result = run(name, *values, check=False, extra_env=monitor_env)
            assert result.returncode != 0 and 'command not found' not in result.stderr.lower()
        checks.append('packaged brightness writers reject invalid requests without hardware/authorization')

        run('tam-toggle-idle', 'stay-awake')
        run('suspend-unless-stay-awake')
        explicit = root / 'awake-override'
        explicit.touch()
        run('suspend-unless-stay-awake', extra_env={'TAMLINUX_STAY_AWAKE_FILE': str(explicit)})
        run('tam-toggle-idle', 'allow-idle')
        checks.append('packaged idle suspend honors the same XDG marker and explicit override without calling logind')

        missing_pam = {'TAMLINUX_HYPRLOCK_PAM': str(root / 'absent-pam')}
        for name, values in [('tam-system-lock', ()), ('tam-system-sleep-lock', ('20',))]:
            result = run(name, *values, check=False, extra_env=missing_pam)
            assert result.returncode != 0 and 'command not found' not in result.stderr.lower()
        checks.append('packaged lock/sleep-lock stop at missing PAM without launching a locker or suspending')

        result = run('tam-toggle-screensaver', check=False)
        assert result.returncode != 0 and 'bus' in result.stderr.lower()
        assert (root / 'state/tamlinux/toggles/screensaver-off').is_file()
        assert run('tam-launch-screensaver', check=False).returncode != 0
        result = run('tam-toggle-screensaver', check=False)
        assert result.returncode != 0 and 'bus' in result.stderr.lower()
        assert not (root / 'state/tamlinux/toggles/screensaver-off').exists()
        checks.append('packaged screensaver reader/writer share XDG marker and retain both prior states')

        provider_tools = args.commands / 'share/tamlinux/provider-tools.json'
        if provider_tools.is_file():
            ttfx = Path(json.loads(provider_tools.read_text())['ttfx'])
            assert ttfx.is_absolute() and ttfx.is_file()
            result = subprocess.run([str(ttfx), '--version'], env=env, cwd=root,
                                    text=True, capture_output=True, timeout=10, check=True)
            assert result.stdout.strip() == 'ttfx 0.3.2'
            # Probe the effect engine directly; the real screensaver manages
            # compositor state and signals, which belong to physical acceptance.
            result = subprocess.run([str(ttfx), '--seed', '1', '--max-frames', '2',
                                     '--parity-dump', 'beams'], input='TAMLINUX\n',
                                    env=env, cwd=root, capture_output=True, text=True,
                                    timeout=10, check=True)
            assert result.stdout
            wrapper = (args.commands / 'bin/tam-screensaver').read_text()
            assert str(ttfx.parent) in wrapper
            checks.append('owned ttfx renders bounded deterministic frames and screensaver resolves its immutable provider')
        else:
            result = run('tam-screensaver', check=False)
            assert result.returncode != 0
            checks.append('packaged effect helper rejects unavailable ttfx before compositor changes')

        for relative in ('lock/hyprlock.conf', 'lock/LICENSE', 'screensaver/alacritty.toml',
                         'screensaver/foot.ini', 'screensaver/ghostty', 'screensaver/screensaver.txt',
                         'screensaver/LICENSE-omarchy'):
            assert (args.commands / 'share/tamlinux' / relative).is_file()
        checks.append('packaged screensaver terminal/text and lock defaults exist without pre-existing user config')

        run('tam-hyprland-monitor-internal', 'recover', extra_env=monitor_env)
        run('tam-hyprland-monitor-internal-mirror', 'recover', extra_env=monitor_env)
        run('tam-hyprland-monitor-clamshell', extra_env=monitor_env | {'TAMLINUX_LID_PATH': str(root / 'no-lid')})
        assert not (root / 'state/tamlinux/toggles/hypr').exists()
        checks.append('packaged transitive monitor recovery is a no-op for lit outputs without saved flags')

        for name in ('tam-toggle', 'tam-hyprland-toggle'):
            result = run(name, '../escape', check=False)
            assert result.returncode != 0
        checks.append('packaged generic and compositor flag writers reject path traversal')

        result = run('tam-toggle-screensaver', check=False,
                     extra_env={'XDG_STATE_HOME': str(root / 'blocked-state')})
        assert result.returncode != 0 and not (root / 'blocked-state/tamlinux/toggles/screensaver-off').exists()
        checks.append('packaged screensaver preservation failure prevents marker writes')

        # Exercise immutable capture tools without a Wayland server or devices.
        # Fixtures stay with this exact delivery snapshot, rather than user data.
        capture = json.loads((args.commands / 'share/tamlinux/capture-tools.json').read_text())
        for name, value in capture.items():
            if name == 'gpu-screen-recorder':
                assert value == '/usr/bin/gpu-screen-recorder'
                continue
            path = Path(value)
            assert value.startswith('/nix/store/') and path.is_file(), (name, value)
        assert Path(capture['englishData']).stat().st_size > 1_000_000
        checks.append('capture manifest pairs immutable tools/OCR data with the fixed signed native recorder boundary')

        fixtures = args.capture_fixtures
        decoded = subprocess.run([capture['zbarimg'], '-q', '--raw', '-Sdisable', '-Sqrcode.enable',
                                  str(fixtures / 'qr.png')], env=env, text=True, capture_output=True, timeout=10)
        assert decoded.returncode == 0 and decoded.stdout.strip() == 'tamlinux capture fixture', decoded.stderr
        checks.append('actual packaged QR decoder recognizes the fixed offline QR fixture')
        ocr = subprocess.run([capture['tesseract'], str(fixtures / 'ocr.png'), 'stdout', '--oem', '1',
                              '--psm', '6', '-l', 'eng'], env=env, text=True, capture_output=True, timeout=10)
        assert ocr.returncode == 0 and ocr.stdout.strip() == 'Tamlinux capture test', ocr.stderr
        checks.append('actual packaged OCR and English language data recognize the fixed text fixture')

        invalid = run('tam-capture-screenshot', 'invalid', check=False)
        assert invalid.returncode != 0 and 'Invalid capture mode' in invalid.stderr
        checks.append('installed screenshot rejects invalid input before picker or cursor side effects')
        for name, values in [('tam-capture-screenrecording', ('--status',)),
                             ('tam-capture-screenrecording', ('--stop-recording',)),
                             ('tam-capture-screenrecording', ('--unknown',))]:
            result = run(name, *values, check=False)
            assert result.returncode != 0 and 'command not found' not in result.stderr.lower()
        checks.append('packaged recording lifecycle status/stop reject absent recording without starting a backend')

        capture_monitor = {'name': 'DP-fixture', 'focused': True, 'x': -1280, 'y': 0,
                           'width': 2560, 'height': 1440, 'scale': 2, 'transform': 0,
                           'activeWorkspace': {'id': 1}}
        extra = {'TEST_MONITORS': json.dumps([capture_monitor])}
        assert run('tam-capture-region', 'fullscreen', extra_env=extra).stdout == '-1280,0 1280x720\n'
        assert run('tam-capture-region', 'fullscreen', '--match-monitor', extra_env=extra).stdout == 'monitor:DP-fixture\n'
        checks.append('installed capture geometry and monitor matching resolve packaged jq against recorded compositor')

        edit = root / 'capture image; literal.png'
        edit.touch()
        editor = host_bin / 'tensaku'
        editor.write_text(launch_recorder)
        editor.chmod(0o755)
        run('tam-capture-edit', str(edit), extra_env={'TAMLINUX_TENSAKU': str(editor)})
        launch = json.loads(launch_log.read_text().splitlines()[-1])
        assert launch['name'] == 'tensaku' and launch['args'][:4] == ['--filename', str(edit), '--output-filename', str(edit)]
        checks.append('packaged annotation adapter preserves filename argv at the explicit recorded provider boundary')
        if provider_tools.is_file():
            selected = json.loads(provider_tools.read_text())
            if 'tensaku' in selected:
                provider = Path(selected['tensaku'])
                result = subprocess.run([str(provider), '--version'], env=env, cwd=root,
                    text=True, capture_output=True, timeout=10, check=True)
                assert '0.29.0' in result.stdout
                result = subprocess.run([str(provider), '--help'], env=env, cwd=root,
                    text=True, capture_output=True, timeout=10, check=True)
                assert '--wire-omarchy' not in result.stdout and '--install-omarchy-wrapper' not in result.stdout
                assert '--filename' in result.stdout and '--wire-capture-key' in result.stdout
                assert str(provider) in (args.commands / 'bin/tam-capture-edit').read_text()
                checks.append('maintained annotation provider retains image/capture interfaces and excludes inherited self-install wiring')
            if 'asdcontrol' in selected:
                result = subprocess.run([selected['asdcontrol'], '--help'], env=env, cwd=root,
                    text=True, capture_output=True, timeout=10, check=True)
                assert 'brightness' in result.stdout.lower()
                checks.append('maintained Apple display provider exposes its interface without opening a device')

        if (args.commands / 'bin/tam-reminder').is_file():
            reminder = run('tam-reminder', 'show', '--json')
            assert json.loads(reminder.stdout)['count'] == 0
            assert 'command not found' not in reminder.stderr
            checks.append('packaged reminder listing resolves its embedded helper, systemd and jq with an unavailable bus')
            assert run('tam-hyprland-window-pop', '0', check=False).returncode == 2
            checks.append('packaged window geometry rejects invalid dimensions before compositor calls')

        if (args.commands / 'bin/tam-session-init').is_file():
            fresh = root / 'fresh-consumers'
            config = fresh / 'config'
            extra = {'HOME': str(fresh / 'home'), 'XDG_CONFIG_HOME': str(fresh / 'config'),
                     'XDG_STATE_HOME': str(fresh / 'state'), 'XDG_DATA_HOME': str(fresh / 'data')}
            initialized = json.loads(run('tam-session-init', extra_env=extra).stdout)
            assert len(initialized['created']) == 11
            mime = (config / 'mimeapps.list').read_text()
            assert 'text/plain=Helix.desktop' in mime
            assert 'x-scheme-handler/http=chromium.desktop' in mime
            assert 'HEY.desktop' not in mime
            assert not (fresh / 'data/applications/HEY.desktop').exists()
            assert str(fresh / 'state/tamlinux/current/theme/alacritty.toml') in (config / 'alacritty/alacritty.toml').read_text()
            assert (fresh / 'state/tamlinux/defaults/editor').read_text() == 'helix\n'
            assert (config / 'helix/themes/tamlinux.toml').is_symlink()
            assert json.loads(run('tam-session-init', extra_env=extra).stdout)['created'] == []
            checks.append('installed fresh consumer defaults pair custom XDG theme/editor paths without replacing existing files')

        if (args.commands / 'bin/tam-migrate-desktop').is_file():
            migration = root / 'migration-proof'
            extra = {'HOME': str(migration / 'home'), 'XDG_CONFIG_HOME': str(migration / 'config'),
                     'XDG_STATE_HOME': str(migration / 'state'), 'XDG_DATA_HOME': str(migration / 'data')}
            mode = migration / 'state/tamlinux/desktop-mode'
            mode.parent.mkdir(parents=True); mode.write_text('omarchy\n')
            journal = migration / 'state/tamlinux/migration/proof'
            plan = json.loads(run('tam-migrate-desktop', 'plan', str(journal), extra_env=extra).stdout)
            assert plan['status'] == 'prepared' and plan['rows'] == 1
            run('tam-migrate-desktop', 'apply', str(journal), extra_env=extra)
            assert mode.read_text() == 'tamlinux\n'
            mode.write_text('windows\n')
            run('tam-migrate-desktop', 'rollback', str(journal), extra_env=extra)
            assert mode.read_text() == 'omarchy\n'
            archives = [json.loads(p.read_text()) for p in (journal / 'new-writes').rglob('*.json')]
            assert any(p['state'].get('bytes') == 'd2luZG93cwo=' for p in archives)
            checks.append('installed finite migration converts legacy state and preserves later writes during explicit rollback')

            icon = args.commands / 'share/tamlinux/assets/icons/tamlinux-discord.png'
            if icon.is_file():
                themed = args.commands / 'share/icons/hicolor/256x256/apps/tamlinux-discord.png'
                assert themed.read_bytes() == icon.read_bytes()
                assert themed.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
                app = migration / 'data/applications/Discord.desktop'
                app.parent.mkdir(parents=True, exist_ok=True)
                original = b'[Desktop Entry]\nExec=omarchy-launch-webapp https://discord.com/channels/@me\nIcon=omarchy-discord\n'
                app.write_bytes(original)
                icon_journal = journal.with_name('discord')
                plan = json.loads(run('tam-migrate-desktop', 'plan', str(icon_journal), extra_env=extra).stdout)
                assert plan['status'] == 'prepared'
                run('tam-migrate-desktop', 'apply', str(icon_journal), extra_env=extra)
                assert app.read_bytes() == original.replace(b'omarchy-launch-webapp', b'tam-launch-webapp').replace(b'Icon=omarchy-discord', b'Icon=tamlinux-discord')
                run('tam-migrate-desktop', 'rollback', str(icon_journal), extra_env=extra)
                assert app.read_bytes() == original
                checks.append('installed Discord launcher migration resolves an owned hicolor icon and restores exact original bytes')
            checkpoint = migration / 'state/tamlinux/migration/before-test'
            layout = migration / 'config/tamlinux/hypr/monitors.lua'
            layout.parent.mkdir(parents=True)
            layout.write_text('left center right\n')
            saved = json.loads(run('tam-migrate-desktop', 'preserve', str(checkpoint), extra_env=extra).stdout)
            assert saved['status'] == 'preserved' and saved['gtkCaptured'] is False
            layout.write_text('later monitor arrangement\n')
            restored = json.loads(run('tam-migrate-desktop', 'restore', str(checkpoint), extra_env=extra).stdout)
            assert restored['status'] == 'restored' and layout.read_text() == 'left center right\n'
            records = [json.loads(p.read_text()) for p in (checkpoint / 'new-writes').glob('*.json')]
            later = records[0]['files'][str(layout)]['blob']
            assert (checkpoint / 'blobs' / later).read_text() == 'later monitor arrangement\n'
            assert json.loads(run('tam-migrate-desktop', 'checkpoint-status', str(checkpoint), extra_env=extra).stdout)['status'] == 'restored'
            checks.append('installed settings checkpoint restores monitor layout and archives later arrangements through the packaged engine')

            # Use another empty user root so the installed retirement is tested
            # without touching the caller's original migration/recovery journals.
            retired = root / 'hey-retirement'
            extra = {'HOME': str(retired / 'home'), 'XDG_CONFIG_HOME': str(retired / 'config'),
                     'XDG_STATE_HOME': str(retired / 'state'), 'XDG_DATA_HOME': str(retired / 'data')}
            app = retired / 'data/applications/HEY.desktop'
            app.parent.mkdir(parents=True)
            original = ('[Desktop Entry]\nVersion=1.0\nName=HEY\nExec=tam-webapp-handler-hey %u\n'
                        'Terminal=false\nType=Application\nIcon=hey\nStartupNotify=true\n'
                        'MimeType=x-scheme-handler/mailto\n')
            app.write_text(original)
            mime = retired / 'config/mimeapps.list'
            mime.parent.mkdir(parents=True)
            original_mime = '[Default Applications]\nx-scheme-handler/mailto=HEY.desktop;other.desktop;\n'
            mime.write_text(original_mime)
            journal = retired / 'state/tamlinux/migration/proof'
            planned = json.loads(run('tam-migrate-desktop', 'plan', str(journal), extra_env=extra).stdout)
            assert planned['status'] == 'prepared' and planned['rows'] == 2
            run('tam-migrate-desktop', 'apply', str(journal), extra_env=extra)
            assert not app.exists()
            assert mime.read_text() == original_mime.replace('HEY.desktop;', '')
            cache = app.parent / 'mimeinfo.cache'
            assert cache.is_file() and 'HEY.desktop' not in cache.read_text()
            run('tam-migrate-desktop', 'apply', str(journal), extra_env=extra)
            app.write_text('[Desktop Entry]\nName=Personal\nType=Application\nExec=personal\n')
            run('tam-migrate-desktop', 'rollback', str(journal), extra_env=extra)
            assert app.read_text() == original and mime.read_text() == original_mime
            assert 'HEY.desktop' in cache.read_text()
            archives = [json.loads(p.read_text()) for p in (journal / 'new-writes').rglob('*.json')]
            assert any(b'Name=Personal' in base64.b64decode(p['state'].get('bytes', '')) for p in archives)
            checks.append('installed HEY retirement removes only its launcher/MIME token, refreshes the desktop database and preserves later writes on return')
            bindings = (args.shell / 'share/tamlinux/session/hypr/tamlinux/bindings/applications.lua').read_text()
            assert 'app.hey.com' not in bindings
            checks.append('packaged application bindings contain no retired HEY email/calendar defaults')

    print(json.dumps({'checks': checks, 'passed': len(checks),
                      'limits': 'Recorded host IPC and unavailable buses; no live desktop or clean-host installation proof.'}, indent=2))


if __name__ == '__main__':
    main()
