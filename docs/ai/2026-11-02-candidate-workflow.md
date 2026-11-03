# Development and candidate workflow

- **Date**: 2026-11-02
- **CLI Tool**: Codex CLI (`codex`) `0.166.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Prompts**:

> For Tamlinux 0.6.2, improve the process of preparing and then testing a version candidate. I noticed that agy spent a lot of time on unnecessar busy work. I believe this is due to inadequate scripts and a poorly conceived process for gathering, packagine, preparing, installing, and then testing software in operation. Think through every step of the process and find ways to speed it up, find efficiencies, reduce re-work, build on cached work, avoid re-testing assumptions over and over again, and so on. Between requests to package up a version of Tamlinux for testing, I should be able to very easily edit, build, and try out new software. Then, when I'm ready to package up the current state of my workstation for a version of Tamlinux, I should be able to say "Package and test the next version of Tamlinux." Our deterministic scripts and harness guardrails should be so good, that any AI agent (including Gemini 3.8 Flash) should be able to quickly package up and install a version of Tamlinux for me to test.

> Implement the plan.

Added source gathering, locked version reservation, interrupted-commit recovery, exact source publication, selective pins, native compatibility and immutable candidate freezing. Split command checks and native compilation into reusable derivations; focused checks have a separate source/runner identity.

The operator integration binds a combined request to one frozen candidate and host. Native installation remains a separate approved step; Test records distinguish installation, physical trials and energy evidence. Existing candidates and releases are unchanged.

Verification passed for all ten required Nix package/contract outputs using an immutable snapshot of this change. Metadata-only VERSION/README changes retained identical monitor, hardware, syntax-check and development-check derivations (3.88-second evaluation). Native `tam` built and passed its full test suite through `tam-dev` without installing a development override.

Focused results: development trials 8 tests; deployment 97; shell 86; candidate preparation 16; native staging 12; native compatibility 4; candidate transaction 10; operator stage integration 41. Transaction fixtures exercised local Git publication, frozen resume, interrupted writes/commits, conflicting edits and cancelled reservations. Registration of a development trial cannot take dirty work held by another session. Unknown command-check dependencies retain a full source snapshot; development header changes invalidate local checks. Promotion-hook fixtures also passed. The final development-command check passed again as an isolated Nix derivation after the dependency-closure fix.

Interactive keybinding, keyboard, plugin and shell preview processes remained running during their short smoke checks. A reversible live source-shell trial returned `pong`, retained the packaged shell endpoint and restored packaged IPC afterward. The live smoke check used the paired source IPC helper explicitly because the installed older helper lacks the new routing capability. These observations do not establish physical input, boot, energy or candidate acceptance. Concurrent desktop changes have their own verification; they were excluded from this change's immutable verification snapshot. No new candidate was prepared or deployed on the workstation.
