## Session: 2026-11-04 — Package start as native C payload

- **CLI Tool**: Cursor (`cursor`) `3.27.22`
- **Model**: `composer`
- **Transcript**: Retained privately by the author.
- **Prompts**: (same session as product rewrite; packaging follows D224)

### Work

Added `start` to `nativeNames` so it builds against `libtam` like
`tam-hardware`. Cleared `commandRuntimeDeps.start` Python wrap. Updated
`session-contract.nix` to assert `start`'s own semver, installed
`share/start/menu.json`, and `18/18` Guides & References activities.
