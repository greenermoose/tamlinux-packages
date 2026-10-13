{ pkgs, sources }:
let
  libtam = pkgs.stdenv.mkDerivation {
    pname = "libtam";
    version = "0.2.0";
    src = sources.libtam;
    nativeBuildInputs = [ pkgs.pkg-config ];
    buildInputs = [ pkgs.dbus ];
    makeFlags = [ "PREFIX=$(out)" ];
    doCheck = true;
    meta.license = pkgs.lib.licenses.gpl3Plus;
  };
  tam = pkgs.stdenv.mkDerivation {
    pname = "tam";
    version = "0.9.1";
    passthru.features.manWrapper = true;
    src = sources.tam;
    postPatch = "patchShebangs tests";
    # The command tests read the guide from the source tree, not from $HOME.
    preCheck = "export TAM_KNOWLEDGE_DIR=$PWD/knowledge";
    buildInputs = [ libtam ];
    makeFlags = [
      "PREFIX=$(out)"
      "LIBTAM_PREFIX=${libtam}"
    ];
    doCheck = true;
    meta = {
      license = pkgs.lib.licenses.gpl3Plus;
      mainProgram = "tam";
    };
  };
  tools = pkgs.stdenv.mkDerivation {
    pname = "tamlinux-tools";
    version = "0-unstable-${builtins.substring 0 7 sources.tamlinux-tools.rev}";
    src = sources.tamlinux-tools;
    postPatch = "patchShebangs tests";
    nativeBuildInputs = [
      pkgs.pkg-config
      pkgs.glibc.bin
    ];
    buildInputs = [
      libtam
      pkgs.dbus
    ];
    makeFlags = [
      "PREFIX=$(out)"
      "LIBTAM_PREFIX=${libtam}"
    ];
    doCheck = true;
    meta = {
      license = pkgs.lib.licenses.gpl3Plus;
      mainProgram = "tam-file-select";
    };
  };
  lib = pkgs.lib;
  product = sources.tamlinux;
  has = path: builtins.pathExists "${product}/${path}";
  productVersion = lib.trim (builtins.readFile "${product}/VERSION");
  # VERSION keeps SemVer spelling; package managers must sort letter
  # candidates before the corresponding release.
  letterVersion = builtins.match "([0-9]+\\.[0-9]+\\.[0-9]+)-([a-z]+)" productVersion;
  packageVersion = if letterVersion == null then productVersion
    else "${builtins.elemAt letterVersion 0}pre.${builtins.elemAt letterVersion 1}";
  features = {
    menu = has "desktop/menu/default.jsonc" && has "desktop/menu/tam-menu";
    protocolShadow = has "desktop/protocol-shadow";
    documentation = has "desktop/README.md";
  };
  # Hash only trial code so unrelated shell/menu commits preserve the 0.4.1
  # protocol shadow observation identity.
  protocolShadowId =
    if features.protocolShadow then
      builtins.hashString "sha256" (
        lib.concatMapStrings (path: builtins.readFile "${product}/desktop/${path}") [
          "shell/host/ProtocolState.qml"
          "shell/host/protocol_model.js"
          "shell/host/ProtocolShadow.qml"
          "shell/host/HyprlandAdapter.qml"
          "protocol-shadow"
        ]
      )
    else
      "";
  entries = dir: if has dir then builtins.readDir "${product}/${dir}" else { };
  pluginIds = lib.sort lib.lessThan (
    lib.attrNames (lib.filterAttrs (name: type: type == "directory" && lib.hasPrefix "fred." name) (entries "desktop/plugins"))
  );
  commandNames = lib.sort lib.lessThan (
    lib.attrNames (lib.filterAttrs (name: type: type == "directory" && has "commands/${name}/Makefile") (entries "commands"))
  );
  # Host session facilities (Quickshell, UWSM and xdg-terminal-exec) remain
  # independently supplied prerequisites. These helpers own their other tools
  # and resolve one another from the same command output, before user PATH.
  commandRuntimeDeps = {
    tam-notification-send = [ pkgs.jq pkgs.systemd ];
    tam-shell = [ pkgs.coreutils pkgs.gnugrep ];
    tam-menu-select = [ pkgs.perl pkgs.coreutils ];
    tam-menu-timezone = [ pkgs.systemd ];
    tam-launch-tui = [ pkgs.coreutils pkgs.util-linux ];
    tam-launch-terminal = [ pkgs.coreutils pkgs.util-linux ];
    tam-cmd-terminal-cwd = [ pkgs.coreutils pkgs.gawk pkgs.gnugrep
      pkgs.procps pkgs.jq ];
    tam-launch-editor = [ pkgs.util-linux ];
    tam-launch-config-editor = [ ];
    tam-launch-floating-terminal-with-presentation = [ pkgs.bash pkgs.util-linux pkgs.gawk ];
    tam-show-logo = [ pkgs.ncurses ];
    tam-default-editor = [ pkgs.coreutils ];
    tam-default-terminal = [ pkgs.coreutils ];
    tam-default-agent = [ pkgs.coreutils pkgs.gnugrep pkgs.mise ];
    tam-audio-output-set-default = [ pkgs.coreutils pkgs.wireplumber pkgs.pulseaudio pkgs.gawk ];
    tam-audio-output-sink = [ pkgs.pulseaudio pkgs.gawk ];
    tam-audio-sink-availability = [ pkgs.pulseaudio pkgs.gawk ];
    tam-audio-tuning = [ pkgs.coreutils pkgs.pulseaudio pkgs.gawk pkgs.gnugrep
      pkgs.gnused pkgs.diffutils pkgs.procps pkgs.systemd ];
    tam-hw-match = [ pkgs.gnugrep ];
    tam-restart-audio = [ pkgs.coreutils pkgs.systemd pkgs.wireplumber
      pkgs.gawk pkgs.gnused ];
    tam-osd = [ pkgs.jq ];
    tam-audio-output-volume = [ pkgs.coreutils pkgs.pulseaudio pkgs.gawk ];
    tam-audio-output-switch = [ pkgs.coreutils pkgs.pulseaudio pkgs.gawk pkgs.jq ];
    tam-settings-preserve = [ pkgs.python3 ];
    tam-network-status = [ pkgs.coreutils pkgs.iproute2 pkgs.networkmanager
      pkgs.iw pkgs.iputils pkgs.gawk pkgs.jq ];
    tam-network-band = [ pkgs.coreutils pkgs.networkmanager pkgs.iw pkgs.gawk pkgs.gnused ];
    tam-network-password = [ pkgs.coreutils pkgs.networkmanager ];
    tam-network-qr = [ pkgs.coreutils pkgs.networkmanager pkgs.iproute2 pkgs.gawk pkgs.qrencode ];
    tam-network-speedtest = [ pkgs.coreutils pkgs.iproute2 pkgs.curl pkgs.jq pkgs.gawk pkgs.procps ];
    # The elevated, immutable body resets PATH to native system tools.
    # Polkit, NetworkManager and resolved are native service/policy owners.
    tam-dns = [ pkgs.coreutils pkgs.networkmanager pkgs.gawk pkgs.findutils ];
    tam-restart-wifi = [ pkgs.networkmanager pkgs.util-linux ];
    tam-bluetooth-power = [ pkgs.coreutils pkgs.bluez pkgs.util-linux pkgs.gawk ];
    tam-bluetooth-device = [ pkgs.coreutils pkgs.bluez ];
    tam-restart-bluetooth = [ pkgs.util-linux ];
    tam-powerprofiles-list = [ pkgs.power-profiles-daemon pkgs.gawk pkgs.coreutils ];
    tam-powerprofiles-set = [ pkgs.power-profiles-daemon pkgs.systemd pkgs.coreutils ];
    tam-battery-status = [ pkgs.upower pkgs.gnugrep pkgs.gawk pkgs.coreutils ];
    tam-system-stats = [ pkgs.procps pkgs.gawk ];
    tam-toggle-idle = [ pkgs.coreutils ];
    tam-toggle-nightlight = [ pkgs.coreutils pkgs.procps pkgs.util-linux pkgs.gnugrep pkgs.jq ];
    tam-restart-hyprsunset = [ pkgs.procps pkgs.util-linux ];
    tam-display-text-size = [ pkgs.coreutils pkgs.gawk pkgs.gnused pkgs.gnugrep
      pkgs.procps pkgs.glib pkgs.dconf ];
    # Native Hyprland/locker/PAM, Polkit/asdcontrol and ttfx remain host boundaries.
    tam-brightness-display = [ pkgs.coreutils pkgs.jq pkgs.gawk pkgs.util-linux pkgs.brightnessctl ];
    tam-brightness-display-ddc = [ pkgs.coreutils pkgs.gawk pkgs.ddcutil ];
    tam-brightness-display-apple = [ pkgs.coreutils pkgs.gawk ];
    tam-brightness-keyboard = [ pkgs.coreutils pkgs.brightnessctl ];
    tam-brightness-keyboard-mute = [ pkgs.coreutils pkgs.brightnessctl ];
    tam-hw-display = [ pkgs.coreutils pkgs.gnugrep ];
    tam-hyprland-monitor-focused = [ pkgs.jq ];
    tam-hyprland-monitor-focused-apple = [ pkgs.jq ];
    tam-hyprland-monitor-laptop = [ pkgs.jq pkgs.coreutils ];
    tam-hyprland-monitor-external-active = [ pkgs.jq ];
    tam-hyprland-monitor-clamshell = [ pkgs.coreutils pkgs.gawk pkgs.gnused pkgs.jq ];
    tam-hyprland-monitor-internal = [ pkgs.coreutils ];
    tam-hyprland-monitor-internal-mirror = [ pkgs.coreutils pkgs.jq ];
    tam-hyprland-toggle = [ pkgs.coreutils ];
    tam-hyprland-toggle-enabled = [  ];
    tam-hyprland-toggle-disabled = [  ];
    tam-hw-clamshell = [  ];
    tam-hw-laptop-closed = [  ];
    tam-hw-external-monitors = [  ];
    tam-system-lock = [ pkgs.coreutils pkgs.procps pkgs.util-linux ];
    tam-system-sleep-lock = [ pkgs.coreutils pkgs.procps pkgs.systemd ];
    tam-system-wake = [  ];
    suspend-unless-stay-awake = [ pkgs.coreutils pkgs.procps pkgs.util-linux pkgs.gnugrep pkgs.gnused pkgs.systemd ];
    tam-launch-screensaver = [ pkgs.coreutils pkgs.procps pkgs.jq pkgs.socat ];
    tam-screensaver = [ pkgs.coreutils pkgs.procps pkgs.jq ];
    tam-toggle = [ pkgs.coreutils ];
    tam-toggle-enabled = [  ];
    tam-toggle-screensaver = [  ];
    tam-weather-location = [ pkgs.coreutils pkgs.jq pkgs.curl ];
    tam-audio-input-set-default = [ pkgs.wireplumber pkgs.pulseaudio pkgs.gawk ];
    tam-browser-command = [ pkgs.python3 ];
    tam-default-browser = [ pkgs.coreutils pkgs.xdg-utils ];
    tam-launch-browser = [ pkgs.coreutils pkgs.jq pkgs.gnugrep
      pkgs.systemd pkgs.xdg-utils ];
    tam-launch-webapp = [ pkgs.coreutils pkgs.jq pkgs.util-linux pkgs.xdg-utils ];
    tam-hyprland-focus-app = [ pkgs.jq ];
    tam-launch-or-focus = [ pkgs.bash pkgs.jq pkgs.coreutils pkgs.util-linux ];
    tam-launch-or-focus-webapp = [ ];
    tam-launch-or-focus-tui = [ pkgs.coreutils ];
    # tam-menu belongs to the shell output, at this same product revision.
    tam-agent = lib.optionals features.menu [ shell ];
    tam-plugin = [ pkgs.git pkgs.python3 pkgs.jq pkgs.coreutils
      pkgs.diffutils pkgs.findutils pkgs.gawk pkgs.gnugrep ];
    tam-qmlcache-purge = [ pkgs.coreutils pkgs.findutils ];
    tam-restart-shell = [ pkgs.systemd ];
  };
  shell =
    pkgs.runCommand "tamlinux-shell-${packageVersion}"
      {
        nativeBuildInputs = [ pkgs.bash pkgs.python3 ];
        passthru = {
          version = productVersion;
          revision = product.rev;
          deploymentSelectionRecord = true;
          inherit features protocolShadowId;
        };
      }
      ''
        mkdir -p $out/share/tamlinux $out/bin
        cp -R ${product}/desktop/shell $out/share/tamlinux/
        cp ${product}/VERSION $out/share/tamlinux/version
        printf '%s\n' ${lib.escapeShellArg product.rev} > $out/share/tamlinux/source-revision
        ${lib.optionalString features.documentation "cp ${product}/desktop/README.md $out/share/tamlinux/README.md"}
        ${lib.optionalString features.menu ''
          mkdir -p $out/share/tamlinux/menu
          cp ${product}/desktop/menu/default.jsonc $out/share/tamlinux/menu/default.jsonc
          install -m755 ${product}/desktop/menu/tam-menu $out/bin/tam-menu
        ''}
        ${lib.optionalString features.protocolShadow "install -m755 ${product}/desktop/protocol-shadow $out/bin/tam-protocol-shadow"}
        patchShebangs $out/bin
      '';
  # Plugin payloads come from the same product revision as the shell.
  plugins =
    pkgs.runCommand "tamlinux-plugins-${packageVersion}"
      {
        passthru = {
          ids = pluginIds;
          revision = product.rev;
        };
      }
      ''
        mkdir -p $out/share/tamlinux/plugins
        ${lib.concatMapStrings (id: ''
          cp -R ${product}/desktop/plugins/${id} $out/share/tamlinux/plugins/${id}
        '') pluginIds}
        chmod -R u+w $out
        find $out -name __pycache__ -type d -prune -exec rm -rf {} +
        find $out -name '*.pyc' -delete
      '';
  # Product commands: each commands/<name>/ installs bin/<name>.
  commands = pkgs.stdenv.mkDerivation {
    pname = "tamlinux-commands";
    version = packageVersion;
    src = product;
    dontConfigure = true;
    dontBuild = true;
    nativeBuildInputs = [ pkgs.makeWrapper ];
    buildInputs = [
      pkgs.bash
      pkgs.python3
    ];
    nativeCheckInputs = [
      (lib.getBin pkgs.util-linux)
      (lib.getBin pkgs.procps)
      pkgs.git
      pkgs.python3
      pkgs.jq
      pkgs.which
      pkgs.nodejs
      pkgs.perl
    ];
    doCheck = true;
    checkPhase = ''
      runHook preCheck
      patchShebangs commands
      ${lib.optionalString features.menu "patchShebangs desktop/menu/tam-menu"}
      export HOME=$TMPDIR/home
      mkdir -p $HOME
      git config --global user.email check@example.invalid
      git config --global user.name check
      git config --global init.defaultBranch main
      ${lib.concatMapStrings (name: ''
        make -C commands/${name} check
      '') commandNames}
      runHook postCheck
    '';
    installPhase = ''
      runHook preInstall
      ${lib.concatMapStrings (name: ''
        make -C commands/${name} install PREFIX=$out
      '') commandNames}
      mkdir -p $out/bin
      runHook postInstall
    '';
    postFixup = lib.concatMapStrings (name:
      lib.optionalString (lib.elem name commandNames) ''
        wrapProgram $out/bin/${name} \
          --prefix PATH : "$out/bin${lib.optionalString (commandRuntimeDeps.${name} != [ ]) ":${lib.makeBinPath commandRuntimeDeps.${name}}"}" ${lib.optionalString (name == "tam-display-text-size") "--prefix XDG_DATA_DIRS : ${pkgs.gsettings-desktop-schemas}/share/gsettings-schemas/${pkgs.gsettings-desktop-schemas.name} --prefix GIO_EXTRA_MODULES : ${pkgs.dconf.lib}/lib/gio/modules"}
      ''
    ) (lib.attrNames commandRuntimeDeps);
    passthru = {
      names = commandNames;
      revision = product.rev;
    };
    meta.license = lib.licenses.gpl3Plus;
  };
in
{
  inherit libtam tam;
  tamlinux-tools = tools;
  tamlinux-shell = shell;
  tamlinux-plugins = plugins;
  tamlinux-commands = commands;
}
