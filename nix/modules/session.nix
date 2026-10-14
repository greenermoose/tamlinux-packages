{ config, lib, pkgs, ... }:
let
  cfg = config.tamlinux.session;
  shell = config.tamlinux.shell;
  browser = "${shell.commandPackage}/share/tamlinux/browser";
  nativeHost = name: command: origin: builtins.toJSON {
    inherit name;
    description = "Tamlinux Chromium native messaging endpoint";
    path = "${shell.commandPackage}/bin/${command}";
    type = "stdio";
    allowed_origins = [ "chrome-extension://${origin}/" ];
  };
in {
  options.tamlinux.session = {
    enable = lib.mkEnableOption "owned Arch/Hyprland fresh-login defaults";
    chromiumExtensions.enable = lib.mkEnableOption "paired Tamlinux Chromium extensions and native hosts";
    chromiumExtensions.manageFlags = lib.mkEnableOption "a fresh Chromium flags file loading the owned extensions";
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !cfg.chromiumExtensions.manageFlags || cfg.chromiumExtensions.enable;
        message = "Managed Chromium flags require the paired extension registrations.";
      }
      {
        assertion = shell.enable && (shell.package.passthru.features.sessionProviders or false)
          && shell.quickshellPackage != null;
        message = "Fresh-login delivery requires paired shell providers and owned product session defaults.";
      }
    ];
    xdg.configFile = {
      "tamlinux/session/hyprland.lua".text =
        "dofile(\"${shell.package}/share/tamlinux/session/entry.lua\")\n";
      "uwsm/env.d/10-tamlinux.sh".text = ''
        . ${shell.package}/share/tamlinux/session/uwsm-env
        export TAMLINUX_QUICKSHELL=${shell.quickshellPackage}/bin/quickshell
        export TAMLINUX_QUICKSHELL_IPC=${shell.quickshellPackage}/bin/qs
        export TAMLINUX_STAY_AWAKE_FILE=${lib.escapeShellArg config.home.sessionVariables.TAMLINUX_STAY_AWAKE_FILE}
      '';
      "xdg-desktop-portal/hyprland-portals.conf".text = ''
        [preferred]
        default=hyprland;gtk
        org.freedesktop.impl.portal.FileChooser=gtk
      '';
    } // lib.optionalAttrs cfg.chromiumExtensions.enable ({
      "tamlinux/chromium/extensions".source = "${browser}/extensions";
      "chromium/NativeMessagingHosts/org.tamlinux.copy_url.json".text =
        nativeHost "org.tamlinux.copy_url" "tam-chromium-copy-url-host" "bgpiichlckmfanooecilcjemknkcpngb";
      "chromium/NativeMessagingHosts/org.tamlinux.ytdlp.json".text =
        nativeHost "org.tamlinux.ytdlp" "tam-chromium-ytdlp-host" "dedjgknigfeelejglamclffonmophnfl";
    } // lib.optionalAttrs cfg.chromiumExtensions.manageFlags {
      "chromium-flags.conf".text = ''
        --ozone-platform=wayland
        --password-store=gnome-libsecret
        --enable-features=TouchpadOverscrollHistoryNavigation
        --load-extension=${browser}/extensions/copy-url,${browser}/extensions/yt-dlp,${browser}/extensions/whatsapp-slim
      '';
    });
    home.file.".local/bin/tamlinux-hyprland-session".source = "${shell.package}/bin/tamlinux-hyprland-session";
    home.packages = [ pkgs.udiskie ];
    fonts.fontconfig.enable = true;
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
