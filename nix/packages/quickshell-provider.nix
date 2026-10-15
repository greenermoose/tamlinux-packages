{ pkgs }:
# Keep the shell's graphics closure private to that process. Product launch
# helpers restore caller values before starting any inheriting child.
pkgs.symlinkJoin {
  name = "${pkgs.quickshell.name}-tamlinux-graphics";
  paths = [ pkgs.quickshell ];
  nativeBuildInputs = [ pkgs.makeWrapper ];
  postBuild = ''
    wrapProgram "$out/bin/quickshell" \
      --run 'if [ "''${TAMLINUX_GRAPHICS_PROVIDER_ENV-}" != "__EGL_VENDOR_LIBRARY_FILENAMES LIBGL_DRIVERS_PATH" ]; then for v in __EGL_VENDOR_LIBRARY_FILENAMES LIBGL_DRIVERS_PATH; do unset "TAMLINUX_HOST_$v"; if [ "''${!v+x}" = x ]; then export "TAMLINUX_HOST_$v=''${!v}"; fi; done; fi' \
      --set __EGL_VENDOR_LIBRARY_FILENAMES "${pkgs.mesa}/share/glvnd/egl_vendor.d/50_mesa.json" \
      --set LIBGL_DRIVERS_PATH "${pkgs.mesa}/lib/dri" \
      --set TAMLINUX_GRAPHICS_PROVIDER_ENV "__EGL_VENDOR_LIBRARY_FILENAMES LIBGL_DRIVERS_PATH"
  '';
  inherit (pkgs.quickshell) meta;
  passthru = { unwrapped = pkgs.quickshell; graphicsProvider = pkgs.mesa; };
}
