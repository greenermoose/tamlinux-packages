{ pkgs }:
{
  # Opt-in selections; consumers may choose a subset or add native packages.
  userTools = with pkgs; [
    nodejs_24
    pnpm
    gh
    glow
    evtest
    nano
    lynx
    lowdown
    nil
    nixfmt
  ];
  developer = with pkgs; [
    bash
    coreutils
    gcc
    binutils
    gnumake
    pkg-config
    git
    curl
    cacert
    nano
  ];
  terminalGames = with pkgs; [
    astroterm
    bastet
    bsdgames
    cataclysmDDA.stable.curses
    cbonsai
    curseofwar
    frotz
    gnugo
    nethack
    pmars
    vms-empire
  ];
}
