{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.tamlinux.terminalGames;
  sets = import ../sets { inherit pkgs; };
in
{
  options.tamlinux.terminalGames = {
    enable = lib.mkEnableOption "curated terminal games and simulations for text VT exploration";
    packages = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = sets.terminalGames;
      description = "Curated terminal games and simulations providing insight into computer science, cognition, science, nature, and society.";
    };
  };
  config = lib.mkIf cfg.enable {
    home.packages = cfg.packages;
  };
}
