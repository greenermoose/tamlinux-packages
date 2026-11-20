# Include Nix manual pages in tam and session

- **Date**: 2026-11-01
- **CLI Tool**: Antigravity 1.4.12
- **Model**: `gemini-3.8-flash`
- **Transcript**: Retained privately by the author.
- **Prompt**: “The goal is to have a complete set of reference material available through tam. Which option do you suggest? The goal is for every future installation of Tamlinux to include a complete set of reference material for nix.” / “make it so”

Included `pkgs.nix.man` in `tam`'s package derivation and runtime `MANPATH` wrapper, asserted `tam man nix` resolution in `tests/tam-package-navigation.sh`, and added `pkgs.nix.man` to `home.packages` in the Tamlinux session module so both `tam man nix` and system `man nix` provide complete Nix reference documentation across future installations.
