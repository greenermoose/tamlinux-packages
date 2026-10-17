# 0.4.4f hibernate package preparation

- **Date**: 2026-10-17
- **CLI Tool**: Codex CLI (`codex`) `0.163.0`, checked live
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted packaging and verification directed by Fred.
- **Prompt**:
  > I have reviewed, edited, and approved the plan. Close the review window and start work on Tamlinux 0.4.4f now.

Pin product `98eb75657942cd6645c28490190bc30d012fb070` and retain the other
component pins. Native package `0.4.4pre.f-0.1` installs the renamed drain
hook, records its source/recipe/archive digests, and declares its coreutils,
util-linux and awk dependencies. The native archive adds only the new sleep
hook and changes its integration manifest; existing login, boot, service and
FUSE payloads are byte-identical to the retained native package.

Verification: 122 delivery tests and all eight selected Nix outputs/contracts
pass. Native makepkg build, check and packaging pass. A fakeroot diagnostic
during packaging prompted an inspection of the final archive: every entry
has root ownership and the new hook is executable with the recorded source
hash. The product's 16 hook tests include a real timeout and restoration
retry; eight native-default tests verify modes, hashes and naming.

The [delivery record](../../deliveries/tamlinux-0.4.4-f.json) binds the native
archive and immutable outputs. [Readiness evidence](../evidence/0.4.4f-hibernate-readiness.json)
records the checks without claiming physical sleep acceptance. Test requires
Fred's instruction for the exact candidate; no activation, hibernation or
Test/Run branch movement was performed during preparation.
