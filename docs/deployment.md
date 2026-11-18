# Deployment contract

Deployment installs a recorded tam-bundle assembly. Test and Run install the
same bundle bytes at the same locations, with the same commands and
services; only their source selection and acceptance differ. Nix and Home
Manager were the previous delivery and are being retired: `tam-deploy
return-nix` keeps a saved Nix generation reachable until then.

Current product develop version is in [`VERSION`](../VERSION). Exact candidate
assemblies are recorded under [`deliveries/`](../deliveries/). Login is
[console-first](console-startup.md): no display manager is packaged. Stage
moves (Test, Run, Release) require Fred's exact word for that candidate.

## Select and record the assembly

"Package and test Tamlinux V" runs `tools/candidate-workflow.py` (through
`fred-stage`). It selects the `develop` revisions of every component and the
recorded inclusions, then:

1. pins them in `recipes/workstation/tamlinux.lock` and renders
   `notes/tamlinux-V.txt`, committing both with the recipe that packs those
   notes;
2. builds, verifies and packs the bundle with `tam-bundle`, refusing one whose
   packed version notes are not V's;
3. records `deliveries/tamlinux-V.json`: the recipe commit, each component
   revision and the archive hash. The archive is cached under
   `~/.cache/tamlinux/bundles/`.

A recorded version is frozen. Changing a source, dependency, recipe or payload
creates a new candidate with the next unused number, which needs Test again.
Run promotes the tested delivery without rebuilding it. From 0.4.5, candidate
numbers are plain `X.Y.Z`.

## Rehearse a Make delivery

After `make` in the product checkout, `make source-delivery` reads the
verified stage and emits a format-1 `source-install` record for
`deliveries/tamlinux-V.json`. The record pins the cultivar version, Arch
rootstock and Git revisions. Each rehearsal uses a disposable delivery
checkout and an isolated Arch root.

Use `fred-stage prepare test V --source-stage PATH --source-root PATH` with
the actual digest-named stage directory. For bundle migration, add
`--rollback-version V --bundle-archive PATH` with the existing bundle's
recorded version and matching archive. Preparation verifies the pinned
source lock, payload, native prerequisites, destination ownership and
recovery baseline. It records the host and the exact manifest SHA-256.
`fred-stage plan test V` repeats those checks and displays the rehearsal
digest. The two commands leave the target root and its installed settings
untouched. Live Test, Run and Release continue to use the current bundle
procedure.

## Install through one endpoint

`tam-deploy` verifies the archive and migration profile (`prepare-console`)
and writes short checksum-bound activation and undo scripts for the console
(`console-helpers`). The privileged `tam-bundle install` stages the version
under `/usr/lib/tamlinux/version/tamlinux-V-<hash>/`, `tam-bundle apply`
switches `/usr/lib/tamlinux/current` to it, and `tam-deploy activate-bundle`
finishes settings and checks at an inactive desktop.

| Installed interface | Location |
| --- | --- |
| Commands | `/usr/bin/` |
| Shell runtime | `/usr/lib/tamlinux/current/share/tamlinux/shell` |
| Plugins | `/usr/lib/tamlinux/current/share/tamlinux/plugins/<id>` |
| Version and notes | `/usr/lib/tamlinux/current/share/tamlinux/version`, `version-notes.txt` |
| Shell service | `/usr/lib/systemd/user/tamlinux-shell.service` |

Deployment installs and verifies the recorded bundle at its system paths.
Verify packaged commands by their installed paths under `/usr/bin`. User
commands in `~/.local/bin` can coexist with the bundle, and each user’s
`PATH` determines what a command name runs.

## Verify and recover

`tam-bundle status` shows the live and previous bundles and their hashes;
`tam-deploy status` shows the recorded assembly and stage. After activation,
verify the installed commands, shell, plugins, service and version against
the delivery record. Passing build checks alone is not acceptance into Run.

The previous bundle stays installed. `tam-deploy recover <ID>` returns that
exact bundle and the settings captured at the switch; it never guesses a
previous version. Mutable user data and root-owned host files need their own
documented recovery.

## Shell graphics on non-NixOS hosts (Nix delivery only)

Bundles run the host's native Quickshell. For the retiring Nix delivery, the
default Quickshell provider wraps `bin/quickshell` with its locked Mesa
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
