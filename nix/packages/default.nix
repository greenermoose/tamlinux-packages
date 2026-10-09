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
    version = "0.3.0";
    src = sources.tam;
    postPatch = "patchShebangs tests";
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
  shell =
    pkgs.runCommand "tamlinux-shell-${pkgs.lib.trim (builtins.readFile "${sources.tamlinux}/VERSION")}"
      { }
      ''
        mkdir -p $out/share/tamlinux
        cp -R ${sources.tamlinux}/desktop/shell $out/share/tamlinux/
        cp ${sources.tamlinux}/VERSION $out/share/tamlinux/version
        printf '%s\n' ${pkgs.lib.escapeShellArg sources.tamlinux.rev} > $out/share/tamlinux/source-revision
      '';
in
{
  inherit libtam tam;
  tamlinux-tools = tools;
  tamlinux-shell = shell;
}
