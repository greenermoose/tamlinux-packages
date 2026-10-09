{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.tamlinux.shell;
  tamlinux = cfg.source;
  protocolShadowAvailable = cfg.protocolShadow.enable;
  protocolShadowId =
    if protocolShadowAvailable then
      builtins.hashString "sha256" (
        lib.concatMapStrings (path: builtins.readFile "${tamlinux}/desktop/${path}") [
          "shell/host/ProtocolState.qml"
          "shell/host/protocol_model.js"
          "shell/host/ProtocolShadow.qml"
          "shell/host/HyprlandAdapter.qml"
          "protocol-shadow"
        ]
      )
    else
      "";
in
{
  options.tamlinux.shell = {
    enable = lib.mkEnableOption "Tamlinux shell deployment on an Arch/Hyprland host";
    source = lib.mkOption {
      type = lib.types.path;
      description = "Pinned Tamlinux product source.";
    };
    sourceRevision = lib.mkOption {
      type = lib.types.str;
      description = "Exact product source revision.";
    };
    documentation = lib.mkOption {
      type = lib.types.str;
      default = "file://${cfg.source}/desktop/README.md";
      description = "Product documentation URI.";
    };
    pluginSources = lib.mkOption {
      type = lib.types.attrsOf lib.types.path;
      default = { };
      description = "Explicit immutable plugin payloads; no development checkout links.";
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
      default = "${config.xdg.configHome}/tamlinux/extensions/menu.jsonc";
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
        assertion = !protocolShadowAvailable || builtins.pathExists "${tamlinux}/desktop/protocol-shadow";
        message = "The selected source must contain the requested protocol shadow trial.";
      }
    ];
    home.file.".local/share/tamlinux/shell".source = "${tamlinux}/desktop/shell";
    home.file.".local/share/tamlinux/shell-revision".text = "${cfg.sourceRevision}\n";
    home.file.".local/bin/tam-protocol-shadow" = lib.mkIf protocolShadowAvailable {
      source = "${tamlinux}/desktop/protocol-shadow";
      executable = true;
    };
    xdg.configFile =
      lib.mapAttrs' (
        id: source: lib.nameValuePair "tamlinux/plugins/${id}" { inherit source; }
      ) cfg.pluginSources
      // lib.optionalAttrs (cfg.layoutSource != null) {
        "tamlinux/shell/layout.json".source = cfg.layoutSource;
      }
      // lib.optionalAttrs (cfg.settingsSource != null) {
        "tamlinux/shell/settings.json".source = cfg.settingsSource;
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
        ++ lib.optionals protocolShadowAvailable [
          # 0.4.1 read-only protocol trial. Hash only trial code so unrelated
          # later shell/menu commits preserve its observation identity.
          "TAMLINUX_PROTOCOL_SHADOW=1"
          "TAMLINUX_SHELL_REVISION=${cfg.sourceRevision}"
          "TAMLINUX_PROTOCOL_SHADOW_ID=${protocolShadowId}"
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
        ExecStart = "${pkgs.python3}/bin/python3 -I ${tamlinux}/desktop/protocol-shadow collect";
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
