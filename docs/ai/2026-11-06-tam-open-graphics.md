# Session: 2026-11-06 - Give tam-open's Nix viewers a GPU driver

- **CLI Tool**: `claude` `2.1.318`
- **Model**: Claude Opus 5.5 (`claude-opus-5-5`)
- **Commit**: `753932f`
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > A process crashed on this workstation and I want to know why. (excerpt)

  > Yes, make the fix on develop

## Key decisions and implementation notes

- Packaging `tam-open` in `e89c555` put Nix `imv`, `mpv` and `zathura` first on
  its `PATH`. On a non-NixOS host, Nix's GLVND reads the host's Mesa vendor file
  but cannot load the relative library name inside it, so EGL has no driver.
- `nix/packages/nix-graphics.nix` wraps a named program with the Mesa from its
  own closure, using the same two variables as the shell and `tensaku`. It uses
  `--set` because a value inherited from another closure would not work either.
- All three viewers are wrapped because they share the cause: `imv` and `mpv`
  aborted, and `zathura` fell back to CPU rendering.
- `tam-capture-screenrecording` and `tam-chromium-ytdlp-host` still use the bare
  `mpv`. They were outside this request and were not tested or changed.

## Verification

All runs used a private headless sway session on an AMD Renoir host, not the
live Hyprland session.

- Before the fix, the loader searched only Nix paths for `libEGL_mesa.so.0` and
  `imv` failed its `window->egl_context` assertion; `mpv` failed `!vo->x11`.
- After the fix, the wrapped `imv` ran until its timeout, the wrapped `mpv`
  chose `gpu-next` and exited normally, and `zathura` chose `GskGLRenderer`.
- The built `tam-open` exited 0 and an `imv` window appeared in the compositor.
- `nix build .#tamlinux-commands` and the `installed-components` check passed.
  The check now fails if a viewer's wrapper or Mesa paths are missing.
