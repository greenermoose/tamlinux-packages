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
  terminalGames =
    let
      lib = pkgs.lib;
      cataclysmCurses = pkgs.cataclysmDDA.stable.curses.overrideAttrs (old: {
        env = (old.env or { }) // {
          NIX_CFLAGS_COMPILE =
            lib.concatStringsSep " "
              (lib.filter (s: s != "") [ (old.env.NIX_CFLAGS_COMPILE or "") "-Wno-error" ]);
        };
        postInstall = (old.postInstall or "") + ''
          if [ -x "$out/bin/cataclysm" ] && [ ! -e "$out/bin/cataclysm-dda" ]; then
            ln -s cataclysm "$out/bin/cataclysm-dda"
          fi
        '';
      });
    in
    with pkgs; [
      astroterm
      bastet
      bsdgames
      cataclysmCurses
      cbonsai
      curseofwar
      frotz
      gnugo
      nethack
      pmars
      vms-empire
    ];
}
