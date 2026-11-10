# Retire the duplicate tam host-profile patch

- **Date:** 2026-11-10
- **CLI Tool:** Codex CLI `0.167.0`
- **Model:** `gpt-6.1-sol`
- **Transcript:** Retained privately by the author.
- **Prompt:**
  > Package up and test Tamlinux 0.6.21

The candidate build stopped because tam 0.51.0 already recognizes Arch through
OS metadata, while the package still applied the historical host-profile patch.
Removed the patch from the tam derivation. The selected source already has the
patch's intended result; no component source changes were needed.

The subsequent assembly-contract build exposed a missing Git build dependency
for the selected tamlinux-tools bundle-build tests. Added Git to that package's
native build inputs so the existing tests can run inside the Nix sandbox.

These are Develop recipe repairs. Candidate 0.6.21's failed selection remains
recorded, and installation requires a new candidate request under the normal
lifecycle. No Test, Run or Release transition occurred.

Verification: `nix build --impure --no-link --print-out-paths .#tam
.#checks.x86_64-linux.assembly-contract` passes, including the tam package's
installed navigation checks and tamlinux-tools package tests. The repaired
tam output is `y5dxhmz0hl8xpdwxj2qpwa2bss55z0df-tam-0.51.0`; the assembly
contract is `yqa7zna6n06fj94pygmfhhy7yakgmkf8-tamlinux-assembly-contract`.
