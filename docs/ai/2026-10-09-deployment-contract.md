# One deployment mechanism for Test and Run

- **Date**: 2026-10-09
- **CLI Tool**: Codex CLI (`codex`) `0.162.1`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Scope**: Documentation; no package implementation or activation.

## Guiding prompts

> While we are waiting for claude to finish, here's another concept I need you to understand and then make sure gets added to repo documentation and agent guidance: deploy. I don't want to be running random bits of code from some random local copy of a repo somewhere. I want to have a very disciplined and consistently reproducible deployment mechanism. Whether I say "deploy on my machine to test" or "deploy on my machine to run", the deploy endpoint mechanism should be the same. We are using nix and Home Manager to do this. When we deploy code to test, we take code from a test branch (or merge from a develop branch to a test branch and then take it from there) and put it into a flake that gets saved on tamlinux-packages. We should always package up our tamlinux software into a package to deploy it. Then it goes into a consistent place on my local machine, no matter where it all is coming from. It always lands in the same place. Can you understand this concept? Is anything unclear about how I want this to work?

> The deployment doc looks good. You can close the window. Please commit your work. I'll let you know when claude is done.

## Decisions and changes

Added `docs/deployment.md` and linked it from the README. Test and Run
install an exact package assembly recorded in this repository through Nix
and Home Manager, using the same managed runtime paths and services.
Branch names identify lifecycle stages; pinned revisions identify inputs.
Run uses the accepted Test assembly. Changed runtime payloads or recipes
require another Test.

The contract distinguishes stable installed interfaces from immutable Nix
store targets and requires package/generation identification, verification,
and recovery of mutable state. It records the current delivery gaps:
the shell module uses source input files rather than the existing package
output, and plugin payloads are supplied separately. Those gaps remain
implementation work; this session changed documentation only.

## Verification and acceptance

Reviewed installed paths and the stated gaps against `nix/modules/shell.nix`
and `nix/packages/default.nix`. Checked documentation links, whitespace,
and the public/private information boundary. The author reviewed the
contract in Micro and accepted it before requesting commits. No build,
service restart, branch promotion, deployment, or public push was performed.
