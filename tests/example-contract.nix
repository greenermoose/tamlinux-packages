{ pkgs, example }:
let
  c = example.config;
  unit = c.systemd.user.services.tamlinux-shell;
in
assert c.home.username == "alex";
assert c.tamlinux.developer.enable && !c.tamlinux.developer.nativeProvided;
assert c.home.file.".local/bin/tam-man".source == "${c.tamlinux.tools.tam}/bin/tam-man";
assert !c.tamlinux.shell.protocolShadow.enable;
assert builtins.elem "TAMLINUX_BACKGROUND_LINK=/home/alex/.local/state/tamlinux/current/background"
  unit.Service.Environment;
assert builtins.elem "TAMLINUX_MENU_EXTENSION=/home/alex/.config/tamlinux/menu/extension.jsonc"
  unit.Service.Environment;
assert c.home.file.".local/share/tamlinux/shell".source
  == "${c.tamlinux.shell.package}/share/tamlinux/shell";
assert c.home.file.".local/share/tamlinux/shell-revision".text
  == "${c.tamlinux.shell.package.passthru.revision}\n";
assert !c.tamlinux.shell.package.passthru.features.menu ||
  (c.xdg.configFile."tamlinux/menu".source != null &&
    c.home.file.".local/bin/tam-menu".source != null &&
    builtins.elem "TAMLINUX_MENU_DEFAULT=/home/alex/.config/tamlinux/menu/default.jsonc"
      unit.Service.Environment);
pkgs.runCommand "tamlinux-example-contract" { } ''
  test -f ${example.activationPackage}/home-files/.config/systemd/user/tamlinux-shell.service
  test -x ${example.activationPackage}/home-files/.local/bin/tam-man
  ${pkgs.lib.optionalString c.tamlinux.shell.package.passthru.features.menu ''
    test -f ${example.activationPackage}/home-files/.config/tamlinux/menu/default.jsonc
    test -x ${example.activationPackage}/home-files/.local/bin/tam-menu
  ''}
  mkdir -p $out
  cp ${example.activationPackage}/home-files/.config/systemd/user/tamlinux-shell.service $out/
''
