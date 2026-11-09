# Local fleet profile defaults

- **Date:** 2026-11-09
- **CLI Tool:** Codex CLI (`codex`) `0.167.0`
- **Model:** `gpt-6.1-sol`
- **Transcript:** Retained privately by the author.
- **Authorship:** AI-assisted implementation, tests and documentation under Fred's direction.

## Guiding prompts and approval

> Clean up exposed defaults and documentation. Suggest a change before you make it so I can review.

Fred approved moving the packaging tool's default follower profiles into local
operator configuration:

> Worth doing.

He clarified the intended boundary:

> What I want to do is have private information on my system and then the public tool can look there for it. So all the people who read the public repo see is that the public tool will look in a particular folder on your system. Is that how this will work?

## Implementation

The public preparation tool now reads `system/fleet-profiles.json` inside the
selected local consumer configuration. Actual follower choices remain outside
the public source. Generic documentation explains the file and gives example
profiles; existing explicit `--profile` options override local defaults.

The combined preparation command resolves profiles before checks, builds or
delivery recording, so a missing or invalid operator configuration cannot
freeze an incomplete candidate. Skipping follower preparation does not require
the file. Local terminal output and build receipts continue identifying the
selected profiles for the operator.

This is the approved portability change. Unrelated pathname cleanup, stage-host
selection, historical commits and other public/private findings are outside
its scope. No candidate reservation, Nix build, installation or stage move was
performed.

## Verification

Preparation tests cover operator-supplied defaults, explicit overrides without
valid defaults, malformed/missing files, early refusal before preparation,
and the existing skip path. A read-only lookup of the real local configuration
confirms the prior two follower choices are preserved without invoking Nix.
Build-invocation tests use a fake Nix executable and temporary consumers.

Results: **21 preparation tests passed**, including the new default-file and
failure-path cases. The full packaging repository suite passed **172 tests**
with host access. An initial sandbox run could not start the isolated GPG
provider-signing fixture; the host run exercised and passed that fixture.
No real Nix build or deployment was used for this verification.
