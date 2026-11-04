# Scope candidate inspect to selected dirty paths

- **Date**: 2026-11-04
- **CLI Tool**: Cursor (`cursor`)
- **Model**: `composer`
- **Transcript**: Retained privately by the author.
- **Request**: Fix packaging so unrelated tam corpus edits do not block Tamlinux candidates.

Candidate inspection now selects only dirty paths claimed by the packaging
session or a registered trial. Unrelated dirty work stays local; HEAD is
pinned for those components. Version-finalize checks use selected paths plus
commits on HEAD, not the uncommitted working tree.
