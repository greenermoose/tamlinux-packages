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
The next Develop candidate is **0.4.2-d**, superseding the recorded c Test
assembly without changing its identity. Its shell, plugin and command package
names use `0.4.2pre.d`, which sorts between 0.4.1 and 0.4.2; `VERSION` keeps
`0.4.2-d`. A changed candidate uses the next unused version: plain patch numbers
from 0.4.5 (D178); the 0.4.4 series keeps letters until one is accepted for Run. The fixture checks
candidate spelling and version ordering; the consumer version comes from the
selected assembly.

The module records the selected plugin IDs and product revision at
`~/.local/share/tamlinux/deployment-selection.json`. `tam-deploy` evaluates the
committed assembly's exact package outputs, rejects missing/broken endpoints,
and compares shell, selected plugins, all product commands, menu defaults,
`tam-menu`, tam, `tam-man` and file-select with those outputs. A package name or
matching revision text alone cannot prove that an endpoint belongs to the
assembly. The selection record supports explicit plugin subsets. Older
assemblies without it are verified against the full plugin set.

Both deployment and rollback identify the active assembly from its matching
generation record, so a consumer lock prepared for a future candidate cannot
become the return pin for an earlier generation.

The owned menu directory is one Home Manager link into an immutable directory
containing the packaged defaults, an optional personal extension, and an
optional launcher-filter link. This replaces earlier whole-directory links
without writing through them into a source checkout. Only the launcher filter
may be mutable; defaults and extension are fixed inputs to the generation.

The 0.4.2-d candidate is prepared on `develop`. Promotion to Test, installation
and physical acceptance remain pending the user's Test instruction.

## Shell graphics on non-NixOS hosts

The default Quickshell provider wraps `bin/quickshell` with its locked Mesa
EGL vendor JSON and DRI directory. It saves any caller values and marks the
injected keys. The shell must implement graphics environment isolation at every
inheriting launch boundary; incompatible product versions fail the module assertion.
`bin/qs` remains the original IPC executable and must not start the shell.

This wrapper changes only the shell process environment. It does not set the
user manager environment or create a global `/run/opengl-driver` link. Child
processes receive the original caller settings, including explicit empty values.
`tools/probe-launch-environment.py` exercises the production Commons helper with
real offscreen Process and detached children; rendering requires separate proof.
Hardware acceptance must show a real hardware renderer without software overrides.
VM OpenGL using a software driver remains explicitly VM-only evidence.

The shell unit enables Qt startup renderer information (`QSG_INFO=1`). The
runtime collector verifies that PID's context and layer surfaces, rejects
software overrides, and supports `--renderer-token` for host-specific GPU
assertions. Use `--graphics-mode vm` only for virtual-driver evidence. To
verify notification surfaces, show a popup first and use `--require-notifications`;
the collector remains read-only and will not create one itself.

## Native login command transition (0.4.4-c)

Candidate c installs `/usr/bin/tam-session` through its paired native recipe
and `~/.local/bin/tam-hyprland-session` through the session module and shell
output. The old executable names are removed, while session data remains
`tamlinux.desktop`. Install the native and user sides in one stopped-session
maintenance transaction. Update a curated session entry at the same time.
The vendor package supplies no user account or automatic-login policy.

Keep the previous native package and user generation before starting Test.
A consumer changing automatic login must checkpoint its effective SDDM
configuration, saved session state and local registrations with SDDM stopped.
Retire obsolete registrations explicitly and preserve the saved user's other
state. On rollback, save later writes before restoring the previous package,
user generation and login files. `tam-deploy back` alone cannot restore those
root-owned files. Physical automatic login, manual logout/login and recovery
are required observations; static checks do not establish them.
