## Session: 2026-11-04 — Restore tamlinux-commands wrapper version

- **CLI Tool**: Cursor (`cursor`) `3.27.22`
- **Model**: `composer`
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > Package up and test Tamlinux 0.6.6

The version-stable commands payload left the public `tamlinux-commands`
wrapper without a derivation `.version`. Restore `version = packageVersion`
so assembly-contract and `.version` consumers keep working.

Also keep `share` in the shell payload source filter so
`share/nftables` is copied into the payload.

Narrowed command checks need sibling lists or full-product opt-in for multi-command integrators.
