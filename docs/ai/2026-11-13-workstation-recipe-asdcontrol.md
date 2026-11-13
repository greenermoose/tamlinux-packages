# Drop required `/usr/bin/asdcontrol` from workstation bundle recipe

Removes `needs file /usr/bin/asdcontrol arch=asdcontrol` from
`recipes/workstation/bundle` because `asdcontrol` is not packaged as a
separate rootstock Arch package on workstation hosts, while preserving the
optional `/usr/lib/tamlinux/asdcontrol` -> `/usr/bin/asdcontrol` rewrite in the
product layout installer for hosts that provide it.

Verification: rebuilt the format-2 workstation bundle from exact committed
sources and re-ran `tamlinux-packages` bundle and workflow unit suites.

- **Date:** 2026-11-13
- **CLI Tool:** Antigravity CLI (`agy`) `1.5.8`
- **Transcript:** Retained privately by the author.
- **Authorship:** AI-assisted packaging recipe update and documentation.

## Guiding prompts

> 2 adjust recipes for asdcontrol
