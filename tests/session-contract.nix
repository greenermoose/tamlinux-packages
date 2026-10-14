{ pkgs, home-manager, components }:
let
  makeHome = stateHome: home-manager.lib.homeManagerConfiguration {
    inherit pkgs;
    modules = [ ../nix/modules {
      home.username = "alex";
      home.homeDirectory = "/home/alex";
      home.stateVersion = "25.05";
      xdg.stateHome = stateHome;
      manual.manpages.enable = false;
      tamlinux.shell = {
        enable = true;
        package = components.tamlinux-shell;
        commandPackage = components.tamlinux-commands;
        pluginPackage = components.tamlinux-plugins;
      };
      tamlinux.session = { enable = true; chromiumExtensions.enable = true; };
      tamlinux.tools = { tam = components.tam; fileSelect = components.tamlinux-tools; };
    } ];
  };
  hm = makeHome "/home/alex/.local/state";
  customHome = makeHome "/home/alex/state with spaces";
  c = hm.config;
  q = c.tamlinux.shell.quickshellPackage;
  unit = c.systemd.user.services.tamlinux-shell.Service;
  files = "${hm.activationPackage}/home-files";
in
assert builtins.elem "TAMLINUX_QUICKSHELL=${q}/bin/quickshell" unit.Environment;
assert builtins.elem "TAMLINUX_QUICKSHELL_IPC=${q}/bin/qs" unit.Environment;
assert c.home.sessionVariables.TAMLINUX_QUICKSHELL_IPC == "${q}/bin/qs";
assert c.home.sessionVariables.TAMLINUX_STAY_AWAKE_FILE == "/home/alex/.local/state/tamlinux/stay-awake";
assert builtins.elem "TAMLINUX_STAY_AWAKE_FILE=${c.home.sessionVariables.TAMLINUX_STAY_AWAKE_FILE}" unit.Environment;
assert customHome.config.home.sessionVariables.TAMLINUX_STAY_AWAKE_FILE == "/home/alex/state with spaces/tamlinux/stay-awake";
assert builtins.elem "TAMLINUX_STAY_AWAKE_FILE=${customHome.config.home.sessionVariables.TAMLINUX_STAY_AWAKE_FILE}"
  customHome.config.systemd.user.services.tamlinux-shell.Service.Environment;
assert unit.ExecStart == [ "${pkgs.python3}/bin/python3 -I /home/alex/.local/share/tamlinux/shell/host/session_start.py" ];
pkgs.runCommand "tamlinux-fresh-session-contract" { } ''
  test -f ${files}/.config/tamlinux/session/hyprland.lua
  test -f ${files}/.config/uwsm/env.d/10-tamlinux.sh
  test -x ${files}/.local/bin/tamlinux-hyprland-session
  test -x ${files}/.local/bin/tam-session-init
  test -x ${files}/.local/bin/tam-migrate-desktop
  test -f ${files}/.config/systemd/user/tamlinux-monitor-watch.service
  test -f ${files}/.config/systemd/user/tam-crash-watch.service
  test -f ${files}/.config/xdg-desktop-portal/hyprland-portals.conf
  test -f ${files}/.config/tamlinux/chromium/extensions/copy-url/manifest.json
  test -f ${files}/.config/chromium/NativeMessagingHosts/org.tamlinux.copy_url.json
  test -f ${files}/.config/chromium/NativeMessagingHosts/org.tamlinux.ytdlp.json
  test ! -e ${files}/.config/chromium-flags.conf
  ${pkgs.python3}/bin/python3 - ${files} ${components.tamlinux-commands} <<'PY'
import json,sys
from pathlib import Path
files,commands=map(Path,sys.argv[1:])
for name,command,extension in [('copy_url','copy-url','bgpiichlckmfanooecilcjemknkcpngb'),('ytdlp','ytdlp','dedjgknigfeelejglamclffonmophnfl')]:
    data=json.loads((files/f'.config/chromium/NativeMessagingHosts/org.tamlinux.{name}.json').read_text())
    assert data['path']==str(commands/f'bin/tam-chromium-{command}-host')
    assert data['allowed_origins']==[f'chrome-extension://{extension}/']
    assert Path(data['path']).is_file()
PY
  grep -q 'tam-toggle-enabled crash-capture-off' ${files}/.config/systemd/user/tam-crash-watch.service
  grep -q 'FileChooser=gtk' ${files}/.config/xdg-desktop-portal/hyprland-portals.conf
  test ! -e ${files}/.config/tamlinux/hypr/monitors.lua
  grep -q ${q}/bin/qs ${files}/.config/uwsm/env.d/10-tamlinux.sh
  # Source the actual delivered session snippets: a spaced custom XDG root
  # must reach command/suspend clients as the same single path as the bar.
  ${pkgs.bash}/bin/bash -c '. "$1"; test "$TAMLINUX_STAY_AWAKE_FILE" = "$2"' -- \
    ${files}/.config/uwsm/env.d/10-tamlinux.sh \
    /home/alex/.local/state/tamlinux/stay-awake
  ${pkgs.bash}/bin/bash -c '. "$1"; test "$TAMLINUX_STAY_AWAKE_FILE" = "$2"' -- \
    ${customHome.activationPackage}/home-files/.config/uwsm/env.d/10-tamlinux.sh \
    '/home/alex/state with spaces/tamlinux/stay-awake'
  mkdir -p $out
  cp ${files}/.config/systemd/user/tamlinux-shell.service $out/
  cp ${files}/.config/tamlinux/session/hyprland.lua $out/
''
