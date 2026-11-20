# Resumable candidate preparation

- **Date**: 2026-11-01
- **CLI Tool**: Codex CLI (`codex`) `0.166.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > Evaluate the current situation. Figure out how to get out of this mess and why you got into it. Fix the process so we don't run into this situation again. We need better scripts to help us make faster and more certain progress preparing a test candidate.

  > Implement the plan.

- **Implementation**: One ten-target policy drives preparation. Focused tests run against archived pinned source. Evidence fingerprints cover pins, recipes and verification policy; stale, incomplete and unavailable outputs cannot be recorded. Nix reuses valid outputs and unchanged focused checks are reused.
- **Delivery boundary**: Develop improvements; the prepared 0.5.12 assembly is unchanged. These changes require a later recorded candidate before deployment.
- **Verification**: 15 preparation tests pass, covering stale and missing evidence, incomplete targets, unavailable outputs and cache reuse. The required checks also passed on the exact pinned 0.5.12 archive: 43 theme-ownership, six keybinding-default and eight user-default tests. No new candidate was frozen.
