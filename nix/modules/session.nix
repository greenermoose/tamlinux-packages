{ config, lib, ... }:
let
  cfg = config.tamlinux.session;
  shell = config.tamlinux.shell;
in {
  options.tamlinux.session.enable = lib.mkEnableOption "owned Arch/Hyprland fresh-login defaults";
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = shell.enable && (shell.package.passthru.features.sessionProviders or false)
          && shell.quickshellPackage != null;
        message = "Fresh-login delivery requires paired shell providers and owned product session defaults.";
      }
    ];
    xdg.configFile."tamlinux/session/hyprland.lua".text =
      "dofile(\"${shell.package}/share/tamlinux/session/entry.lua\")\n";
    xdg.configFile."uwsm/env.d/10-tamlinux.sh".text = ''
      . ${shell.package}/share/tamlinux/session/uwsm-env
      export TAMLINUX_QUICKSHELL=${shell.quickshellPackage}/bin/quickshell
      export TAMLINUX_QUICKSHELL_IPC=${shell.quickshellPackage}/bin/qs
    '';
    home.file.".local/bin/tamlinux-hyprland-session".source = "${shell.package}/bin/tamlinux-hyprland-session";
  };
}
