{ pkgs, product }:
pkgs.stdenv.mkDerivation {
  pname = "tamlinux-asdcontrol";
  version = "0.6.0";
  src = builtins.path { path = "${product}/desktop/native/providers/asdcontrol"; name = "tamlinux-asdcontrol-source"; };
  dontConfigure = true;
  installPhase = ''
    install -Dm755 asdcontrol $out/bin/asdcontrol
    install -Dm644 LICENSE $out/share/licenses/tamlinux-asdcontrol/LICENSE
    install -Dm644 origins.json $out/share/tamlinux/asdcontrol-origins.json
  '';
  doInstallCheck = true;
  installCheckPhase = ''
    $out/bin/asdcontrol --help > help.txt
    grep -q brightness help.txt
  '';
  meta = {
    description = "Apple display HID brightness control from maintained source";
    license = pkgs.lib.licenses.gpl2Plus;
    platforms = pkgs.lib.platforms.linux;
  };
}
