# Correct the 0.6.31 Make pilot tam pin

- **CLI tool** — Codex CLI `0.170.0`
- **Model** — `gpt-6.2-sol`
- **Transcript** — Retained privately by the author.

> Fix the tam issue. Tamlinux should install tam 0.61.4 with corpus 0.96.3. Resolve that ambiguity.

Fred approved replacing the uninstalled pilot delivery under 0.6.31.
The replacement delivery was recorded in commit `8c2964f`. It pins
tam command 0.61.4 and corpus 0.96.3. The manifest SHA-256 is
`39621669846e19021c4b3df1d1c55bbff7cb2579f8a8b89c7d70ec255c0d59b5`.
It supersedes the [first rehearsal](2026-11-18-clean-make-pilot.md).

The corrected stage installed and reinstalled all 3,285 files through
the approved-plan Make target in an isolated Arch fixture. Its installed
`/usr/bin/tam --version` reported command 0.61.4, corpus 0.96.3, and
Tamlinux cultivar KBN WB 0.6.31. An administrator-local command survived.
Source preparation accepted the replacement manifest and rejected a
stage rebuilt from the superseded source pins. The hardware trial is pending.
