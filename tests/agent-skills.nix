{ pkgs, home-manager, components }:
let
  root = "${components.tamlinux-shell}/share/tamlinux/skills";
  makeHome = extra: home-manager.lib.homeManagerConfiguration {
    inherit pkgs;
    modules = [ ../nix/modules {
      home.username = "alex";
      home.homeDirectory = "/home/alex";
      home.stateVersion = "25.05";
      manual.manpages.enable = false;
      xdg.dataHome = "/home/alex/data with spaces";
      tamlinux.agentSkills = { enable = true; package = components.tamlinux-shell; };
    } extra ];
  };
  fresh = (makeHome { }).config;
  whole = (makeHome {
    home.file.".agents/skills".source = pkgs.emptyDirectory;
    home.file.".claude/skills".source = pkgs.emptyDirectory;
  }).config;
  disabled = (makeHome { tamlinux.agentSkills.enable = pkgs.lib.mkForce false; }).config;
  activation = pkgs.writeText "tamlinux-skills-activation" fresh.home.activation.tamlinuxAgentSkills.data;
in
assert fresh.tamlinux.agentSkills.managedDirectories == [
  ".agents/skills" ".claude/skills" ".codex/skills" ".pi/agent/skills" ".hermes/skills" ];
assert whole.tamlinux.agentSkills.managedDirectories == [
  ".codex/skills" ".pi/agent/skills" ".hermes/skills" ];
assert fresh.home.activation.tamlinuxAgentSkills.after == [ "linkGeneration" ];
assert !(disabled.home.activation ? tamlinuxAgentSkills);
assert fresh.xdg.dataFile."tamlinux/skills".source == root;
pkgs.runCommand "tamlinux-agent-skills-contract" { nativeBuildInputs = [ pkgs.python3 ]; } ''
  set -eu
  test -f ${root}/tamlinux/SKILL.md
  test -f ${root}/diagnose-crash/SKILL.md
  test -f ${root}/diagnose-crash/LICENSE
  # Dry-run activation prints the command without registering skills.
  run() { printf '%s\n' "$*"; }
  . ${activation}
  # Real registration and rejection run only in an isolated build home.
  export HOME="$TMPDIR/home with spaces"
  export XDG_DATA_HOME="$HOME/data with spaces"
  mkdir -p "$XDG_DATA_HOME/tamlinux"
  ln -s ${root} "$XDG_DATA_HOME/tamlinux/skills"
  python3 -I ${root}/manage.py --install --store ${root}
  python3 -I ${root}/manage.py --check --store ${root}
  ln -s /usr/share/omarchy/missing "$HOME/.codex/skills/omarchy"
  if python3 -I ${root}/manage.py --check --store ${root}; then
    echo 'Inherited skill was incorrectly accepted' >&2; exit 1
  fi
  python3 -I ${root}/manage.py --install --store ${root}
  test ! -L "$HOME/.codex/skills/omarchy"
  mkdir -p "$out"
''
