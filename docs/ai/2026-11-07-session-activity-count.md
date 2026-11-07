# Fresh-session activity verification

- **CLI Tool**: Codex CLI `0.167.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Prompt**:
  > Proceed. The goal is to package up and test Tamlinux 0.6.15. Continue working toward that goal. Ask me for help if you get stuck.

The fresh-session check expected 18 installed launcher activities after the
packaged menu grew to 20. It now reads the packaged menu and requires the
launcher to report every entry installed. An empty menu fails. The check prints
the launcher output so a missing command is visible in the build log.

This verification-only correction precedes the delivery assembly freeze for
0.6.15. The selected component revisions and their package contents are unchanged.

Validation: `nix build --impure --no-link --print-out-paths .#checks.x86_64-linux.fresh-session`
passes against the selected 0.6.15 packages.
