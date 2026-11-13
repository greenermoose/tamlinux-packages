# Portable UX list and tool requirement

The workstation list now names menu extensions, paired Chromium extension
files and native registrations, Chromium flags, portal/Fcitx settings and
additional terminals/desktop overrides. Browser profiles, credentials and
application state remain outside it. Product native defaults supply the
matching generated files. Imported deliveries and the development recipe
require tam-bundle 0.13.0 for cancellation of prepared user plans.

Verification: eight bundle delivery/comparison/settings fixtures and four
product installation cases passed. The latter validate real generated browser
paths and scan staged defaults for Nix store references. No full workstation
bundle or bootstrap was rebuilt; neither recipe source lock was repinned.

Complete portable mutable desktop-state coverage, whole-UX audit, reviewed
exact-source rebuilds and physical acceptance remain open. There was no native
package action or stage transition.

- **Date:** 2026-11-12
- **CLI Tool:** Codex CLI (`codex`) `0.167.2`
- **Model:** `gpt-6.1-sol`
- **Transcript:** Retained privately by the author.
- **Authorship:** AI-assisted source implementation, tests and records.

## Guiding prompt

> resume from [redacted: private handoff reference], including the remaining source gates and native-tool discrepancy.
