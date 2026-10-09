{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.tamlinux.shell;
  shell = cfg.package;
  features = shell.passthru.features;
  protocolShadowAvailable = cfg.protocolShadow.enable;
  selectedPlugins = if cfg.plugins == null then cfg.pluginPackage.passthru.ids else cfg.plugins;
in
{
  options.tamlinux.shell = {
    enable = lib.mkEnableOption "Tamlinux shell deployment on an Arch/Hyprland host";
    package = lib.mkOption {
      type = lib.types.package;
      description = "Tamlinux shell package built from the recorded assembly.";
    };
    pluginPackage = lib.mkOption {
      type = lib.types.package;
      description = "Plugin payloads built from the same product revision as the shell.";
    };
    commandPackage = lib.mkOption {
      type = lib.types.package;
      description = "Tamlinux product commands built from the same product revision.";
    };
    plugins = lib.mkOption {
      type = lib.types.nullOr (lib.types.listOf lib.types.str);
      default = null;
      description = "Plugin IDs to install from the plugin package; null installs all of them.";
    };
    documentation = lib.mkOption {
      type = lib.types.str;
      default =
        if features.documentation then "file://${shell}/share/tamlinux/README.md" else "https://github.com/greenermoose/tamlinux";
      description = "Product documentation URI.";
    };
    layoutSource = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
    };
    settingsSource = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
    };
    backgroundLink = lib.mkOption {
      type = lib.types.str;
      default = "${config.xdg.stateHome}/tamlinux/current/background";
      description = "Mutable background selection owned by user configuration.";
    };
    menuExtension = lib.mkOption {
      type = lib.types.str;
      default = "${config.xdg.configHome}/tamlinux/menu/extension.jsonc";
    };
    menuExtensionSource = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "Optional private extension payload, installed at the owned menu path.";
    };
    menuLauncherHidesSource = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "Optional mutable launcher filter, linked inside the owned menu directory.";
    };
    protocolShadow.enable = lib.mkEnableOption "the explicitly selected read-only protocol trial";
  };
  config = lib.mkIf cfg.enable {
    tamlinux.developer.enable = lib.mkDefault true;
    assertions = [
      {
        assertion = config.tamlinux.developer.enable;
        message = "Every Tamlinux shell installation requires the developer baseline (Nix or verified host tools).";
      }
      {
        assertion = !protocolShadowAvailable || features.protocolShadow;
        message = "The selected assembly must contain the requested protocol shadow trial.";
      }
      {
        assertion = (cfg.menuExtensionSource == null && cfg.menuLauncherHidesSource == null) || features.menu;
        message = "Owned menu extension delivery requires an assembly with product menu defaults and tam-menu.";
      }
      {
        assertion = lib.all (id: lib.elem id cfg.pluginPackage.passthru.ids) selectedPlugins;
        message = "Selected plugins must be in the assembly's plugin package: "
          + lib.concatStringsSep ", " cfg.pluginPackage.passthru.ids;
      }
      {
        assertion = shell.passthru.revision == cfg.pluginPackage.passthru.revision
          && shell.passthru.revision == cfg.commandPackage.passthru.revision;
        message = "Shell, plugins and commands must come from the same product revision.";
      }
    ];
    home.file =
      {
        ".local/share/tamlinux/shell".source = "${shell}/share/tamlinux/shell";
        ".local/share/tamlinux/shell-revision".text = "${shell.passthru.revision}\n";
      }
      // lib.optionalAttrs features.menu {
        ".local/bin/tam-menu".source = "${shell}/bin/tam-menu";
      }
      // lib.optionalAttrs protocolShadowAvailable {
        ".local/bin/tam-protocol-shadow".source = "${shell}/bin/tam-protocol-shadow";
      }
      // lib.listToAttrs (
        map (name: lib.nameValuePair ".local/bin/${name}" { source = "${cfg.commandPackage}/bin/${name}"; })
          cfg.commandPackage.passthru.names
      );
    xdg.configFile =
      lib.listToAttrs (
        map (
          id: lib.nameValuePair "tamlinux/plugins/${id}" { source = "${cfg.pluginPackage}/share/tamlinux/plugins/${id}"; }
        ) selectedPlugins
      )
      // lib.optionalAttrs (cfg.layoutSource != null) {
        "tamlinux/shell/layout.json".source = cfg.layoutSource;
      }
      // lib.optionalAttrs (cfg.settingsSource != null) {
        "tamlinux/shell/settings.json".source = cfg.settingsSource;
      }
      // lib.optionalAttrs features.menu {
        # One directory link replaces legacy whole-directory Home Manager
        # links without traversing them into a mutable source checkout.
        "tamlinux/menu".source = pkgs.linkFarm "tamlinux-menu" (
          [{ name = "default.jsonc"; path = "${shell}/share/tamlinux/menu/default.jsonc"; }]
          ++ lib.optionals (cfg.menuExtensionSource != null) [
            { name = "extension.jsonc"; path = cfg.menuExtensionSource; }
          ]
          ++ lib.optionals (cfg.menuLauncherHidesSource != null) [
            { name = "launcher.hides"; path = cfg.menuLauncherHidesSource; }
          ]
        );
      };
    # Preflight check before checkLinkTargets and writeBoundary:
    # Reject any active dev or test override symlink or stale recovery state
    # in ~/.local/state/tam-plugin/ to prevent Home Manager from resolving
    # through symlinks and mutating the source Git checkout with store links.
    home.activation.checkPluginOverrides = config.lib.dag.entryBefore [ "checkLinkTargets" ] ''
      stateDir="''${XDG_STATE_HOME:-${config.home.homeDirectory}/.local/state}/tam-plugin"
      has_error=0

      for pluginsDir in "${config.xdg.configHome}/omarchy/plugins" "${config.xdg.configHome}/tamlinux/plugins"; do
      if [[ -d "$pluginsDir" ]]; then
        for pluginDir in "$pluginsDir"/fred.*; do
          [[ -e "$pluginDir" || -L "$pluginDir" ]] || continue
          id="''${pluginDir##*/}"
          if [[ -L "$pluginDir" && "$(readlink -f "$pluginDir")" != /nix/store/* ]]; then
            target=$(readlink "$pluginDir" 2>/dev/null || true)
            echo "Error: Cannot switch Home Manager configuration: plugin '$id' is an active override link." >&2
            echo "  Observed target: $target" >&2
            echo "  Recovery command: tam-plugin restore $id" >&2
            has_error=1
          fi
          if [[ -e "$stateDir/dev/$id/original" || -e "$stateDir/dev/$id/original.absent" || -f "$stateDir/dev/$id/active" || -e "$stateDir/test/$id/original" || -e "$stateDir/test/$id/original.absent" || -f "$stateDir/test/$id/active" ]]; then
            echo "Error: Cannot switch Home Manager configuration: plugin '$id' has active or uncommitted override state in $stateDir." >&2
            echo "  Recovery command: tam-plugin restore $id" >&2
            has_error=1
          fi
        done
      fi

      done

      if (( has_error != 0 )); then
        echo "Home Manager activation aborted to protect repository source checkouts." >&2
        exit 1
      fi
    '';

    systemd.user.services.tamlinux-shell = {
      Unit = {
        Description = "Tamlinux shell (bar, panels, and session services)";
        Documentation = cfg.documentation;
        After = [ "graphical-session.target" ];
        PartOf = [ "graphical-session.target" ];
        ConditionEnvironment = "WAYLAND_DISPLAY";
      };
      Service = {
        Type = "simple";
        ExecStart = "/usr/bin/python3 -I ${config.home.homeDirectory}/.local/share/tamlinux/shell/host/session_start.py";
        Environment = [
          "QML_IMPORT_PATH=${config.home.homeDirectory}/.local/share/tamlinux/shell/modules"
          "QS_DISABLE_FILE_WATCHER=1"
          "QS_NO_RELOAD_POPUP=1"
          "TAMLINUX_BAR_LAYOUT=${config.home.homeDirectory}/.config/tamlinux/shell/layout.json"
          "TAMLINUX_PLUGINS_DIR=${config.home.homeDirectory}/.config/tamlinux/plugins"
          "TAMLINUX_BAR_EXCLUSIVE=1"
          "TAMLINUX_OUTPUT=all"
          "TAMLINUX_HOST_ACTIONS=1"
          "TAMLINUX_SERVICES=theme,notifications,osd,clipboard,emojis,imagepicker,reminders,menu,background,polkit,media,idle,nightlight,battery,keybindings,panels"
          "TAMLINUX_PANELS=audio,bluetooth,network,wifiqr,power,speedtest,disk-speedtest"
          "TAMLINUX_STAY_AWAKE_FILE=${config.home.homeDirectory}/.local/state/tamlinux/indicators/stay-awake"
          "TAMLINUX_BACKGROUND_LINK=${cfg.backgroundLink}"
          "TAMLINUX_MENU_EXTENSION=${cfg.menuExtension}"
          "TAMLINUX_APP_REMOVER=tam-remove-launcher-entry"
          "TAMLINUX_COMPOSITOR_LIVE_ACTIONS=1"
          "QT_QPA_PLATFORM=wayland"
        ]
        ++ lib.optionals features.menu [
          "TAMLINUX_MENU_DEFAULT=${config.xdg.configHome}/tamlinux/menu/default.jsonc"
        ]
        ++ lib.optionals protocolShadowAvailable [
          # 0.4.1 read-only protocol trial; the package hashes only trial code.
          "TAMLINUX_PROTOCOL_SHADOW=1"
          "TAMLINUX_SHELL_REVISION=${shell.passthru.revision}"
          "TAMLINUX_PROTOCOL_SHADOW_ID=${shell.passthru.protocolShadowId}"
        ];
        Restart = "always";
        RestartSec = 2;
      };
      Install.WantedBy = [ "graphical-session.target" ];
    };

    # Retain the trial across journal rotation and login/reboot. Collection is
    # idempotent, read-only to the desktop, and resumes after sleep; failures
    # stay visible in this unit's journal and in the evidence summary.
    systemd.user.services.tamlinux-protocol-shadow-collect = lib.mkIf protocolShadowAvailable {
      Unit.Description = "Archive Tamlinux compositor shadow evidence";
      Service = {
        Type = "oneshot";
        ExecStart = "${pkgs.python3}/bin/python3 -I ${shell}/bin/tam-protocol-shadow collect";
        TimeoutStartSec = 60;
        UMask = "0077";
      };
    };
    systemd.user.timers.tamlinux-protocol-shadow-collect = lib.mkIf protocolShadowAvailable {
      Unit.Description = "Collect Tamlinux compositor shadow evidence every five minutes";
      Timer = {
        OnCalendar = "*:0/5";
        Persistent = true;
        OnStartupSec = "1min";
      };
      Install.WantedBy = [ "timers.target" ];
    };

  };
}
