{
  config,
  lib,
  ...
}:
let
  cfg = config.tamlinux.tools;
in
{
  options.tamlinux.tools = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.tamlinux.shell.enable;
      description = "Install the tam command, its offline guide and tam-file-select from the assembly.";
    };
    tam = lib.mkOption {
      type = lib.types.package;
      description = "The tam command package from the recorded assembly.";
    };
    fileSelect = lib.mkOption {
      type = lib.types.package;
      description = "The tamlinux-tools package from the recorded assembly.";
    };
  };
  config = lib.mkIf cfg.enable {
    home.file = {
      ".local/bin/tam".source = "${cfg.tam}/bin/tam";
      # tam reads ~/.local/share/tamlinux/knowledge before system data
      # directories, so the packaged guide wins over any other installation.
      ".local/share/tamlinux/knowledge".source = "${cfg.tam}/share/tamlinux/knowledge";
      ".local/bin/tam-file-select".source = "${cfg.fileSelect}/bin/tam-file-select";
    };
  };
}
