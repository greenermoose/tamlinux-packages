{ config, lib, pkgs, ... }:
let
  cfg = config.tamlinux.agentSkills;
  directories = [ ".agents/skills" ".claude/skills" ".codex/skills"
    ".pi/agent/skills" ".hermes/skills" ];
  # Do not create individual entries inside a consumer's whole-directory link.
  covered = relative: lib.any (file:
    file.enable && (file.target == relative || lib.hasPrefix "${file.target}/" relative)
  ) (lib.attrValues config.home.file);
  root = "${cfg.package}/share/tamlinux/skills";
  arguments = lib.escapeShellArgs ([
    "--home" config.home.homeDirectory
    "--data-home" config.xdg.dataHome
    "--store" root
    "--managed-directory"
  ] ++ cfg.managedDirectories);
in {
  options.tamlinux.agentSkills = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.tamlinux.shell.enable
        && (config.tamlinux.shell.package.passthru.features.agentSkills or false);
      description = "Install and verify the Tamlinux desktop and crash-diagnosis agent skills.";
    };
    package = lib.mkOption {
      type = lib.types.package;
      default = config.tamlinux.shell.package;
      description = "Selected immutable package containing share/tamlinux/skills.";
    };
    managedDirectories = lib.mkOption {
      type = lib.types.listOf (lib.types.enum directories);
      default = lib.filter (relative: !(covered relative)) directories;
      description = "Agent skill directories in which activation registers individual skills. Whole-directory managers supply their own two links.";
    };
  };
  config = lib.mkIf cfg.enable {
    xdg.dataFile."tamlinux/skills".source = root;
    home.activation.tamlinuxAgentSkills = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
      run ${pkgs.python3}/bin/python3 -I ${root}/manage.py --install ${arguments}
    '';
  };
}
