# Blue Sparkler 0.5.0 fleet and first-install assembly

- **Date**: 2026-10-23.
- **CLI Tool**: Codex CLI (`codex`) `0.163.0`, dynamically checked.
- **Model**: `gpt-6.1-sol`.
- **Transcript**: Retained privately by the author.
- **Prompt** (excerpt; private machine name redacted):
  > - Package the fleet tools and supported first-install handling; activate [redacted: personal detail]’s host profile.

## Assembly

Pin product `96de179db1048feefca064627b678d0b72051bce` and preserve the other
released component pins. Record version 0.5.0 with the source's Blue Sparkler
cultivar. Build the shell, plugins and commands plus installed-component and
example-profile contracts. The exact delivery record binds the lock and built
outputs; no installation, branch promotion or native package removal is part
of this development step.

The product carries the fleet workflow, registered-host selection and text
first-install support. Consumer account fixes, native boot policy and optional
feature selections remain separate. Physical and two-machine reconciliation
acceptance require the user's subsequent Test instruction.

## Verification

All five prepared targets built: shell, plugins, commands, installed-component
contract and example-profile contract. Installed probes include fleet/deploy
help and the bootstrap welcome with a deliberately minimal PATH. The build
caught and fixed a bootstrap PATH assumption; the delivery recipe now supplies
coreutils, awk, lsblk and PCI inspection providers explicitly.

Source regressions: 56 deployment, 18 fleet and two bootstrap tests pass. Consumer
regressions: four host-configuration tests pass. No physical acceptance or
reconciliation timestamp is inferred from these checks.
