# Deployment contract

Deployment installs a reproducible Tamlinux package through Nix and Home
Manager. Test and Run use the same packaging, activation mechanism, installed
paths, commands, and services. Their source selection and acceptance differ.

Current product develop version is in [`VERSION`](../VERSION). Exact candidate
assemblies are recorded under [`deliveries/`](../deliveries/). Login is
[console-first](console-startup.md): no display manager is packaged. Stage
moves (Test, Run, Release) require Fred's exact word for that candidate.

## Select and record the assembly

For Test, select exact source commits on `test`. If the candidate is still
on `develop`, promote it to `test` on Fred's Test instruction before
selecting it. Branch promotion is fast-forward: it moves the selected commit
without creating a different merge commit.

Record the assembly in this repository's flake and lock file: exact component
revisions, content hashes, package definitions, and dependencies. Commit that
definition before deployment and identify the exact `tamlinux-packages`
revision on `test`. A branch name identifies the stage; the pinned revision
identifies the bytes. Deployment must not resolve a moving branch afresh.

`tools/prepare-candidate.py` performs these Develop steps one at a time:
`version` (next unused version), `pin INPUT=<commit>` (exact commits, checked
against the resolved lock), `build` (standard outputs and checks, without
links; evidence outside the repository), `record` (the delivery record from
the lock and build) and a read-only `check`. It never commits, promotes or
activates, never reuses a version and never overwrites a delivery record.

Build the Tamlinux package outputs from that recorded assembly. The consumer's
Home Manager configuration pins the exact delivery revision and selects its
package outputs and module. Machine-specific settings belong in the consumer
configuration; they do not supply alternate copies of Tamlinux software.

For Run, promote the accepted source and delivery commits to `main` and use
the same tested package assembly. Changing a source, dependency, package
recipe, or runtime payload creates a new candidate that needs Test again.
Test and Run do not have separate recipes or installation layouts.

From 0.4.5, candidate numbers are plain `X.Y.Z` (never reused for a changed
assembly). Released **0.4.8** is the Gate A recovery anchor; develop continues
on 0.5.

## Install through one endpoint

Home Manager activates the built package through the same managed locations
for both stages. The current module defines these desktop locations, with
the usual home and XDG defaults:

| Installed interface | Location |
| --- | --- |
| Shell runtime | `~/.local/share/tamlinux/shell` |
| Shell revision record | `~/.local/share/tamlinux/shell-revision` |
| Plugins | `~/.config/tamlinux/plugins/<id>` |
| Menu data | `~/.config/tamlinux/menu/` |
| Shell service | `tamlinux-shell.service` |

Packaged binaries are exposed through the managed command profile or the
module's declared command links. Launchers and services keep these installed
interfaces when the candidate changes. The immutable `/nix/store` target
changes with the package; the consumer-facing location stays the same.

Installed software must resolve to the recorded package outputs in the Nix
store. Deploying to test is a real package installation at the normal
endpoint. Local checkout links, copied working trees, temporary plugin
snapshots, and ad hoc source overrides do not satisfy this contract.
Developer checks of source code are useful evidence before deployment, but
do not constitute a deployed Test.

`tam-deploy` pins a `tamlinux-packages` revision for Test, verifies that
installed shell, plugins and commands resolve into the assembly's packages,
and for Run fast-forwards `main` without rebuilding. `tam-deploy init`
supports a first install on a registered host without a prior generation;
it never enables a display manager or starts a compositor.

## Verify and recover

Before activation, retain the current generation and package outputs and
record the exact delivery revision, component revisions, package paths, and
consumer configuration used to build the candidate. Keep mutable settings
and state recovery information alongside that record.

After activation, verify the installed commands, resolved shell and plugin
paths, service definition, and revision records against the selected
assembly. Report the Home Manager generation and any unresolved differences.
Passing build checks alone is not acceptance into Run.

Rollback activates the retained generation and its package through the same
installed interfaces. Home Manager generations preserve immutable software;
mutable user data and root-owned host files need their own documented recovery.

## Shell graphics on non-NixOS hosts

The default Quickshell provider wraps `bin/quickshell` with its locked Mesa
EGL vendor JSON and DRI directory. It saves any caller values and marks the
injected keys. The shell must implement graphics environment isolation at every
inheriting launch boundary; incompatible product versions fail the module assertion.
`bin/qs` remains the original IPC executable and must not start the shell.

This wrapper changes only the shell process environment. Child processes
receive the original caller settings. Hardware acceptance must show a real
hardware renderer without software overrides. VM OpenGL using a software
driver remains explicitly VM-only evidence.

## Historical notes

First-extraction, lettered 0.4.2–0.4.4, and SDDM login cutover documents are
removed from the working tree; see [FILING-CARD.md](FILING-CARD.md) and
[plans/FILING-CARD.md](plans/FILING-CARD.md). Do not treat them as current
guidance. Console login is described in [console-startup.md](console-startup.md).
