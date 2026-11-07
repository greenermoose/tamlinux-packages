# AI collaboration and provenance

2026-11-07: Antigravity `1.5.3` (`claude-opus-5.5-high` / `gemini-4-argon-high`) generates `notes/tamlinux-<version>.txt` during candidate packaging, installs `share/tamlinux/version-notes.txt` (with delivery fallback), and exposes `TAMLINUX_VERSION_NOTES` in the shell and session environments. [Session](docs/ai/2026-11-07-version-notes-generation.md).

2026-11-07: Codex CLI `0.167.0` (`gpt-6.1-sol`) derives the fresh-session launcher's installed activity count from its packaged menu. [Session](docs/ai/2026-11-07-session-activity-count.md).

2026-11-06: Antigravity `1.4.12` (`gemini-3.8-flash`) enables Home Manager man page cache generation in the session module (D228). [Session](docs/ai/2026-11-06-man-cache-generation.md).

2026-11-06: Claude Code `2.1.318` (`claude-opus-5-5`) runs the `json5` migration tests in the installed components check. [Session](docs/ai/2026-11-06-json5-migration-tests.md).

2026-11-06: Claude Code `2.1.318` (`claude-opus-5-5`) gives `tam-open`'s Nix viewers a GPU driver after `imv` aborted on a non-NixOS host. [Session](docs/ai/2026-11-06-tam-open-graphics.md).

2026-11-04: Cursor (`composer`) narrows the commands payload desktop allowlist for Tamlinux 0.6.10 Package/Test speed. [Session](docs/ai/2026-11-04-0.6.10-commands-desktop-allowlist.md).

2026-11-04: Cursor (`composer`) recovers Package/Test speed for 0.6.9 and unblocks Pacman quickshell removal in the clean-host collector. [Session](docs/ai/2026-11-04-0.6.9-speed-quickshell.md).

2026-11-04: Cursor (`composer`) restores `tamlinux-commands` wrapper `.version` after the version-stable payload split. [Session](docs/ai/2026-11-04-commands-wrapper-version.md).

2026-11-04: Cursor (`composer`) lets pin-only source resume keep unrelated dirty component drafts. [Session](docs/ai/2026-11-04-pin-only-resume-dirty.md).

2026-11-04: Cursor (`composer`) speeds Package/Test assembly for Tamlinux 0.6.6 (narrowed check sources, version-stable payloads, rebuild instrumentation, fleet profile prebuild). [Session](docs/ai/2026-11-04-0.6.6-package-speed.md).

2026-11-04: Cursor (`composer`) packages `start` 0.2 as a native `libtam` payload (no Python). [Session](docs/ai/2026-11-04-start-c-native.md).

2026-11-04: Cursor (`composer`) scopes candidate inspect so unrelated dirty component work does not block packaging. [Session](docs/ai/2026-11-04-scoped-candidate-inspect.md).

2026-11-04: Cursor (`composer`) wires nautilus launcher packaging for Tamlinux 0.6.3. [Session](docs/ai/2026-11-04-0.6.3-nautilus-launchers.md).

2026-11-02: Codex CLI `0.166.0` (`gpt-6.1-sol`) separates recorded inclusions from named-version candidate preparation, preserves exact tam command/corpus requests, and verifies source/artifact delivery. [Session](docs/ai/2026-11-02-candidate-inclusions.md).

2026-11-02: Antigravity `1.4.12` (`gemini-3.8-flash`) packages tam-desktop-test runtime dependencies and library wrappers for candidate 0.6.2. [Session](docs/ai/2026-11-02-package-tam-desktop-test.md).

2026-11-02: Codex CLI `0.166.0` (`gpt-6.1-sol`) implements the development and candidate workflow. [Session](docs/ai/2026-11-02-candidate-workflow.md).

2026-11-02: Antigravity `1.4.12` (`gemini-4-argon-medium`) prepares the 0.6.1 KBN WB assembly and verifies curated terminal game builds. [Session](docs/ai/2026-11-02-061-preparation.md).

2026-11-02: Antigravity `1.4.12` (`gemini-3.8-flash`) packages runtime dependencies for the start command. [Session](docs/ai/2026-11-02-hi-and-start-packaging.md).

2026-11-02: Antigravity `1.4.12` (`gemini-3.8-flash`) pins tam 0.48.1 / corpus 0.58.1 for candidate 0.6.1. [Session](docs/ai/2026-11-02-tam-0481-0581.md).

2026-11-02: Antigravity `1.4.12` (`gemini-3.8-flash`) packages curated terminal games and simulations for candidate 0.6.1. [Session](docs/ai/2026-11-02-curated-terminal-games.md).

2026-11-01: Codex CLI `0.166.0` (`gpt-6.1-sol`) implements resumable candidate preparation. [Session](docs/ai/2026-11-01-candidate-process.md).

This repository follows the
[Tamlinux AI provenance standard](https://github.com/greenermoose/tamlinux/blob/develop/docs/ai-provenance-standard.md).
AI-assisted commits carry tool/model trailers. Session records give guiding
prompts, implementation choices and verification; transcripts are retained
privately by the author.

**How to read this ledger:** Recent session bullets below are provenance, not
open deploy instructions. Exact assemblies are in [`VERSION`](VERSION) and
[`deliveries/`](deliveries/). Living session files are indexed in
[`docs/ai/README.md`](docs/ai/README.md). Archived sessions (first extraction,
lettered 0.4.x, early superseded 0.5 prep) are in Git via
[`docs/ai/FILING-CARD.md`](docs/ai/FILING-CARD.md).

## Recent sessions (kept in tree)

2026-11-02: Antigravity `1.4.12` (`gemini-3.8-flash`) packages tam-desktop-test runtime dependencies and library wrappers for candidate 0.6.2. [Session](docs/ai/2026-11-02-package-tam-desktop-test.md).

2026-11-02: Antigravity `1.4.12` (`gemini-4-argon-medium`) prepares the 0.6.1 KBN WB assembly and verifies curated terminal game builds. [Session](docs/ai/2026-11-02-061-preparation.md).

2026-11-02: Antigravity `1.4.12` (`gemini-3.8-flash`) pins tam 0.48.1 / corpus 0.58.1 for candidate 0.6.1. [Session](docs/ai/2026-11-02-tam-0481-0581.md).

2026-11-02: Antigravity `1.4.12` (`gemini-3.8-flash`) packages curated terminal games and simulations for candidate 0.6.1. [Session](docs/ai/2026-11-02-curated-terminal-games.md).

2026-11-01: Antigravity `1.4.12` (`gemini-3.8-flash`) packages Nix reference manuals into tam and session. [Session](docs/ai/2026-11-01-nix-man-reference.md).

2026-11-01: Codex CLI `0.166.0` (`gpt-6.1-terra`) prepares the 0.5.12 assembly. [Session](docs/ai/2026-11-01-0512-preparation.md).

2026-10-31: Codex CLI `0.166.0` (`gpt-6.1-terra`) reviews macro package dependencies. [Session](docs/ai/2026-10-31-continuation-integration.md).

2026-10-30: Codex CLI `0.166.0` (`gpt-6.1-terra`) corrected the session bootstrap. [Session](docs/ai/2026-10-30-session-bootstrap.md).

2026-10-29: Codex CLI `0.166.0` (`gpt-6.1-terra`) completed 0.5.11 candidate assembly preparation. [Session](docs/ai/2026-10-29-0511-ready.md).

2026-10-29: Codex CLI `0.166.0` (`gpt-6.1-terra`) begins 0.5.11 assembly preparation. [Session](docs/ai/2026-10-29-prepare-0511.md).

2026-10-29: Codex CLI `0.165.0` (`gpt-6.1-sol`) records the approved Start menu and binding cutover requirements for 0.5.10 preparation. [Session](docs/ai/2026-10-29-start-menu.md).

2026-10-28: Codex CLI `0.165.0` (`gpt-6.1-sol`) prepares 0.5.9 with shell palette, visible authorization and readiness validation fixes. [Session](docs/ai/2026-10-28-0.5.9-candidate.md).

2026-10-23: Console-first delivery and Blue Sparkler 0.5.0–0.5.4 assembly work. See index rows for 2026-10-23 in [`docs/ai/README.md`](docs/ai/README.md).

2026-10-22: Release 0.4.8, the final Incipiens / Gate A assembly. [Session](docs/ai/2026-10-22-release-0.4.8.md).

## Milestone index (kept sessions)

| Date | Milestone | Record |
| --- | --- | --- |
| 2026-10-30 | Terminal prerequisite; tam/corpus pins; session bootstrap | [docs/ai/README.md](docs/ai/README.md) |
| 2026-10-29 | 0.5.11 prep; start menu; screensaver; fonts | [docs/ai/README.md](docs/ai/README.md) |
| 2026-10-28 | 0.5.5–0.5.9 candidates; console welcome; tam pins | [docs/ai/README.md](docs/ai/README.md) |
| 2026-10-27 | Monitor integration; tam 0.45.5 selection | [docs/ai/README.md](docs/ai/README.md) |
| 2026-10-25 | 0.5.5 plan; monitor feasibility | [docs/ai/README.md](docs/ai/README.md) |
| 2026-10-23 | Console-first and 0.5.0–0.5.4 | [docs/ai/README.md](docs/ai/README.md) |
| 2026-10-22 | Release 0.4.8; nut | [2026-10-22-release-0.4.8.md](docs/ai/2026-10-22-release-0.4.8.md), [nut](docs/ai/2026-10-22-nut.md) |

Older milestones through first extraction (2026-10-09) remain in Git; retrieve
paths listed on [`docs/ai/FILING-CARD.md`](docs/ai/FILING-CARD.md).

Candidate 0.6.2: [preparation](docs/ai/0.6.2-candidate-preparation.md).

Candidate 0.6.3: [preparation](docs/ai/0.6.3-candidate-preparation.md).

Candidate 0.6.4: [preparation](docs/ai/0.6.4-candidate-preparation.md).

Candidate 0.6.5: [preparation](docs/ai/0.6.5-candidate-preparation.md).

Candidate 0.6.6: [preparation](docs/ai/0.6.6-candidate-preparation.md).

Candidate 0.6.7: [preparation](docs/ai/0.6.7-candidate-preparation.md).

Candidate 0.6.8: [preparation](docs/ai/0.6.8-candidate-preparation.md).

Candidate 0.6.9: [preparation](docs/ai/0.6.9-candidate-preparation.md).

Candidate 0.6.10: [preparation](docs/ai/0.6.10-candidate-preparation.md).

Candidate 0.6.11: [preparation](docs/ai/0.6.11-candidate-preparation.md).

Candidate 0.6.12: [preparation](docs/ai/0.6.12-candidate-preparation.md).

Candidate 0.6.14: [preparation](docs/ai/0.6.14-candidate-preparation.md).

Candidate 0.6.15: [preparation](docs/ai/0.6.15-candidate-preparation.md).

Candidate 0.6.17: [preparation](docs/ai/0.6.17-candidate-preparation.md).
