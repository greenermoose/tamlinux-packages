{ pkgs, home-manager, components }:
let
  hm = home-manager.lib.homeManagerConfiguration {
    inherit pkgs;
    modules = [ ../nix/modules {
      home.username = "alex";
      home.homeDirectory = "/home/alex";
      home.stateVersion = "25.05";
      manual.manpages.enable = false;
      tamlinux.shell = {
        enable = true;
        package = components.tamlinux-shell;
        commandPackage = components.tamlinux-commands;
        pluginPackage = components.tamlinux-plugins;
      };
      tamlinux.session.enable = true;
      tamlinux.tools = { tam = components.tam; fileSelect = components.tamlinux-tools; };
    } ];
  };
  c = hm.config;
  q = c.tamlinux.shell.quickshellPackage;
  unit = c.systemd.user.services.tamlinux-shell.Service;
  files = "${hm.activationPackage}/home-files";
in
assert builtins.elem "TAMLINUX_QUICKSHELL=${q}/bin/quickshell" unit.Environment;
assert builtins.elem "TAMLINUX_QUICKSHELL_IPC=${q}/bin/qs" unit.Environment;
assert c.home.sessionVariables.TAMLINUX_QUICKSHELL_IPC == "${q}/bin/qs";
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
  grep -q 'tam-toggle-enabled crash-capture-off' ${files}/.config/systemd/user/tam-crash-watch.service
  grep -q 'FileChooser=gtk' ${files}/.config/xdg-desktop-portal/hyprland-portals.conf
  test ! -e ${files}/.config/tamlinux/hypr/monitors.lua
  grep -q ${q}/bin/qs ${files}/.config/uwsm/env.d/10-tamlinux.sh
  mkdir -p $out
  cp ${files}/.config/systemd/user/tamlinux-shell.service $out/
  cp ${files}/.config/tamlinux/session/hyprland.lua $out/
''
