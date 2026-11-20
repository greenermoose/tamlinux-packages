# Package tam-desktop-test for Tamlinux 0.6.2

- **Date**: 2026-11-02
- **CLI Tool**: Antigravity CLI (`agy`) `1.4.12`
- **Model**: Gemini 3.8 Flash (`gemini-3.8-flash`)
- **Transcript**: Retained privately by the author.

## Prompts

> Include tam-desktop-test in Tamlinux 0.6.2.

## Changes

1. **`nix/packages/default.nix`**:
   - Registered `tam-desktop-test` in `commandRuntimeDeps` with `pkgs.python3`, `pkgs.wl-clipboard`, `pkgs.libnotify`, `pkgs.util-linux`, and `pkgs.systemd`.
   - In `commands.postFixup`, configured `wrapProgram` for `tam-desktop-test` with:
     - `--prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [ pkgs.wayland pkgs.libxkbcommon ]}`
     - `--set-default TAMLINUX_WAYLAND_CLIENT ${lib.getLib pkgs.wayland}/lib/libwayland-client.so.0`
     - `--set-default TAMLINUX_XKBCOMMON ${lib.getLib pkgs.libxkbcommon}/lib/libxkbcommon.so.0`
   - Verified that `commands.installPhase` installs `tam-desktop-test` launcher into `$out/bin/` and `test-battery` + `virtual_input.py` into `$out/share/tamlinux/desktop/`.

2. **`tests/installed-components.nix`**:
   - Added assertions to verify executable presence and basic `--help` output of `tam-desktop-test` when present in `components.tamlinux-commands`.

## Verification

- `PYTHONPATH=tests python3 -B -m unittest discover -s tests -p 'test_*.py'` (154 tests passed).
- `tam-desktop-test --help` and dry-run execution verified.
