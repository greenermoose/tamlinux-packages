# Deployment contract

Deployment installs a reproducible Tamlinux package through Nix and Home
Manager. Test and Run use the same packaging, activation mechanism, installed
paths, commands, and services. Their source selection and acceptance differ.

This is the required delivery contract. Implementation status is recorded below.

## Select and record the assembly

For Test, select exact source commits on `test`. If the candidate is still
on `develop`, promote it to `test` on the user's Test instruction before
selecting it. Branch promotion is fast-forward: it moves the selected commit
without creating a different merge commit.

Record the assembly in this repository's flake and lock file: exact component
revisions, content hashes, package definitions, and dependencies. Commit that
definition before deployment and identify the exact `tamlinux-packages`
revision on `test`. A branch name identifies the stage; the pinned revision
identifies the bytes. Deployment must not resolve a moving branch afresh.

Build the Tamlinux package outputs from that recorded assembly. The consumer's
Home Manager configuration pins the exact delivery revision and selects its
package outputs and module. Machine-specific settings belong in the consumer
configuration; they do not supply alternate copies of Tamlinux software.

For Run, promote the accepted source and delivery commits to `main` and use
the same tested package assembly. Changing a source, dependency, package
recipe, or runtime payload creates a new candidate that needs Test again.
Test and Run do not have separate recipes or installation layouts.

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
mutable user data needs its own documented recovery procedure.

## Implementation status

Implemented on 2026-10-09: the Home Manager module installs only package
outputs of the recorded assembly. `tamlinux-shell` carries the shell, menu
defaults, `tam-menu` and the protocol shadow trial; `tamlinux-plugins` and
`tamlinux-commands` carry the plugin payloads and product commands from the
same product revision, and the module refuses packages from different
revisions. Separately supplied plugin payloads and direct source links are
gone. The `tam-deploy` command pins a `tamlinux-packages` revision on `test` in
the consumer lock for Test, verifies that the installed shell, plugins and
commands resolve into the assembly's packages, and for Run fast-forwards
`main` without rebuilding. A fixture-based check proves the installed paths.

The packaged 0.4.1 assembly was tested, run and released on 2026-10-09.
The next Develop candidate selects the owned-menu implementation at product
`0.4.2-a`. Its Nix shell, plugin and command package names use `0.4.2pre.a`,
which sorts between 0.4.1 and 0.4.2; the declared product version stays
`0.4.2-a`. The assembly fixture checks both spellings and their ordering.
The consumer's installed version must come from the selected assembly.

The owned menu directory is one Home Manager link into an immutable directory
containing the packaged defaults, an optional personal extension, and an
optional launcher-filter link. This replaces earlier whole-directory links
without writing through them into a source checkout. Only the launcher filter
may be mutable; defaults and extension are fixed inputs to the generation.

The 0.4.2-a candidate still needs promotion to Test and physical acceptance.
