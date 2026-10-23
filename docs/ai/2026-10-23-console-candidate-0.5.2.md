# Console-startup 0.5.2 assembly preparation

- **CLI Tool**: Codex CLI (`codex`) `0.164.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted candidate preparation directed by Fred.
- **Commit**: The commit introducing this record contains the assembly.
- **Prompt**:
  > Prepare Tamlinux 0.5.2 with the verified console-startup fixes. Keep Test separate.

Prepare 0.5.2 from product `f77a8c7034d7cec136258594d73dece23f70afd8`,
including the verified finite recovery fix for explicit shared and host source
roots. Other component pins remain unchanged from 0.5.1. Earlier delivery
records and retained native artifacts remain unchanged.

All nine package/contract outputs build, including fresh-session,
installed-components and example-contract. All 79 focused product tests,
nine candidate-tool tests, ten native-staging tests and seven boot-checkpoint
tests pass. A probe through the actual packaged checkpoint CLI verifies both
source roots and mutable links, preserve/status/restore/retry, missing-root
refusal, later-write retention and original file modes. It uses isolated
HOME/XDG paths and never checkpoints or restores live settings.

The native 0.5.2 archive builds through makepkg build/check/package. `--nodeps`
skips its initial dependency check; `pacman -T` separately confirms all actual
archive dependencies on the preparation host. Archive inspection finds no
SDDM/Plymouth dependency, greeter or chooser files, and its recovery payload
matches the pinned product source exactly. The source, recipe and archive
hashes are bound in the [delivery record](../../deliveries/tamlinux-0.5.2.json).
Their retained private copies are required by the later native procedure;
disposable source snapshots, build trees and probe fixtures are removed.

Test remains separate. No stage promotion, user activation, live checkpoint,
native installation/removal, boot/login mutation or reboot occurred. Fresh
settings/audio/boot and root checkpoints, exact Test authorization and
individually approved native steps remain pending. Build checks do not prove
text boot/unlock, VT locking, desktop lifecycle, physical recovery or timings.
