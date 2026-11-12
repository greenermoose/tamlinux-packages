# Display continuity candidate 0.6.23

- **Date:** 2026-11-12
- **CLI Tool:** Codex CLI `0.167.2`
- **Model:** `gpt-6.1-sol`
- **Transcript:** Retained privately by the author.
- **Prompt:** (private plan number redacted)
  > For [redacted: private plan], select an exact Test candidate and prepare the approved native installation and Dell trial.

Prepared candidate 0.6.23 with product
`98806d0f9b387b13c93b2083fc5046c86262baa5`, library
`67cffd54df3f674bc9867a4a5b8962155f912b53`, tools
`b92c4f5da7712ce84905d89afb683a7a7054aa16` and the unchanged tam
pin from 0.6.22. Dependency pins remain unchanged. The source selection
contains the committed Develop product tree, including dormant bundle
preparation support; this does not initiate conversion or native bundle delivery.

All ten assembly targets build. The exact product desktop suite passes
301 units, with 14 skipped tests and no core dumps. All 194 assembly tests
pass. The final packaged shell, plugins and standalone helper match the
selected source and both native archives through `check-display-integration.py`.

The required display providers are Hyprland **0.56.2-4.2** and Aquamarine
**0.15.1-1.2**, frozen in `contracts/providers/selection.json` and its recipe
closure. Both are needed before trying the new workspace helper. The product's
native integration payload remains compatible with the prior installed
`tamlinux-native` package; there is no native integration payload change.
The generic candidate operator's native integration check does not verify
the display provider pair; operators must check those archives, installed
versions and the running compositor/library identities separately.

The assembly is prepared for a later exact-candidate Test instruction.
No Test branch, host installation, session restart, physical trial or cleanup
was performed. Native installation, its rollback snapshot and session
re-entry require their own approvals. Runtime logging, quiet idle and the
20-switch physical continuity matrix remain open.
