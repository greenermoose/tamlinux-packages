# First extraction verification — 2026-10-09

The pinned public inputs were fetched from GitHub. `nix flake check` built all
seven checks successfully:

- libtam: source tests and staged library/header installation.
- tam: command behavior and offline guide source tests.
- tamlinux-tools: dynamic linkage, argument errors and source tests.
- tamlinux-shell: immutable shell payload and revision/version metadata.
- developer-baseline: compile, link and execute a C program using libc; tool
  availability and certificate bundle.
- example-contract: generic Home Manager construction, public user paths,
  developer baseline and explicit protocol-trial selection.
- installed-components: installed offline guide, file selector errors, and a
  separately compiled consumer of the installed library/header.

The first tools check exposed an unmapped `/usr/bin/env` test interpreter in
the build sandbox. Recipes now patch test shebangs before building; the corrected
source and installed-package checks passed. No component source was modified.

`tests/portability.py` checks public source for private repositories, workstation
paths and local flake input URLs. The public example uses an illustrative user
and needs no private source. These checks establish build/installed component
behavior; they do not establish complete desktop host integration, boot/network
acceptance, daily use, or rollback proof. See [scope and limits](first-extraction.md).

## 0.4.2-d assembly verification — 2026-10-10

All Nix flake checks passed against the pinned d product, including 36
deployment command tests, the existing plugin/work coordination checks, seven
actual packaged plugin storage tests, component installation and the generic
Home Manager example. The assembly contract proves explicit plugin selection
is recorded and excluded payloads remain absent. Public portability and
provenance checks passed. These checks prepare d for physical Test; they do
not activate it or establish acceptance.
