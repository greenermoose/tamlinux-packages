# Add Nerd Font requirement and `tam-nut` `/var/lib/tamlinux` `0755` rules

Two fixes discovered during live Step 3 `slowhp` format-2 bundle testing:

- **`recipes/workstation/bundle`:** Adds
  `needs file /usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf arch=ttf-jetbrains-mono-nerd`
  so hosts transitioning off Home Manager (`10-hm-fonts.conf`) require the native
  JetBrainsMono Nerd Font used by top-bar icons (`monospace` ->
  `JetBrainsMono Nerd Font`).
- **`recipes/tam-nut/` (`PKGBUILD`, `tam-nut.conf`, `tam-nut.install`, `test_bootstrap.py`):**
  Ships `/usr/lib/tmpfiles.d/tam-nut.conf` (`d /var/lib/tamlinux 0755 root root -`),
  packages `/var/lib/tamlinux` with `-m755`, adds `tam-nut.install`
  (`post_install`/`post_upgrade` `chmod 0755 /var/lib/tamlinux`) so upgrading or
  replacing `tamlinux-native` fixes pre-existing `0700` `/var/lib/tamlinux`
  directories immediately on `pacman -U`, and bumps `pkgrel` to `2`.

Verification:
- `python3 -B recipes/tam-nut/test_bootstrap.py -v` (`Ran 5 tests in 0.152s`, `OK`)
- `umask 022 && python3 -m unittest discover -s tests -p "test_prepare_candidate.py" -v` (`Ran 22 tests in 10.798s`, `OK`)

- **Date:** 2026-11-14
- **CLI Tool:** Antigravity CLI (`agy`) `1.5.9`
- **Transcript:** Retained privately by the author.
- **Authorship:** AI-assisted recipe, packaging, and test changes.

## Guiding prompts

> Most things are loading normally, but glyphs are missing for the top bar. Seems like a font is missing.
> 2
