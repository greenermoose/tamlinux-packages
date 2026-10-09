# 2026-10-09 — Initial Nix delivery extraction

- **CLI Tool**: Codex CLI `0.162.0` (live checked).
- **Model**: `gpt-6.1-sol` (runtime/transcript metadata).
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted implementation directed by Fred.
- **Commit**: Initial extraction commit carrying this record.

Guiding prompt:

> I have reviewed and approve Tamlinux repository ownership and package plan that is open in micro right now. Read that plan and begin implementing. Go ahead and close the micro window. Ask if you have any questions.

The approved split assigns product behavior to Tamlinux, reusable utilities to
tamlinux-tools, public packaging to this repository, and personal/fleet
configuration to the consumer. Selected reusable Nix definitions were extracted
without importing private history or settings. Public inputs are pinned to
existing source revisions; the generic example has a separate user identity.

The native recipes use source Makefiles and tests. Tests' interpreter paths are
mapped to the Nix build sandbox. Additional checks exercise the installed offline
guide, library headers/linkage, file-selector errors, and C compilation/execution.
The Home Manager module preserves the existing shell service and protocol-trial
interface and protects plugin override recovery state. A consumer may supply
accepted payloads explicitly while consolidated source differences are reviewed.

Verification results are recorded in `docs/verification.md`. This is a Develop
candidate. Complete native host integration, plugin reconciliation, installed
delivery versioning, activation/recovery proof and publication remain separate.
