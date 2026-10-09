{ pkgs, example }:
let
  c = example.config;
  unit = c.systemd.user.services.tamlinux-shell;
in
assert c.home.username == "alex";
assert c.tamlinux.developer.enable && !c.tamlinux.developer.nativeProvided;
assert !c.tamlinux.shell.protocolShadow.enable;
assert builtins.elem "TAMLINUX_BACKGROUND_LINK=/home/alex/.local/state/tamlinux/current/background"
  unit.Service.Environment;
assert builtins.elem "TAMLINUX_MENU_EXTENSION=/home/alex/.config/tamlinux/extensions/menu.jsonc"
  unit.Service.Environment;
assert c.home.file.".local/share/tamlinux/shell".source != null;
pkgs.runCommand "tamlinux-example-contract" { } ''
  test -f ${example.activationPackage}/home-files/.config/systemd/user/tamlinux-shell.service
  mkdir -p $out
  cp ${example.activationPackage}/home-files/.config/systemd/user/tamlinux-shell.service $out/
''
