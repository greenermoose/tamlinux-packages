{ pkgs, sources }:
let
  buildSource = source: builtins.path {
    path = source;
    name = "component-source";
    filter = path: type:
      let relative = pkgs.lib.removePrefix "${source}/" (toString path);
      in !(pkgs.lib.any (prefix: relative == prefix || pkgs.lib.hasPrefix "${prefix}/" relative)
        [ ".git" ".github" "docs/ai" "docs/plans" "AI_PROVENANCE.md" "UPSTREAM.md" ]);
  };
  libtam = pkgs.stdenv.mkDerivation {
    pname = "libtam";
    version = builtins.head (builtins.match ''#define TAM_VERSION_STRING[[:space:]]+"([^"]+)"[[:space:]]*''
      (pkgs.lib.findFirst (pkgs.lib.hasPrefix "#define TAM_VERSION_STRING")
        (throw "Pinned libtam source has no version")
        (pkgs.lib.splitString "\n" (builtins.readFile "${sources.libtam}/include/tam.h"))));
    src = buildSource sources.libtam;
    nativeBuildInputs = [ pkgs.pkg-config ];
    buildInputs = [ pkgs.dbus ] ++ pkgs.lib.optionals (builtins.pathExists "${sources.libtam}/include/tam_display.h") [ pkgs.libdrm pkgs.systemd ];
    dontStrip = true;
    buildPhase = ''
      runHook preBuild
      make all ${pkgs.lib.optionalString (builtins.pathExists "${sources.libtam}/include/tam_display.h") "display session"}
      runHook postBuild
    '';
    installPhase = ''
      runHook preInstall
      make install PREFIX="$out"
      ${pkgs.lib.optionalString (builtins.pathExists "${sources.libtam}/include/tam_display.h") "make install-display install-session PREFIX=\"$out\""}
      runHook postInstall
    '';
    makeFlags = [ "PREFIX=$(out)" ];
    doCheck = true;
    meta.license = pkgs.lib.licenses.gpl3Plus;
  };
  tam = pkgs.stdenv.mkDerivation {
    dontStrip = true;
    NIX_CFLAGS_COMPILE = "-g";
    NIX_LDFLAGS = "--build-id";
    pname = "tam";
    version = builtins.head (builtins.match ''#define TAM_COMMAND_VERSION[[:space:]]+"([^"]+)"[[:space:]]*''
      (lib.findFirst (lib.hasPrefix "#define TAM_COMMAND_VERSION")
        (throw "Pinned tam source has no command version")
        (lib.splitString "\n" (builtins.readFile "${sources.tam}/src/version.h"))));
    passthru = {
      features.manWrapper = true;
      corpusVersion = lib.trim (builtins.readFile "${sources.tam}/knowledge/version");
    };
    src = buildSource sources.tam;
    postPatch = ''
      patchShebangs tests
      install -m 755 ${../../tests/tam-package-navigation.sh} tests/tam-package-navigation.sh
      patchShebangs tests/tam-package-navigation.sh
    '';
    nativeBuildInputs = [ pkgs.python3 pkgs.pkg-config pkgs.makeWrapper ];
    buildInputs = [
      libtam
      pkgs.zlib
      pkgs.ncurses
      pkgs.coreutils
      pkgs.coreutils.info
      pkgs.texinfo
      pkgs.man
      pkgs.groff
      pkgs.nix.man
    ];
    makeFlags = [
      "PREFIX=$(out)"
      "LIBTAM_PREFIX=${libtam}"
    ];
    doCheck = true;
    checkPhase = ''
      runHook preCheck
      package_root="$TMPDIR/tam-package"
      make install DESTDIR="$package_root" PREFIX=/usr LIBTAM_PREFIX=${libtam}
      tests/tam-package-navigation.sh \
        "$package_root/usr/bin/tam" \
        "$package_root/usr/share/tamlinux/knowledge" \
        "${pkgs.coreutils.info}/share/info:${pkgs.texinfo}/share/info" \
        "$package_root/usr/share/man:${pkgs.groff}/share/man:${pkgs.nix.man}/share/man" \
        "$version"
      runHook postCheck
    '';
    # makeWrapper normalizes away empty path entries; restore the final empty
    # entry after prefixing so man/Info retain their default search paths.
    postInstall = ''
      wrapProgram "$out/bin/tam" \
        --prefix PATH : ${lib.makeBinPath [ pkgs.man pkgs.groff pkgs.gzip pkgs.bzip2 pkgs.xz pkgs.zstd ]} \
        --prefix MANPATH : "$out/share/man:${pkgs.nix.man}/share/man" \
        --prefix INFOPATH : "${pkgs.coreutils.info}/share/info:${pkgs.texinfo}/share/info" \
        --run 'export MANPATH="$MANPATH:" INFOPATH="$INFOPATH:"'
    '';
    # Check the final compressed manuals through the actual wrapper, away from
    # the checkout and without the build's manual/Info search paths.
    postFixup = ''
      TAM_PACKAGE_NATURAL_ENV=1 \
      PATH=${lib.makeBinPath [ pkgs.coreutils pkgs.gnugrep ]} \
      tests/tam-package-navigation.sh \
        "$out/bin/tam" "$out/share/tamlinux/knowledge" \
        wrapped wrapped "$version"
    '';
    meta = {
      license = pkgs.lib.licenses.gpl3Plus;
      mainProgram = "tam";
    };
  };
  tools = pkgs.stdenv.mkDerivation {
    dontStrip = true;
    NIX_CFLAGS_COMPILE = "-g";
    NIX_LDFLAGS = "--build-id";
    pname = "tamlinux-tools";
    version = "0-unstable-${builtins.substring 0 7 sources.tamlinux-tools.rev}";
    src = buildSource sources.tamlinux-tools;
    postPatch = "patchShebangs tests";
    nativeBuildInputs = [
      pkgs.pkg-config
      pkgs.glibc.bin
      pkgs.git
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
  tensaku = if has "desktop/vendor/tensaku/Cargo.lock"
    then import ../native/tensaku.nix { inherit pkgs product; } else null;
  asdcontrol = if has "desktop/native/providers/asdcontrol/asdcontrol.cpp"
    then import ../native/asdcontrol.nix { inherit pkgs product; } else null;
  productVersion = lib.trim (builtins.readFile "${product}/VERSION");
  # The minor version's cultivar name (D181); products before 0.4.5 have none.
  productCultivar = if has "CULTIVAR"
    then lib.trim (builtins.readFile "${product}/CULTIVAR") else null;
  # VERSION keeps SemVer spelling; package managers must sort letter
  # candidates before the corresponding release. Plain X.Y.Z (every
  # candidate from 0.4.5) passes through unchanged; the letter mapping serves
  # the historical letter candidates.
  letterVersion = builtins.match "([0-9]+\\.[0-9]+\\.[0-9]+)-([a-z]+)" productVersion;
  packageVersion = if letterVersion == null then productVersion
    else "${builtins.elemAt letterVersion 0}pre.${builtins.elemAt letterVersion 1}";
  assemblyRoot = ../..;
  versionNotesPath = assemblyRoot + "/notes/tamlinux-${productVersion}.txt";
  deliveryRecordPath = assemblyRoot + "/deliveries/tamlinux-${productVersion}.json";
  inferredParentVersion =
    let
      parts = builtins.match "([0-9]+)\\.([0-9]+)\\.([0-9]+)" productVersion;
      patch = if parts == null then 0 else lib.toInt (builtins.elemAt parts 2);
      prev = if parts == null || patch <= 0 then null
        else "${builtins.elemAt parts 0}.${builtins.elemAt parts 1}.${toString (patch - 1)}";
    in
    if prev != null && builtins.pathExists (assemblyRoot + "/deliveries/tamlinux-${prev}.json")
    then prev else null;
  renderDeliveryNotes = delivery:
    let
      inclusions = delivery.inclusions or [ ];
      components = delivery.components or { };
      parentVer = delivery.parentVersion or inferredParentVersion;
      formatInclusion = item:
        let
          name = item.name or "component";
          versions = item.versions or null;
          ver = item.version or null;
          rev = item.revision or (if (item ? repo) && item.repo != null && (components ? ${item.repo}) then (components.${item.repo}.rev or null) else null);
          repo = item.repo or null;
          summary = item.summary or null;
          label =
            if versions != null && (versions ? command) && (versions ? corpus) then
              "${name} ${versions.command} (${versions.corpus})"
            else if ver != null then
              "${name} ${ver}"
            else
              name;
        in
        if summary != null && summary != "" then
          "- ${label}: ${summary}"
        else if label != name then
          "- ${label}"
        else if repo != null && rev != null && rev != "" then
          "- ${name} (${repo} ${builtins.substring 0 12 rev})"
        else if repo != null then
          "- ${name} (${repo})"
        else
          "- ${name}";
      componentNames = lib.filter (n: components ? ${n}) [ "libtam" "tam" "tamlinux-tools" "tamlinux" ];
      formatComponent = name:
        let
          c = components.${name};
          rev = c.rev or "";
        in
        if rev != "" then "- ${name} (${builtins.substring 0 12 rev})" else "- ${name}";
      bullets =
        if inclusions != [ ] then map formatInclusion inclusions
        else if componentNames != [ ] then map formatComponent componentNames
        else [ "- tamlinux (${builtins.substring 0 12 (product.rev or "unknown")})" ];
      header = [ "Tamlinux ${productVersion} version notes" "" ]
        ++ lib.optional (parentVer != null && parentVer != "" && parentVer != productVersion) "Changes since Tamlinux ${parentVer}:";
    in
    lib.concatStringsSep "\n" (header ++ bullets) + "\n";
  versionNotesText =
    if builtins.pathExists versionNotesPath then
      builtins.readFile versionNotesPath
    else if builtins.pathExists deliveryRecordPath then
      renderDeliveryNotes (builtins.fromJSON (builtins.readFile deliveryRecordPath))
    else
      "Tamlinux ${productVersion} version notes\n\n- tamlinux (${builtins.substring 0 12 (product.rev or "unknown")})\n";
  features = {
    menu = has "desktop/menu/default.jsonc" && has "desktop/menu/tam-menu";
    protocolShadow = has "desktop/protocol-shadow";
    documentation = has "desktop/README.md";
    sessionProviders = has "desktop/session/providers.json";
    consoleDesktop = has "desktop/session/console.py" && has "desktop/session/desktop";
    consoleWelcome = has "desktop/session/console-welcome.py";
    graphicsEnvironmentIsolation = has "desktop/shell/graphics-environment-isolation-v1";
    userDefaults = has "desktop/user-defaults/apply";
    agentSkills = has "desktop/skills/manage.py";
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
  englishOcr = pkgs.tesseract.override { enableLanguages = [ "eng" ]; };
  captureTools = {
    grim = "${pkgs.grim}/bin/grim";
    slurp = "${pkgs.slurp}/bin/slurp";
    hyprpicker = "${pkgs.hyprpicker}/bin/hyprpicker";
    gpu-screen-recorder = "/usr/bin/gpu-screen-recorder";
    wl-copy = "${pkgs.wl-clipboard}/bin/wl-copy";
    tesseract = "${englishOcr}/bin/tesseract";
    englishData = "${englishOcr}/share/tessdata/eng.traineddata";
    zbarimg = "${pkgs.zbar}/bin/zbarimg";
    v4l2-ctl = "${pkgs.v4l-utils}/bin/v4l2-ctl";
    mpv = "${mpvWithGraphics}/bin/mpv";
    ffmpeg = "${lib.getBin pkgs.ffmpeg}/bin/ffmpeg";
    ffprobe = "${lib.getBin pkgs.ffmpeg}/bin/ffprobe";
  };
  # Outline-preserving font rename: build input retains ancestry, installed
  # font advertises only the owned family and PostScript identities.
  themeFontPython = pkgs.python3.withPackages (python: [ python.fonttools ]);
  themeTools = [ pkgs.coreutils pkgs.python3 pkgs.gawk pkgs.gnused pkgs.gnugrep
    pkgs.findutils pkgs.util-linux pkgs.procps pkgs.jq pkgs.dconf ];
  withNixGraphics = import ./nix-graphics.nix { inherit pkgs; };
  mpvWithGraphics = withNixGraphics { package = pkgs.mpv; programs = [ "mpv" ]; };
  commandRuntimeDeps = {
    tam-dev =[ pkgs.python3 pkgs.git pkgs.gnumake pkgs.coreutils pkgs.systemd ];
    tam-desktop-test = [ pkgs.python3 pkgs.wl-clipboard pkgs.libnotify pkgs.util-linux pkgs.systemd ];
    start = [ ];
    tam-macro = [ pkgs.python3 pkgs.wl-clipboard ];
    tam-nut = [ pkgs.coreutils pkgs.gawk pkgs.util-linux pkgs.pciutils ];
    tam-theme-set = themeTools;
    tam-theme-journal = themeTools;
    tam-theme-refresh = themeTools;
    tam-theme-init = themeTools;
    tam-session-init = [ pkgs.python3 pkgs.coreutils ];
    tam-desktop-mode = [ pkgs.python3 pkgs.coreutils ];
    tam-migrate-desktop = [ pkgs.desktop-file-utils (pkgs.python3.withPackages (python: [ python.json5 ])) pkgs.coreutils pkgs.dconf pkgs.systemd pkgs.pulseaudio ];
    tam-theme-current = themeTools;
    tam-theme-list = themeTools;
    tam-theme-remove = themeTools;
    tam-theme-install = themeTools ++ [ pkgs.git pkgs.gum ];
    tam-theme-switcher = themeTools;
    tam-theme-bg-set = themeTools;
    tam-theme-bg-next = themeTools;
    tam-theme-bg-install = themeTools ++ [ pkgs.xdg-utils ];
    tam-theme-bg-switcher = themeTools;
    tam-theme-color = themeTools;
    tam-theme-colors-from-alacritty = themeTools;
    tam-theme-set-templates = themeTools;
    tam-theme-osc = themeTools;
    tam-theme-set-foot = themeTools;
    tam-theme-set-tmux = themeTools ++ [ pkgs.tmux ];
    tam-theme-set-gnome = themeTools ++ [ pkgs.glib ];
    tam-theme-set-browser = themeTools;
    tam-theme-set-pi = themeTools;
    tam-theme-set-claude = themeTools;
    tam-theme-set-t3code = themeTools;
    tam-theme-set-vscode = themeTools;
    tam-theme-set-obsidian = themeTools;
    tam-theme-set-keyboard = themeTools;
    tam-theme-set-keyboard-asus-rog = themeTools;
    tam-theme-set-keyboard-f16 = themeTools;
    tam-font-set = themeTools ++ [ pkgs.fontconfig ];
    tam-font-list = themeTools ++ [ pkgs.fontconfig ];
    tam-font-current = themeTools ++ [ pkgs.fontconfig ];
    tam-install-font = themeTools;
    tam-pkg-add = themeTools;
    tam-pkg-present = themeTools;
    tam-pkg-missing = themeTools;
    tam-branding-about = themeTools;
    tam-transcode-ascii = themeTools ++ [ pkgs.imagemagick ];
    tam-launch-about = themeTools ++ [ pkgs.fastfetch ];
    tam-hook = themeTools;
    tam-menu-images = themeTools ++ [ pkgs.vips ];
    tam-restart-terminal = themeTools;
    tam-restart-hyprctl = themeTools;
    tam-restart-btop = themeTools;
    tam-restart-opencode = themeTools;
    tam-restart-helix = themeTools;

    tam-notification-send = [ pkgs.jq pkgs.systemd ];
    tam-audio-input-mute = [ pkgs.wireplumber pkgs.gnugrep ];
    tam-audio-source-switch = [ ];
    tam-battery-low = [ ];
    tam-notification-battery = [ ];
    tam-notification-time = [ pkgs.coreutils ];
    tam-hardware = [ ];
    tam-meter = [ ];
    tam-boot = [ (lib.getBin pkgs.systemd) ];
    tam-open = [
      (withNixGraphics { package = pkgs.zathura; programs = [ "zathura" ]; })
      (withNixGraphics { package = pkgs.imv; programs = [ "imv" "imv-wayland" "imv-x11" ]; })
      mpvWithGraphics
      pkgs.micro pkgs.hexyl pkgs.hexedit pkgs.p7zip pkgs.poppler-utils pkgs.less pkgs.lynx pkgs.coreutils pkgs.libarchive ];
    tam-hw-touchpad = [ pkgs.jq ];
    tam-hw-touchscreen = [ pkgs.jq ];
    tam-hw-laptop = [ ];
    tam-hw-fingerprint = [ pkgs.coreutils ];
    tam-hw-hybrid-gpu = [ pkgs.pciutils pkgs.gnugrep ];
    tam-hw-dell-xps-haptic-touchpad = [ ];
    tam-hyprland-window-close-all = [ pkgs.jq ];
    tam-hyprland-window-pop = [ pkgs.jq ];
    tam-hyprland-window-tiled-fullscreen-toggle = [ pkgs.jq ];
    tam-hyprland-window-transparency-toggle = [ pkgs.jq ];
    tam-hyprland-window-gaps-toggle = [ ];
    tam-hyprland-window-single-square-aspect-toggle = [ ];
    tam-hyprland-workspace-layout-toggle = [ pkgs.jq pkgs.coreutils ];
    tam-hyprland-window-width = [ pkgs.jq pkgs.coreutils ];
    tam-toggle-notification-silencing = [ ];
    tam-toggle-input-device = [ pkgs.coreutils ];
    tam-menu-keybindings = [ pkgs.lua pkgs.jq pkgs.coreutils ];
    tam-menu-tmux-keybindings = [ pkgs.coreutils pkgs.gnugrep pkgs.gawk pkgs.jq pkgs.tmux ];
    tam-menu-herdr-keybindings = [ pkgs.coreutils pkgs.gnugrep pkgs.gawk pkgs.jq ];
    tam-reminder = [ pkgs.coreutils pkgs.systemd pkgs.jq pkgs.gawk pkgs.gnugrep pkgs.findutils ];
    tam-disk-speedtest = [ pkgs.coreutils pkgs.gawk pkgs.jq pkgs.findutils pkgs.util-linux ];
    tam-system-lid-close = [ ];
    tam-system-logout = [ pkgs.coreutils pkgs.bash ];
    tam-system-reboot = [ pkgs.coreutils pkgs.systemd ];
    tam-system-shutdown = [ pkgs.coreutils pkgs.systemd ];
    tam-restart-xcompose = [ pkgs.systemd ];
    tam-hyprland-monitor-watch = [ pkgs.coreutils pkgs.util-linux pkgs.socat ];
    tam-hyprland-monitor-modeless = [ pkgs.jq ];
    tam-hyprland-reload-guard = [ pkgs.coreutils pkgs.jq ];
    tam-drive-password = [ pkgs.coreutils pkgs.util-linux pkgs.gum ];
    tam-drive-select = [ pkgs.coreutils pkgs.gum pkgs.gawk pkgs.util-linux pkgs.gnugrep ];
    tam-drive-info = [ pkgs.coreutils pkgs.gnused pkgs.gawk pkgs.util-linux ];
    tam-hibernation-available = [ pkgs.coreutils pkgs.gawk ];
    tam-hyprland-monitor-scaling = [ pkgs.coreutils pkgs.jq pkgs.gawk pkgs.gnused pkgs.gnugrep pkgs.procps pkgs.python3 ];
    tam-launch-docker-tui = [  ];
    tam-menu-share = [ pkgs.coreutils ];
    tam-pkg-aur-install = [ pkgs.fzf pkgs.coreutils pkgs.gnused pkgs.yay ];
    tam-pkg-install = [ pkgs.fzf pkgs.gawk ];
    tam-pkg-remove = [ pkgs.fzf pkgs.coreutils ];
    tam-pkg-drop = [  ];
    tam-sudo-keepalive = [ pkgs.coreutils ];
    tam-remove-security-fido2 = [ pkgs.coreutils pkgs.gnugrep pkgs.gnused ];
    tam-remove-security-fingerprint = [ pkgs.coreutils pkgs.gnugrep pkgs.gnused ];
    tam-remove-security-sshd = [ pkgs.coreutils pkgs.gum ];
    tam-remove-security-sudoless-docker = [ pkgs.coreutils pkgs.gum ];
    tam-restart-trackpad = [ pkgs.coreutils pkgs.gnugrep pkgs.kmod ];
    tam-setup-security-fido2 = [ pkgs.coreutils pkgs.gnugrep pkgs.gnused ];
    tam-setup-security-fingerprint = [ pkgs.coreutils pkgs.gnugrep pkgs.gnused ];
    tam-setup-security-sshd = [ pkgs.coreutils pkgs.gnugrep pkgs.openssh pkgs.curl pkgs.gum ];
    tam-setup-security-sudoless-docker = [ pkgs.coreutils pkgs.gum ];
    tam-sudo-docker = [ pkgs.coreutils pkgs.gnugrep ];
    tam-sudo-passwordless = [ pkgs.coreutils pkgs.gum ];
    tam-toggle-crash-capture = [ pkgs.systemd ];
    tam-crash-watch = [ pkgs.coreutils pkgs.systemd pkgs.jq pkgs.gnugrep ];
    tam-notification-wait = [ pkgs.coreutils pkgs.systemd ];
    tam-agent-crash = [ pkgs.coreutils pkgs.systemd ];
    tam-toggle-hybrid-gpu = [ pkgs.coreutils pkgs.gnugrep pkgs.gnused pkgs.gum ];
    tam-transcode = [ pkgs.coreutils pkgs.file pkgs.imagemagick pkgs.ffmpeg pkgs.wl-clipboard ];
    tam-menu-file = [ pkgs.coreutils pkgs.findutils ];
    tam-tui-install = [ pkgs.coreutils pkgs.gnused pkgs.curl pkgs.gum pkgs.gtk3 ];
    tam-tui-remove = [ pkgs.coreutils pkgs.gnused pkgs.gnugrep pkgs.findutils ];
    tam-update-time = [  ];
    tam-update = [ pkgs.coreutils pkgs.python3 pkgs.yay ];
    tam-update-firmware = [ pkgs.coreutils pkgs.python3 ];
    tam-webapp-install = [ pkgs.coreutils pkgs.gnused pkgs.gnugrep pkgs.curl pkgs.gum pkgs.gtk3 ];
    tam-webapp-remove = [ pkgs.coreutils pkgs.gnused pkgs.gnugrep pkgs.findutils pkgs.desktop-file-utils ];
    tam-remove-launcher-entry = [ pkgs.coreutils pkgs.gnused pkgs.gnugrep pkgs.desktop-file-utils ];
    # Capture tools are delivered; compositor, portal/device policy and native
    # Tensaku remain explicit host capabilities. English OCR data is immutable.
    tam-capture-region = [ pkgs.coreutils pkgs.procps pkgs.jq pkgs.slurp pkgs.hyprpicker ];
    tam-capture-screenshot = [ pkgs.coreutils pkgs.procps pkgs.jq pkgs.grim pkgs.wl-clipboard ];
    tam-capture-text = [ pkgs.coreutils pkgs.hyprpicker pkgs.slurp pkgs.grim
      pkgs.wl-clipboard englishOcr ];
    tam-capture-qr = [ pkgs.coreutils pkgs.hyprpicker pkgs.slurp pkgs.grim pkgs.wl-clipboard pkgs.zbar ];
    tam-capture-screenrecording = [ pkgs.coreutils pkgs.util-linux pkgs.jq
      pkgs.gnugrep pkgs.gnused pkgs.v4l-utils mpvWithGraphics pkgs.ffmpeg ];
    tam-capture-screenrecording-with-webcam = [ ];
    tam-capture-webcam-list = [ pkgs.v4l-utils pkgs.gawk ];
    tam-capture-webcam-resize = [ pkgs.jq ];
    tam-capture-edit = [ pkgs.wl-clipboard ];

    tam-shell = [ pkgs.python3 pkgs.coreutils pkgs.gnugrep ];
    tam-menu-select = [ pkgs.perl pkgs.coreutils ];
    tam-menu-timezone = [ pkgs.systemd ];
    tam-launch-tui = [ pkgs.coreutils pkgs.util-linux ];
    tam-launch-terminal = [ pkgs.coreutils pkgs.util-linux ];
    tam-launch-nautilus = [ pkgs.coreutils pkgs.util-linux ];
    tam-launch-nautilus-cwd = [ pkgs.coreutils pkgs.util-linux ];
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
    tam-display-text-size = [ pkgs.python3 pkgs.coreutils pkgs.gawk pkgs.gnused pkgs.gnugrep
      pkgs.procps pkgs.glib pkgs.dconf ];
    # Text-console ioctls need no compositor; DDC/hw siblings supply their own tools.
    tam-monitor = (lib.optional (!(has "commands/tam-monitor/native.c")) pkgs.python3) ++ [ pkgs.brightnessctl ];
    # Native Hyprland/locker/PAM, Polkit/asdcontrol remain host boundaries.
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
    tam-toggle = [ pkgs.coreutils ];
    tam-toggle-enabled = [  ];
    tam-weather-location = [ pkgs.coreutils pkgs.jq pkgs.curl ];
    tam-audio-input-set-default = [ pkgs.wireplumber pkgs.pulseaudio pkgs.gawk ];
    tam-browser-command = [ pkgs.python3 ];
    tam-chromium-copy-url-host = [ pkgs.coreutils pkgs.python3 pkgs.wl-clipboard ];
    tam-chromium-ytdlp-host = [ pkgs.bash pkgs.python3 pkgs.yt-dlp pkgs.ffmpeg mpvWithGraphics
      pkgs.coreutils pkgs.jq ];
    tam-default-browser = [ pkgs.coreutils pkgs.xdg-utils ];
    tam-launch-browser = [ pkgs.coreutils pkgs.jq pkgs.gnugrep
      pkgs.systemd pkgs.xdg-utils ];
    tam-launch-webapp = [ pkgs.coreutils pkgs.jq pkgs.util-linux pkgs.xdg-utils ];
    tam-webapp-handler-zoom = [ pkgs.coreutils pkgs.gnused ];
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
  shellRuntimeDeps = [ pkgs.coreutils pkgs.findutils pkgs.gnugrep pkgs.gawk
    pkgs.jq pkgs.perl pkgs.util-linux pkgs.procps pkgs.systemd pkgs.wl-clipboard
    pkgs.wtype pkgs.inotify-tools pkgs.xdg-utils pkgs.python3 ];
  # Content-addressed shell tree: candidate VERSION/CULTIVAR stamps stay out so
  # VERSION-only bumps reuse this payload (A3).
  shellPayloadSource = builtins.path {
    path = product;
    name = "tamlinux-shell-payload-source";
    filter = path: type:
      let relative = lib.removePrefix ((toString product) + "/") (toString path);
      in toString path == toString product
        || relative == "desktop"
        || relative == "share"
        || relative == "LICENSE"
        || lib.any (prefix: relative == prefix || lib.hasPrefix "${prefix}/" relative) [
          "desktop/shell" "desktop/session" "desktop/skills" "desktop/menu"
          "desktop/protocol-shadow" "desktop/user-defaults" "desktop/README.md"
          "share/nftables"
        ];
  };
  shellPayload =
    pkgs.runCommand "tamlinux-shell-payload-1"
      {
        nativeBuildInputs = [ pkgs.bash pkgs.python3 pkgs.makeWrapper ];
        passthru = {
          deploymentSelectionRecord = true;
          inherit features protocolShadowId;
          runtimePath = lib.makeBinPath shellRuntimeDeps;
        };
      }
      ''
        mkdir -p $out/share/tamlinux $out/bin
        cp -R ${shellPayloadSource}/desktop/shell $out/share/tamlinux/
        chmod -R u+w $out/share/tamlinux/shell
        ${lib.optionalString features.consoleWelcome ''
          mkdir -p $out/share/tamlinux/console
          python3 ${shellPayloadSource}/desktop/session/console-welcome.py > $out/share/tamlinux/console/welcome-generic.issue
        ''}
        ${lib.optionalString features.agentSkills ''
          cp -R ${shellPayloadSource}/desktop/skills $out/share/tamlinux/skills
        ''}
        ${lib.optionalString features.documentation "cp ${shellPayloadSource}/desktop/README.md $out/share/tamlinux/README.md"}
        ${lib.optionalString features.sessionProviders ''
          cp -R ${shellPayloadSource}/desktop/session $out/share/tamlinux/session
          install -m755 ${shellPayloadSource}/desktop/session/start $out/bin/tam-hyprland-session
          ${lib.optionalString features.consoleDesktop "install -m755 ${shellPayloadSource}/desktop/session/desktop $out/bin/tam-desktop"}
          chmod +x $out/share/tamlinux/session/Hyprland
          mkdir -p $out/share/tamlinux/nftables
          cp -R ${shellPayloadSource}/share/nftables/. $out/share/tamlinux/nftables/
        ''}
        ${lib.optionalString features.menu ''
          mkdir -p $out/share/tamlinux/menu
          cp ${shellPayloadSource}/desktop/menu/default.jsonc $out/share/tamlinux/menu/default.jsonc
          install -m755 ${shellPayloadSource}/desktop/menu/tam-menu $out/bin/tam-menu
        ''}
        ${lib.optionalString features.protocolShadow "install -m755 ${shellPayloadSource}/desktop/protocol-shadow $out/bin/tam-protocol-shadow"}
        ${lib.optionalString features.userDefaults ''
          mkdir -p $out/share/tamlinux/user-defaults
          cp -R ${shellPayloadSource}/desktop/user-defaults/bash ${shellPayloadSource}/desktop/user-defaults/gnupg $out/share/tamlinux/user-defaults/
          install -m644 ${shellPayloadSource}/desktop/user-defaults/apply ${shellPayloadSource}/desktop/user-defaults/LICENSE-bash $out/share/tamlinux/user-defaults/
        ''}
        patchShebangs $out/bin $out/share/tamlinux/shell
        for script in $out/share/tamlinux/shell/services/*/*.sh; do
          test -f "$script" || continue
          wrapProgram "$script" --prefix PATH : ${lib.makeBinPath shellRuntimeDeps}
        done
      '';
  shell =
    pkgs.runCommand "tamlinux-shell-${packageVersion}"
      {
        nativeBuildInputs = lib.optional features.consoleWelcome pkgs.python3;
        passthru = shellPayload.passthru // {
          version = productVersion;
          cultivar = productCultivar;
          revision = product.rev;
          payload = shellPayload;
        };
      }
      ''
        cp -a ${shellPayload}/. $out/
        chmod -R u+w $out
        printf '%s\n' ${lib.escapeShellArg productVersion} > $out/share/tamlinux/version
        printf '%s' ${lib.escapeShellArg versionNotesText} > $out/share/tamlinux/version-notes.txt
        chmod 644 $out/share/tamlinux/version-notes.txt
        ${lib.optionalString (productCultivar != null) "printf '%s\\n' ${lib.escapeShellArg productCultivar} > $out/share/tamlinux/cultivar"}
        printf '%s\n' ${lib.escapeShellArg product.rev} > $out/share/tamlinux/source-revision
        ${lib.optionalString features.consoleWelcome ''
          python3 ${shellPayloadSource}/desktop/session/console-welcome.py ${lib.optionalString (productCultivar != null) "--cultivar ${lib.escapeShellArg productCultivar} --version ${lib.escapeShellArg productVersion}"} > $out/share/tamlinux/console/welcome.issue
        ''}
      '';
  pluginsPayloadSource = builtins.path {
    path = product;
    name = "tamlinux-plugins-payload-source";
    filter = path: type:
      let relative = lib.removePrefix ((toString product) + "/") (toString path);
      in toString path == toString product
        || relative == "desktop"
        || relative == "desktop/plugins"
        || lib.any (id: relative == "desktop/plugins/${id}" || lib.hasPrefix "desktop/plugins/${id}/" relative) pluginIds;
  };
  pluginsPayload =
    pkgs.runCommand "tamlinux-plugins-payload-1"
      {
        passthru = { ids = pluginIds; };
      }
      ''
        mkdir -p $out/share/tamlinux/plugins
        ${lib.concatMapStrings (id: ''
          cp -R ${pluginsPayloadSource}/desktop/plugins/${id} $out/share/tamlinux/plugins/${id}
        '') pluginIds}
        chmod -R u+w $out
        find $out -name __pycache__ -type d -prune -exec rm -rf {} +
        find $out -name '*.pyc' -delete
      '';
  plugins =
    pkgs.runCommand "tamlinux-plugins-${packageVersion}"
      {
        passthru = pluginsPayload.passthru // {
          revision = product.rev;
          payload = pluginsPayload;
        };
      }
      ''
        cp -a ${pluginsPayload}/. $out/
      '';
  commandSource = name: builtins.path {
    path = product;
    name = "${name}-source";
    filter = path: type:
      let relative = lib.removePrefix ((toString product) + "/") (toString path);
      in toString path == toString product || relative == "commands" || relative == "commands/${name}"
        || relative == "LICENSE" || lib.hasPrefix "commands/${name}/" relative;
  };
  # Checks that need desktop/ fixtures beside commands/<name> (inventory 2026-11-04).
  desktopCheckNames = [
    "suspend-unless-stay-awake"
    "tam-audio-tuning"
    "tam-capture-region"
    "tam-capture-screenrecording-with-webcam"
    "tam-desktop-mode"
    "tam-desktop-test"
    "tam-display-text-size"
    "tam-menu-images"
    "tam-migrate-desktop"
    "tam-notification-send"
    "tam-plugin"
    "tam-powerprofiles-set"
    "tam-session-init"
    "tam-shell"
    "tam-system-lock"
    "tam-system-sleep-lock"
    "tam-theme-set"
    "tam-work"
  ];
  extraCheckCommands = {
    tam-dev = [ "tam-demo" "tam-macro" "tam-menu-keybindings" "tam-sibling" ];
    tam-browser-command = [
      "tam-default-browser" "tam-launch-browser" "tam-launch-webapp"
      "tam-hyprland-focus-app" "tam-launch-or-focus" "tam-launch-or-focus-webapp"
      "tam-launch-or-focus-tui" "tam-launch-tui" "tam-notification-send"
      "tam-settings-preserve"
    ];
    tam-launch-terminal = [
      "tam-cmd-present" "tam-cmd-terminal-cwd" "tam-default-editor" "tam-default-terminal"
      "tam-launch-config-editor" "tam-launch-editor"
      "tam-launch-floating-terminal-with-presentation" "tam-launch-tui"
      "tam-notification-send" "tam-settings-preserve" "tam-show-done" "tam-show-logo"
    ];
    tam-capture-region = [
      "tam-capture-edit"
      "tam-capture-qr"
      "tam-capture-screenrecording"
      "tam-capture-screenrecording-with-webcam"
      "tam-capture-screenshot"
      "tam-capture-text"
      "tam-capture-webcam-list"
      "tam-capture-webcam-resize"
    ];
    tam-theme-set = [
      "tam-theme-bg-install"
      "tam-theme-bg-next"
      "tam-theme-bg-set"
      "tam-theme-bg-switcher"
      "tam-theme-color"
      "tam-theme-colors-from-alacritty"
      "tam-theme-current"
      "tam-theme-init"
      "tam-theme-install"
      "tam-theme-journal"
      "tam-theme-list"
      "tam-theme-osc"
      "tam-theme-payload"
      "tam-theme-refresh"
      "tam-theme-remove"
      "tam-theme-set-browser"
      "tam-theme-set-claude"
      "tam-theme-set-foot"
      "tam-theme-set-gnome"
      "tam-theme-set-keyboard"
      "tam-theme-set-keyboard-asus-rog"
      "tam-theme-set-keyboard-f16"
      "tam-theme-set-obsidian"
      "tam-theme-set-pi"
      "tam-theme-set-t3code"
      "tam-theme-set-templates"
      "tam-theme-set-tmux"
      "tam-theme-set-vscode"
      "tam-theme-switcher"
    ];
    tam-update = [ "tam-update-firmware" ];
  };
  # Multi-command integrators need commands+desktop (646880e). Keep them on a
  # filtered tree that omits VERSION/docs so candidate stamps do not rebuild
  # these checks (0.6.9 speed recovery without the empty-list breakage).
  fullProductCheckNames = [
    "tam-shell"
    "tam-theme-set"
    "tam-launch-terminal"
    "tam-browser-command"
    "tam-capture-region"
  ];
  checkSource = name: builtins.path {
    path = product;
    name = "${name}-check-source";
    filter = path: type:
      let
        relative = lib.removePrefix ((toString product) + "/") (toString path);
        extras = extraCheckCommands.${name} or [ ];
        allowCommand = cmd:
          relative == "commands/${cmd}" || lib.hasPrefix "commands/${cmd}/" relative;
        productTree =
          toString path == toString product
          || relative == "LICENSE"
          || relative == "commands" || lib.hasPrefix "commands/" relative
          || relative == "desktop" || lib.hasPrefix "desktop/" relative
          || relative == "share" || lib.hasPrefix "share/" relative;
      in if lib.elem name fullProductCheckNames then productTree
      else toString path == toString product
        || relative == "LICENSE"
        || relative == "commands"
        || allowCommand name
        || lib.any allowCommand extras
        || (lib.elem name desktopCheckNames && (
          relative == "desktop" || lib.hasPrefix "desktop/" relative
        ));
  };
  simpleSyntaxCheck = name:
    let text = builtins.readFile "${product}/commands/${name}/Makefile";
        parts = lib.splitString "\ncheck:\n" text;
        block = if lib.length parts == 2 then lib.trim (builtins.head (lib.splitString "\n\n" (builtins.elemAt parts 1))) else "";
    in block == "bash -n ${name}" && !(lib.hasInfix "include" text) && !(lib.hasInfix "$(shell" text);
  needsDesktopFixtures = name: lib.elem name desktopCheckNames || lib.elem name fullProductCheckNames;
  # nativeNames must precede commandChecks (subtractLists).
  nativeNames = lib.filter (name:
    has "commands/${name}/native.c"
    || (name == "tam-hardware" && has "commands/${name}/Makefile")
    || (name == "tam-open" && has "commands/${name}/Makefile")
    || (name == "start" && has "commands/start/Makefile")
    || (name == "tam-meter" && has "commands/${name}/Makefile")
    || (name == "tam-boot" && has "commands/${name}/Makefile")
  ) [ "tam-monitor" "tam-hardware" "tam-open" "start" "tam-meter" "tam-boot" ];
  commandChecks = lib.genAttrs (lib.subtractLists nativeNames commandNames) (name: pkgs.stdenv.mkDerivation {
    pname = "${name}-checks";
    version = "1";
    src = checkSource name;
    nativeBuildInputs = [ pkgs.bash pkgs.python3 pkgs.git pkgs.jq pkgs.which pkgs.nodejs pkgs.perl pkgs.lua
      pkgs.pkg-config (lib.getBin pkgs.util-linux) (lib.getBin pkgs.procps) ];
    dontConfigure = true;
    buildPhase = "true";
    doCheck = true;
    checkPhase = ''
      patchShebangs commands
      ${lib.optionalString (name == "tam-macro") "export TAMLINUX_XKBCOMMON=${lib.getLib pkgs.libxkbcommon}/lib/libxkbcommon.so.0"}
      ${lib.optionalString (has "desktop/widget-proof" && needsDesktopFixtures name) "patchShebangs desktop/widget-proof"}
      ${lib.optionalString (features.menu && needsDesktopFixtures name) "patchShebangs desktop/menu/tam-menu"}
      export HOME=$TMPDIR/home
      mkdir -p $HOME
      git config --global user.email check@example.invalid
      git config --global user.name check
      git config --global init.defaultBranch main
      make -C commands/${name} check
    '';
    installPhase = "touch $out";
  });
  nativePayload = name: pkgs.stdenv.mkDerivation {
    pname = "${name}-payload";
    version = "1";
    NIX_LDFLAGS = "--build-id";
    src = commandSource name;
    nativeBuildInputs = [ pkgs.pkg-config pkgs.python3 pkgs.bash ];
    buildInputs = [ libtam ]
      ++ lib.optionals (name == "tam-monitor") [ pkgs.systemd pkgs.libdrm ]
      ++ lib.optionals (name == "tam-hardware") [ pkgs.libcpuid ]
      ++ lib.optionals (name == "tam-open") [ pkgs.file ];
    dontStrip = true;
    buildPhase = "make -C commands/${name} LIBTAM_PREFIX=${libtam}";
    doCheck = true;
    checkPhase = ''
      patchShebangs commands
      ${lib.optionalString (name == "tam-monitor") ''
        substituteInPlace commands/tam-monitor/tests/test_monitor.py \
          --replace-fail '/usr/bin:/bin' '${pkgs.coreutils}/bin' \
          --replace-fail '    def test_installed_command_metadata_without_desktop(self):' \
            $'    @unittest.skipUnless(Path("/sys/class/drm").is_dir(), "requires host sysfs; tested outside the Nix sandbox")\n    def test_installed_command_metadata_without_desktop(self):'
      ''}
      make -C commands/${name} check LIBTAM_PREFIX=${libtam}
    '';
    installPhase = "make -C commands/${name} install PREFIX=$out LIBTAM_PREFIX=${libtam}";
  };
  nativePayloads = lib.genAttrs nativeNames nativePayload;
  # Desktop trees command installs and the payload installPhase actually copy.
  # Keep this allowlist (not full desktop/): session/hypr looknfeel edits must
  # not rebuild the commands payload. Do not drop audio/lock/migration/theme.
  commandsDesktopAllow = [
    "desktop/assets"
    "desktop/audio"
    "desktop/browser"
    "desktop/lock"
    "desktop/migration"
    "desktop/theme"
    "desktop/session/initialize.py"
    "desktop/test-battery"
    "desktop/virtual_input.py"
    "desktop/plugins/fred.workspaces"
    "desktop/shell/host"
  ];
  commandsPayloadSource = builtins.path {
    path = product;
    name = "tamlinux-commands-payload-source";
    filter = path: type:
      let relative = lib.removePrefix ((toString product) + "/") (toString path);
          # Allow listed trees, their descendants, and parent dirs Nix must
          # traverse (e.g. desktop/plugins for fred.workspaces).
          allowDesktop = prefix:
            relative == prefix
            || lib.hasPrefix (prefix + "/") relative
            || lib.hasPrefix (relative + "/") prefix;
      in toString path == toString product
        || relative == "LICENSE"
        || relative == "commands" || lib.hasPrefix "commands/" relative
        || relative == "desktop"
        || lib.any allowDesktop commandsDesktopAllow;
  };
  commandsPayload = pkgs.stdenv.mkDerivation {
    NIX_LDFLAGS = "--build-id";
    pname = "tamlinux-commands-payload";
    version = "1";
    src = commandsPayloadSource;
    dontConfigure = true;
    dontStrip = true;
    nativeBuildInputs = [ pkgs.makeWrapper themeFontPython pkgs.pkg-config ];
    buildPhase = ''
      runHook preBuild
      runHook postBuild
    '';
    buildInputs = [
      pkgs.bash
      pkgs.python3
    ] ++ lib.optionals (has "commands/tam-monitor/native.c") [ libtam pkgs.systemd pkgs.libdrm ]
      ++ lib.optionals (has "commands/tam-hardware/Makefile") [ libtam pkgs.libcpuid ]
      ++ lib.optionals (has "commands/start/Makefile") [ libtam ];
    makeFlags = lib.optional (
      has "commands/tam-monitor/native.c"
      || has "commands/tam-hardware/Makefile"
      || has "commands/start/Makefile"
    ) "LIBTAM_PREFIX=${libtam}";
    preBuild = ''
      for check in ${lib.concatStringsSep " " (map toString (builtins.attrValues commandChecks))}; do
        test -e "$check"
      done
    '';
    doCheck = false;
    installPhase = ''
      runHook preInstall
      ${lib.concatMapStrings (name: ''
        make -C commands/${name} install PREFIX=$out ${lib.optionalString (
          (name == "tam-monitor" && has "commands/tam-monitor/native.c")
          || name == "tam-hardware"
          || name == "start"
        ) "LIBTAM_PREFIX=${libtam}"}
      '') (lib.subtractLists nativeNames commandNames)}
      ${lib.concatMapStrings (name: "cp -R ${nativePayloads.${name}}/. $out/\nchmod -R u+w $out\n") nativeNames}
      mkdir -p $out/bin
      ${lib.optionalString (has "desktop/browser/native_host.py") ''
        mkdir -p $out/share/tamlinux
        cp -R desktop/browser $out/share/tamlinux/browser
        chmod -R u+w $out/share/tamlinux/browser
        patchShebangs $out/share/tamlinux/browser/download-worker
      ''}
      ${lib.optionalString (tensaku != null || asdcontrol != null) ''
        mkdir -p $out/share/tamlinux
        cp ${pkgs.writeText "tamlinux-provider-tools.json" (builtins.toJSON ({}
          // lib.optionalAttrs (tensaku != null) { tensaku = "${tensaku}/bin/tensaku"; }
          // lib.optionalAttrs (asdcontrol != null) { asdcontrol = "${asdcontrol}/bin/asdcontrol"; }))} $out/share/tamlinux/provider-tools.json
      ''}
      ${lib.optionalString (has "desktop/assets") ''
        mkdir -p $out/share/tamlinux
        cp -R desktop/assets $out/share/tamlinux/assets
        chmod -R u+w $out/share/tamlinux/assets
        mkdir -p $out/share/fonts/truetype
        ${themeFontPython}/bin/python3 desktop/theme/rename-font.py \
          desktop/assets/fonts/source.ttf $out/share/fonts/truetype/TamlinuxIcons.ttf
        rm $out/share/tamlinux/assets/fonts/source.ttf
        find $out/share/tamlinux/assets/themes -name vscode.json -delete
        cp -R ${pkgs.nerd-fonts.jetbrains-mono}/share/fonts/. $out/share/fonts/
        chmod -R u+w $out/share/fonts
        cp -R ${pkgs.atkinson-hyperlegible}/share/fonts/. $out/share/fonts/
        chmod -R u+w $out/share/fonts
        cp -R ${pkgs.nerd-fonts.atkynson-mono}/share/fonts/. $out/share/fonts/
        cp desktop/assets/LICENSE-omarchy $out/share/tamlinux/assets/fonts/LICENSE
        ${lib.optionalString (has "desktop/assets/icons/tamlinux-discord.png") ''
          install -Dm644 desktop/assets/icons/tamlinux-discord.png \
            $out/share/icons/hicolor/256x256/apps/tamlinux-discord.png
        ''}
      ''}
      ${lib.optionalString (lib.elem "tam-capture-region" commandNames) ''
        mkdir -p $out/share/tamlinux
        cp ${pkgs.writeText "tamlinux-capture-tools.json" (builtins.toJSON captureTools)} $out/share/tamlinux/capture-tools.json
      ''}
      runHook postInstall
    '';
    postFixup = lib.concatMapStrings (name:
      lib.optionalString (lib.elem name commandNames) ''
        wrapProgram $out/bin/${name} \
          --prefix PATH : "$out/bin${lib.optionalString (commandRuntimeDeps.${name} != [ ]) ":${lib.makeBinPath commandRuntimeDeps.${name}}"}" ${lib.optionalString (name == "tam-macro") "--set TAMLINUX_XKBCOMMON ${lib.getLib pkgs.libxkbcommon}/lib/libxkbcommon.so.0 --run 'export TAMLINUX_MACRO_ENTRY=\"$HOME/.local/bin/tam-macro\"'"} ${lib.optionalString (name == "tam-desktop-test") "--prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [ pkgs.wayland pkgs.libxkbcommon ]} --set-default TAMLINUX_WAYLAND_CLIENT ${lib.getLib pkgs.wayland}/lib/libwayland-client.so.0 --set-default TAMLINUX_XKBCOMMON ${lib.getLib pkgs.libxkbcommon}/lib/libxkbcommon.so.0"} ${lib.optionalString (name == "tam-plugin") "--set TAMLINUX_PLUGIN_CATALOG ${pluginsPayload}/share/tamlinux/plugins"} ${lib.optionalString (name == "tam-shell") "--set-default TAMLINUX_QUICKSHELL_IPC ${pkgs.quickshell}/bin/qs"} ${lib.optionalString (name == "tam-capture-edit" && tensaku != null) "--set-default TAMLINUX_TENSAKU ${tensaku}/bin/tensaku"} ${lib.optionalString (lib.elem name [ "tam-display-text-size" "tam-theme-set-gnome" ]) "--prefix XDG_DATA_DIRS : ${pkgs.gsettings-desktop-schemas}/share/gsettings-schemas/${pkgs.gsettings-desktop-schemas.name} --prefix GIO_EXTRA_MODULES : ${pkgs.dconf.lib}/lib/gio/modules"}
      ''
    ) (lib.attrNames commandRuntimeDeps);
    passthru = {
      names = commandNames;
      inherit commandChecks nativePayloads;
    };
    meta.license = lib.licenses.gpl3Plus;
  };
  commands = pkgs.runCommand "tamlinux-commands-${packageVersion}" {
    # Keep the derivation version for assembly-contract and consumers that read
    # .version; the payload stays version-stable at "1".
    version = packageVersion;
    passthru = commandsPayload.passthru // {
      revision = product.rev;
      payload = commandsPayload;
    };
    meta = commandsPayload.meta;
  } ''
    cp -a ${commandsPayload}/. $out/
    chmod -R u+w $out
    mkdir -p $out/share/tamlinux
    printf '%s' ${lib.escapeShellArg versionNotesText} > $out/share/tamlinux/version-notes.txt
    chmod 644 $out/share/tamlinux/version-notes.txt
    if [ -d $out/share/tamlinux/assets ]; then
      printf '%s\n' ${lib.escapeShellArg productVersion} > $out/share/tamlinux/assets/version
    fi
  '';

in
{
  inherit libtam tam;
  tamlinux-tools = tools;
  tamlinux-shell = shell;
  tamlinux-plugins = plugins;
  tamlinux-commands = commands;
  tamlinux-quickshell = import ./quickshell-provider.nix { inherit pkgs; };
}
  // lib.optionalAttrs (tensaku != null) { tamlinux-tensaku = tensaku; }
  // lib.optionalAttrs (asdcontrol != null) { tamlinux-asdcontrol = asdcontrol; }
