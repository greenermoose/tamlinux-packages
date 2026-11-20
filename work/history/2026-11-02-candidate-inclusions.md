# Record inclusions before candidate preparation

- **Date**: 2026-11-02
- **CLI Tool**: Codex CLI (`codex`) `0.166.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.

## Prompts

> I want to be able to later say, "Package up and test Tamlinux x.y.z" to actual start testing that version of Tamlinux on my workstation.

> Make it so.

> Improve the inclusion helper so tam inclusion requests for tam version x.y.z (p.d.q) work. I'll use the same version format, command version (corpus version), as the tam command uses itself in its footer line.

The developer approved separating record-only inclusion from a later explicit
Package/Test request, extending the existing workflow and adding regression
checks. Codex implemented the changes.

## Changes

- Accept named-version combined requests and reject conflicting or used numbers.
- Freeze requested contents with the candidate and its delivery record.
- Check source ancestry and installed artifacts so old source pins or recipe
  entries alone cannot satisfy inclusion.
- Preserve interrupted preparation and frozen output reuse.
- Preserve explicit tam command/corpus constraints and reject a different
  selected or built pair, independently of development corpus overrides.

## Verification

The package integration suite passed 163 tests. The final 19 workflow tests
cover prompt scope, named versions, old pins, missing or non-executable artifacts,
complete preparation, exact command/corpus source and package checks, and
unchanged resume. Fixtures use temporary
Git repositories and a fake Nix executable; they never activate software or
establish real workstation Test acceptance.
