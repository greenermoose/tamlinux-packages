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
    nativeProvided = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "The host supplies and verifies the compiler, headers, linker, editing and secure download tools.";
    };
  };
  config = lib.mkIf (cfg.enable && !cfg.nativeProvided) {
    home.packages = (import ../sets { inherit pkgs; }).developer;
  };
}
