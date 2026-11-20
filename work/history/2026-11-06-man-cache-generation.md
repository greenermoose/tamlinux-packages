# Session: 2026-11-06 - Generate man page caches in Home Manager session module

- **CLI Tool**: `antigravity` `1.4.12`
- **Model**: `gemini-3.8-flash`
- **Commits**: Pending
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > We have installed some games for Tamlinxu but I don't see any listed in the man pages. Why not?
  > 2 and make this a part of adding new software to the system, not part of the Home Manager switch. Or explain to me why it would be better to make it part of the Home Manager switch.
  > I accept A. Note that decision.
  > Keep going

## Key decisions and implementation notes

- Decision D228: Generate manual page caches in the Home Manager generation (`programs.man.generateCaches = true`).
- Manual pages packaged via Nix are placed under `~/.nix-profile/share/man`, but man database search utilities (`whatis`, `apropos`, and section browsing in `tam`) require man-db index caches.
- Setting `programs.man.generateCaches = lib.mkDefault true;` in `tamlinux.session` ensures Home Manager invokes `mandb` during generation building, producing an immutable manual cache in the Nix store and writing `~/.manpath` with `MANDB_MAP`.
- This keeps the manual search index consistent with installed packages across deployments and rollbacks (`tam-deploy back`).

## Verification

- `nix flake check` passed on `tamlinux-packages` with all 13 checks passing, verifying `man-cache` build derivation and session contract.
