## Session: 2026-10-15 — Native system defaults in tamlinux-native (0.4.3 Develop)

- **CLI Tool**: Claude Code (`claude`) `2.1.300`
- **Model**: Claude Opus 5.5 (`claude-opus-5-5`)
- **Commit**: `601bff8`
- **Product input**: `greenermoose/tamlinux` `f43e7c8`
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > Codex has release claims. Please proceed with what you can do.

- **Key Decisions & Implementation Notes**:
  - `prepare-native-integration.py` stages the product's
    `desktop/native/defaults/root` exactly as its `origins.json` records it.
    Digests, modes and in-tree symlinks are checked; unrecorded entries,
    paths outside `/usr/lib`/`/usr/share` and links leaving the tree are
    refused before anything is staged.
  - The recipe copies the tree with modes and links, installs the MIT notice
    and syntax-checks the sleep hook. Font, zram, input-method, pairing-agent
    and plocate providers are `optdepends`; the defaults are inert without
    them. The manifest lists the remaining adapter rows and the
    `systemctl preset` provisioning step for `systemd-oomd`.
- **Verification**:
  - Native staging tests (8) and the full delivery suite (95) pass.
  - A local `makepkg` build (no installation) produced
    `tamlinux-native-0.4.3-0.1`; none of its 38 non-directory paths is owned
    by any installed package, so it is co-installable during Desktop Test.
