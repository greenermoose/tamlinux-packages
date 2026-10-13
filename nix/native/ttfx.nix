{ pkgs, product }:
pkgs.rustPlatform.buildRustPackage {
  pname = "tamlinux-ttfx";
  version = "0.3.2";
  src = builtins.path { path = "${product}/desktop/vendor/ttfx"; name = "tamlinux-ttfx-source"; };
  cargoHash = "sha256-DNrg12MNqBcQi6yvoJObM1gtE90iGBCxeQ3RwueYCE4=";
  doCheck = true;
  postInstall = ''
    install -Dm644 LICENSE $out/share/licenses/tamlinux-ttfx/LICENSE
    install -Dm644 NOTICE $out/share/licenses/tamlinux-ttfx/NOTICE
    install -Dm644 origins.json $out/share/tamlinux/ttfx-origins.json
  '';
  meta = {
    description = "Retained terminal text effects from maintained Tamlinux source";
    license = pkgs.lib.licenses.mit;
    mainProgram = "ttfx";
    platforms = pkgs.lib.platforms.linux;
  };
}
