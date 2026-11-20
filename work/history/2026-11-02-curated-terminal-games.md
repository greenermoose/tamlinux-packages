# Package curated terminal games and simulations for 0.6.1

- **Date**: 2026-11-02
- **CLI Tool**: Antigravity 1.4.12
- **Model**: `gemini-3.8-flash`
- **Transcript**: Retained privately by the author.
- **Prompt**: “Proceed. Create a curated list. Package them for inclusion in Tamlinux 0.6.1.”

Defined the curated `terminalGames` package set in `nix/sets/default.nix` containing eleven terminal games and simulations spanning computer science, cognition, natural sciences, and society (Cataclysm: DDA curses, Frotz, BSD Games, Astroterm, Curse of War, GNU Go, pMARS, Bastet, cbonsai, VMS Empire, NetHack). Created the opt-in `tamlinux.terminalGames` Home Manager module in `nix/modules/games.nix`, registered it in `nix/modules/default.nix`, and documented launch/exit controls, operational notes, and fleet host compatibility in `docs/curated-terminal-games.md`. Verified flake evaluation and contract checks via `nix flake check --no-build`.
