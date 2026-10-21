# Session: 2026-10-21 — Retire the inherited HEY integration

- **CLI Tool**: Codex CLI (`codex`) `0.163.0`
- **Model**: `gpt-6.1-sol`
- **Implementation commit**: `3c4a8f9`
- **Transcript**: Retained privately by the author.
- **Guiding prompt**:
  > Do the most important next step to finish Tamlinux 0.4 Incipiens. Try to get something checked off the 0.4-CHECKLIST.
- **Changes**: Remove the HEY dependency entry; give the explicit migration
  its desktop-file-utils runtime dependency. Package probes verify absence of
  the retired command and shortcuts, retain the real Zoom/webapp/browser chain,
  and exercise launcher/MIME retirement plus preserving return and desktop
  database refresh in an isolated user root.
- **Verification**: Offline development-snapshot build and installed-component
  integration pass; all 81 isolated package probes pass. The static audit
  covers 836 runtime files, with zero missing outputs/required files, eight
  unresolved lexical command names and 88 inherited identifier locations.
  Inventory readiness remains false; these lexical counts are not live
  dependency or installed independence proof. An initial probe reused another
  fixture's user-root variables; this was corrected before the passing build.
- **Limits**: Product/component pins and frozen 0.4.6 remain unchanged. The
  build uses an explicit development snapshot, never activated. A later
  candidate must pin the committed retirement and current components, then
  obtain its own Test instruction and installed proof. No native, boot, login
  or package-removal transaction is performed.
