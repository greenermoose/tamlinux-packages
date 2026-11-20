## Session: 2026-11-04 — Pin-only source resume with unrelated dirty work

- **CLI Tool**: Cursor (`cursor`) `3.27.22`
- **Model**: `composer`
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > Package up and test Tamlinux 0.6.6

Resume after a pin-only source finalization no longer treats unrelated dirty
files as movement of the selected HEAD. Watched paths are the frozen selection
and any written source-intent files; local drafts outside that set may remain.
