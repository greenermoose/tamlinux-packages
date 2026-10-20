# 2026-10-20 — Single-owner input-method startup

- **CLI Tool**: Codex CLI `0.163.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted implementation directed and reviewed by Fred.
- **Prompts**:
  > What's next for Tamlinux 0.4.4?

  > Close the evidence gaps.

  > Looks good. Close the review window and proceed.

Fred approved the public input-startup plan before implementation. Fresh Arch
VM evidence exposed competing vendor XDG and native systemd startup paths.
The session module supplies a default Hidden=true override with explicit
consumer precedence; the native unit restarts only on failure, respecting a
successful exit when another instance already owns the bus name.

The repair is prepared as the next unused Develop letter, 0.4.4-l. This is
no authorization to promote, install on the workstation, or release it.

Verification at the implementation commit: eight native-default tests pass;
package/module evaluation and two-login VM proof remain in progress. Subsequent
verification is recorded in a forward update to this record and the plan.

The implementation commit contains this record; inspect Git history for exact
source identity. No transcript identifiers or private evidence paths are public.
