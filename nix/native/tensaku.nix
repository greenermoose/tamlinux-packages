{ pkgs, product }:
let
  application = pkgs.rustPlatform.buildRustPackage {
  pname = "tamlinux-tensaku";
  version = "0.29.0";
  src = builtins.path { path = "${product}/desktop/vendor/tensaku"; name = "tamlinux-tensaku-source"; };
  cargoHash = "sha256-q+jS+NX/AKWwaidEQrJMF2hMW+UCb1XJ9zA9Tc5iH5A=";
  nativeBuildInputs = [ pkgs.pkg-config pkgs.wrapGAppsHook4
    (pkgs.python3.withPackages (p: [ p.fonttools ])) ];
  buildInputs = [ pkgs.gtk4 pkgs.gtk4-layer-shell pkgs.libadwaita pkgs.libepoxy
    pkgs.fontconfig pkgs.libxkbcommon pkgs.wayland ];
  doCheck = true;
  preBuild = ''
    python3 ${builtins.path { path = "${product}/desktop/theme/rename-font.py"; name = "tamlinux-rename-font.py"; }} src/assets/omarchy.ttf src/assets/TamlinuxIcons.ttf
  '';
  # Tests/configuration get empty state and cannot touch the build user's home.
  preCheck = ''
    export HOME=$TMPDIR/tensaku-home
    mkdir -p $HOME
    export XDG_CONFIG_HOME=$HOME/config XDG_STATE_HOME=$HOME/state XDG_CACHE_HOME=$HOME/cache
    export TAMLINUX_TIFF_FIXTURE=$TMPDIR/tamlinux-alpha.tiff
  '';
  postCheck = ''
    ${pkgs.python3.withPackages (p: [ p.pillow ])}/bin/python3 - <<'PY'
    import os
    from PIL import Image
    image = Image.open(os.environ['TAMLINUX_TIFF_FIXTURE'])
    assert image.size == (13, 9)
    assert image.convert('RGBA').getpixel((0, 0)) == (128, 64, 32, 128)
    print('Independent TIFF decode preserves straight RGB and alpha')
    PY
  '';
  postInstall = ''
    install -Dm644 LICENSE $out/share/licenses/tamlinux-tensaku/LICENSE
    install -Dm644 NOTICE $out/share/licenses/tamlinux-tensaku/NOTICE
    install -Dm644 origins.json $out/share/tamlinux/tensaku-origins.json
    install -Dm644 dev.tensaku.Tensaku.desktop $out/share/applications/dev.tensaku.Tensaku.desktop
    install -Dm644 assets/tensaku.svg $out/share/icons/hicolor/scalable/apps/dev.tensaku.Tensaku.svg
  '';
  meta = {
    description = "Retained screenshot annotation from maintained Tamlinux source";
    license = pkgs.lib.licenses.mpl20;
    mainProgram = "tensaku";
    platforms = pkgs.lib.platforms.linux;
  };
};
in pkgs.symlinkJoin {
  name = "${application.name}-graphics";
  paths = [ application ];
  nativeBuildInputs = [ pkgs.makeWrapper ];
  # Non-NixOS hosts do not provide NixOS's /run/opengl-driver links. The
  # GLVND loader needs a vendor JSON and matching DRI libraries from the same
  # Nix closure as GTK, rather than an undeclared native driver fallback.
  postBuild = ''
    wrapProgram "$out/bin/tensaku" \
      --set-default __EGL_VENDOR_LIBRARY_FILENAMES "${pkgs.mesa}/share/glvnd/egl_vendor.d/50_mesa.json" \
      --set-default LIBGL_DRIVERS_PATH "${pkgs.mesa}/lib/dri"
  '';
  inherit (application) meta;
  passthru = { inherit application; graphicsProvider = pkgs.mesa; };
}
