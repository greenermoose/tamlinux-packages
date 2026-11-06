{ pkgs }:
# Nix GUI programs load their GPU driver through Nix's GLVND. Outside NixOS it
# finds only the host's vendor file, whose relative library name a Nix program
# cannot resolve, so EGL has no driver: imv and mpv abort, GTK falls back to the
# CPU. Point each named program at the Mesa from its own closure instead.
{ package, programs }:
pkgs.symlinkJoin {
  name = "${package.name}-tamlinux-graphics";
  paths = [ package ];
  nativeBuildInputs = [ pkgs.makeWrapper ];
  postBuild = pkgs.lib.concatMapStrings (program: ''
    wrapProgram "$out/bin/${program}" \
      --set __EGL_VENDOR_LIBRARY_FILENAMES "${pkgs.mesa}/share/glvnd/egl_vendor.d/50_mesa.json" \
      --set LIBGL_DRIVERS_PATH "${pkgs.mesa}/lib/dri"
  '') programs;
  inherit (package) meta;
  passthru = { unwrapped = package; graphicsProvider = pkgs.mesa; };
}
