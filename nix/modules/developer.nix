{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.tamlinux.developer;
in
{
  options.tamlinux.developer = {
    enable = lib.mkEnableOption "the universal C developer baseline";
    libraries = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [];
      description = "Assembly-matched development libraries and build dependencies.";
    };
    nativeProvided = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "The host supplies and verifies the compiler, headers, linker, editing and secure download tools.";
    };
  };
  config = lib.mkIf cfg.enable {
    home.packages = cfg.libraries ++ lib.optionals (!cfg.nativeProvided) (import ../sets { inherit pkgs; }).developer;
    home.sessionSearchVariables.PKG_CONFIG_PATH = map (p: "${lib.getDev p}/lib/pkgconfig") cfg.libraries;
  };
}
