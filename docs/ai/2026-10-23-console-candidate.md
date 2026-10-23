# Console-first 0.5.1 assembly preparation

- **CLI Tool**: Codex CLI (`codex`) `0.164.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Prompt**:
  > We are working toward text-only boot for Tamlinux 0.5 Blue Sparkler. Take the next step to make this happen.

Prepare 0.5.1 from product `7c0d8d7de36a470ea357b6cb36b7fc7948fe7d4d`,
retaining the earlier 0.5.0 delivery record. All other component pins remain
unchanged. The assembly carries the guarded explicit desktop launcher,
finite terminal-theme migration and native package without graphical-login
integration. The native recipe version advances to match this candidate.

All nine requested package/contract outputs build, including fresh-session,
installed-components and example-contract. Nine candidate-tool, ten native
staging and seven boot-checkpoint tests pass; all 49 focused product tests
pass. `makepkg --nodeps --nosign --noconfirm` passes build/check/package;
its actual archive contains no SDDM/Plymouth dependency, greeter or session
chooser. All archive dependencies are satisfied on the preparation host.
`--nodeps` skips makepkg's initial dependency check, not the build or checks.

The [delivery record](../../deliveries/tamlinux-0.5.1.json) records all exact
outputs and native source/recipe/archive hashes. The archive and its frozen
source/recipe are retained privately for the pending native Test transaction.
Host recovery retains its existing exact package and accepted routes.

No package is installed, no stage advances and no boot/login setting changes.
Fresh user/boot checkpoints, a root snapshot, exact Test and individual native
step approvals remain prerequisites. Generated text-boot images and physical
boot/unlock/VT/locking/desktop/timing acceptance remain pending.
