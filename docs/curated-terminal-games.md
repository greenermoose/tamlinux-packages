# Science simulations and learning games

The eleven-package selection introduced in Tamlinux 0.6.1 is retired in
Develop for the next candidate. Fred requested a fresh science and learning
selection and a source list to review before downloading any replacements.
No replacement games have been selected or downloaded.

`(lib.packageSets pkgs).terminalGames` is now empty. The Home Manager options
`tamlinux.terminalGames.enable` and `tamlinux.terminalGames.packages` remain
available for a future reviewed selection or an explicit consumer override.
When a new assembly containing this change is activated, Home Manager removes
the previous selection from its profile. Existing saves and settings remain;
previous generations and their Nix store contents remain available for recovery.

## Retired default selection

Astroterm, Bastet, BSD Games, Cataclysm: Dark Days Ahead (curses), cbonsai,
Curse of War, Frotz, GNU Go, NetHack, pMARS, and VMS Empire.

Their default `start` entries are also removed in the product source. A source
change does not uninstall the games from an already active generation.
