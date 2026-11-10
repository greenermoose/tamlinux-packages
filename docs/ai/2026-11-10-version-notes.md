# Explain the changes in Tamlinux 0.6.22

- **Date:** 2026-11-10
- **CLI Tool:** Codex CLI `0.167.0`
- **Model:** `gpt-6.1-sol`
- **Transcript:** Retained privately by the author.
- **Prompt:**
  > Make a note: these version notes are terrible. See tamlinux-0.6.19.txt and tamlinux-0.6.20.txt for how they should be done. Can you fix them now?

  > See tamlinux-0.6.15.txt for how to report changes to tam. Report the semver if we have updated tam, not the git hash.

Replaced the four component hashes in `notes/tamlinux-0.6.22.txt` with tam's
command/corpus semvers, `tam 0.51.0 (0.78.1)`, and short descriptions of the
monitor and console changes, deployment recovery and file-bundle tools.
Used 0.6.15 for tam's version format and 0.6.19/0.6.20 for change descriptions.
Checked the selected component histories against the preceding 0.6.20 delivery
and used the tam version pair verified from the installed package.

This corrects the notes on Develop. The already installed 0.6.22 assembly
retains its original immutable notes; no package was rebuilt or deployed and
no candidate number or stage was changed. The generator was not changed.

Verification: read the corrected plain-text notes against both examples and
the selected sources; `git diff --check` passes. No executable changes.
