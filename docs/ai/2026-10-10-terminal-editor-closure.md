# 2026-10-10 — 0.4.3 terminal/editor package closure

- **CLI Tool**: Codex CLI `0.162.1` (live checked)
- **Model**: `gpt-6.1-sol` (local runtime/transcript checked)
- **Transcript**: Retained privately by the author.
- **Stage**: Develop; no candidate, pin, activation or promotion changed.

## Guiding prompt

> Think about what still needs to happen for Tamlinux 0.4.3. Prioritize a work plan so that the most impactful work gets done first, in a rational order that avoids rework. Make an implementation plan for a slice you can complete next, then do it. The goal is to get to a complete 0.4.3 I can test as soon as possible.

## Implementation and decisions

Added runtime dependency wrappers and same-output sibling resolution for the
nine new terminal/editor/default/presentation helpers. Declared those executables
in the clean Arch contract, extended isolated installed-output probes and retained
the repeated current-output audit plus immutable build/check identities.
Source pins and candidate version remain unchanged; the development snapshot's
baseline version string is not a newly prepared letter assembly.

## Verification

- The Nix command build runs all command checks, including 19 new installed-chain
  launcher regressions. Nix installed-component integration passes.
- 14 probes of real wrapped outputs pass with minimal PATH and isolated XDG state;
  host effects are recorded and buses deliberately unavailable.
- 17 existing audit regression tests pass. The current five-output audit has 103
  unresolved lexical command findings (from 108), no newly unresolved commands,
  54 inherited-name locations, and expected blocked-readiness exit status 1.
- The first offline build lacked a cached procps dependency and hit an unrelated
  bootstrap source hash failure; the declared Nix cache supplied procps for the
  successful build without changing source hashes or pins.
- [Evidence](../evidence/0.4.3-terminal-editor-closure.json) records snapshots,
  derivations, output paths, checks and the repeated audit.
- No clean-host, graphical/physical, migration or deployment acceptance is claimed.
