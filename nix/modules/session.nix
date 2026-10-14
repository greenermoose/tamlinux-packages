{ config, lib, pkgs, ... }:
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
    home.packages = [ pkgs.udiskie ];
    fonts.fontconfig.enable = true;
    xdg.configFile."xdg-desktop-portal/hyprland-portals.conf".text = ''
      [preferred]
      default=hyprland;gtk
      org.freedesktop.impl.portal.FileChooser=gtk
    '';
    systemd.user.services.tam-crash-watch = {
      Unit = {
        Description = "Tamlinux process crash notifications";
        After = [ "graphical-session.target" "tamlinux-shell.service" ];
        PartOf = [ "graphical-session.target" ];
      };
      Service = {
        ExecCondition = "${pkgs.bash}/bin/bash -c '! ${shell.commandPackage}/bin/tam-toggle-enabled crash-capture-off'";
        ExecStart = "${shell.commandPackage}/bin/tam-crash-watch";
        Restart = "on-failure";
        RestartSec = 5;
      };
      Install.WantedBy = [ "graphical-session.target" ];
    };
    systemd.user.services.tamlinux-monitor-watch = {
      Unit = {
        Description = "Tamlinux Hyprland monitor recovery watch";
        After = [ "graphical-session.target" ];
        PartOf = [ "graphical-session.target" ];
        ConditionEnvironment = "HYPRLAND_INSTANCE_SIGNATURE";
      };
      Service = {
        Type = "simple";
        ExecStart = "${shell.commandPackage}/bin/tam-hyprland-monitor-watch";
        KillMode = "control-group";
      };
    };
  };
}
