# Clean Arch/Hyprland installation contract — 0.4.3

The first independent desktop target is a standard `x86_64-linux` Arch host
with Hyprland. The [machine-readable contract](../contracts/arch-hyprland.json)
declares the native binary/service boundary, the five delivered package outputs
and the remaining ownership/proof requirements. This is a development contract;
the current assembly cannot yet install the complete desktop on a clean host.

## Host and delivery responsibilities

The host supplies its kernel, firmware, graphics/Qt/Wayland stack, systemd,
D-Bus, PAM, polkit and independently sourced Hyprland/Quickshell session.
The product currently calls native programs by absolute `/usr/bin` paths as
well as through PATH, so installing an equivalent tool only in a Nix profile
does not satisfy those absolute calls. The contract lists their native owners.
Quickshell must provide the QML modules imported by the shell; the selected
Hyprland build must implement the product's current Lua dispatch contract.
Record exact providers and capabilities before claiming independent delivery.
Package names observed on a reference installation alone do not prove which
independent channel supplies them on a fresh host.

Delivery supplies shell, plugins and product commands from one product revision,
plus the selected `tam` and `tamlinux-tools` outputs. The commands' wrapped
runtime dependencies remain in their Nix closures. Product source must also
supply compositor/session defaults, theme/background/fonts, application/editor
integration, browser registrations and required root integration. Consumer
configuration contributes values such as username/home, output choices and host
identifiers; it cannot provide missing implementations or inherited defaults.

NetworkManager, PipeWire/WirePlumber, BlueZ, authorization and portal facilities
need service-level proof. Optional power-profile controls must report unavailable
capability on a host without the daemon. The consumer selects independently
installed terminal/editor/browser applications and supplies their desktop entries.
Fresh login must import session environment into the user manager before the
shell's graphical-session unit starts. Neither a successful module evaluation
nor the illustrative [Home Manager example](../examples/home.nix) proves those
host facilities or complete desktop installation.

Machine IDs come from the host: existing UUIDs, mapper names and hostnames survive
upgrades; a fresh machine never inherits identifiers from another computer.
Native settings and boot/update/recovery changes require pinned package artifacts
and recovery records before activation. The contract's `pending` list prevents
missing resources or unproven behavior being hidden by a successful binary scan.

## Read-only output audit

Use actual built outputs, without adding the reference workstation's tools to the
search path. The auditor does not execute inspected files, enter a chroot, start
services, contact a server or change a package database:

```sh
python3 tools/clean-host-audit.py \
  --output shell=/nix/store/SELECTED-shell \
  --output plugins=/nix/store/SELECTED-plugins \
  --output commands=/nix/store/SELECTED-commands \
  --output tools=/nix/store/SELECTED-tools \
  --output tam=/nix/store/SELECTED-tam \
  > /tmp/clean-host-audit.json
```

Exit `0` means this inventory has no blockers, `1` means the JSON report contains
blockers, and `2` means invalid input or an inspection error. An omitted output
is a blocker. The current contract still has mandatory pending requirements,
so exit `1` is expected for the existing development outputs.

The audit inventories executable `bin` entries from only the supplied outputs;
it never accepts a command from the caller's PATH. It scans menu actions,
conditions and launcher arguments, shell/services/modules, plugin code and
packaged command bodies for custom-command references, inherited identifiers
and absolute host programs. Executable embedded plugin helpers are reported
separately: their presence does not establish correct invocation or PATH
resolution. Docs, tests, licenses and whole-line comments preserve ancestry and
are excluded. Inline comments, data strings and dormant code are conservative
review hits. The deferred Sway adapter's absolute `swaymsg` reference is recorded
separately and does not add a Sway requirement to this Hyprland target.
Non-UTF-8 compiled payloads are skipped by this text inventory; binary string,
shared-library and resolved QML-module audits still require their own checks.

Optionally add `--host-root /path/to/clean-arch-root` to inspect native executable
presence and the offline Pacman local database for forbidden inherited packages.
The image must contain `etc/arch-release`. Absolute image symlinks are resolved
inside that image, including directory links; the auditor's own `/usr/bin`
cannot satisfy an absent image binary. Optional missing binaries are reported
without failing that check. This does not validate package signatures/origins,
repository configuration, running services or the actual graphical session.

Run the regression check with:

```sh
python3 -B -m unittest discover -s tests -p test_clean_host_audit.py -v
nix build .#checks.x86_64-linux.clean-host-audit
```

That Nix check tests the auditor's negative cases; it is not a claim that the
selected assembly is clean-host-ready.

For a compact view of the same scan, add `--format compact`. Add
`--report /tmp/full-audit.json` to retain complete JSON evidence alongside it.
The summary groups unresolved lexical names by menu-only, shared and other
callers and reports every blocker category; the readiness exit status is
unchanged. A menu-only reference is not authority to retire its feature.
The 21 auditor regressions include compact/full evidence parity and failed
evidence-write handling.

## Measured baseline and next transfers

The [retained audit](evidence/0.4.3-clean-host-audit.json) covers the five actual
outputs used by the earlier 0.4.3 helper development check: 212 runtime files,
108 unresolved custom-command references and 54 inherited-name locations.
There are no unclassified absolute `/usr/bin` tool names in that snapshot.
These are lexical inventory counts, not 108 proven runtime dependencies or 54
independent defects. For example, a plugin's cache/service name can resemble a
command. References identify exact output-relative files and lines for review;
no source bodies or user state are recorded.

The [browser/menu follow-up](evidence/0.4.3-menu-launch-closure.json) records all
five exact outputs, 16 installed browser/focus regressions and 19 real-output
probes. It scans 245 runtime files, with 101 unresolved lexical names (103 after
the terminal slice), no new unresolved names and 54 inherited-name locations.
Browser defaults and webapp launch now resolve. Groups: 66 menu-only, nine shared,
26 other callers. The complete installed-component check and auditor Nix check
pass; this does not establish clean-host readiness. Agent adapters and control,
theme/assets/capture, session/native and migration/recovery chains remain pending.

The baseline exposes menu launches and settings, theme/font/background support,
capture helpers, audio/network/power controls, reminders and plugin display or
location setters that are not yet in the supplied `bin` outputs. Active inherited
names include menu actions/font identities, desktop-mode values and user-visible
text; compatibility data and development proof paths also require classification.
The next implementation work should establish maintained product components and
package closure for these caller chains, with theme/default assets alongside
their paired consumers. Re-run against fresh outputs after each transfer.

## Installation proof still required

Prepare a complete exact assembly, install it on a clean Arch host that never had
the inherited distribution, and retain the independent package/source manifest.
Prove startup/login, menus and all eight plugins; notifications/reminders;
theme/background/fonts and application/editor/browser workflows; screenshot,
recording, OCR/QR; authorization, portals and hardware panels. Block inherited
domains/repositories and observe that no request or fallback is attempted.
Verify native update/boot/recovery and sleep/resume for any changed root package.
Record immutable and mutable rollback evidence before reference-machine Test.

Static checks are useful gates, but cannot replace this installation evidence.
No desktop was activated by this work; Test, Run and Release remain explicit
stage transitions.

The [product plan](https://github.com/greenermoose/tamlinux/blob/develop/docs/plans/non-theme-compatibility.md)
now fixes nine acceptance checks (I01–I09): artifact/source identity, native
ownership, delivered software, effective runtime, network independence, data
migration, baseline behavior, native update/recovery and promotion/rollback.
Their result must bind every required pass and evidence digest to one artifact
tuple. The contract enumerates those IDs; complete aggregation/collectors remain
pending. The 108/54 inventory supports part of I03 only.

The plan also requires a pinned host image/native snapshot and staged offline
installation, observation of attempted inherited network requests, a per-interface
rename/migration table, upgrade/rollback proof preserving new user writes, fixed
0.4.2-d parity and a bounded capture-defect admission rule. These refine the
already agreed 0.4.3 scope; they do not establish a completed clean-host recipe.

## Network/power and paired settings follow-through — 2026-10-12

[Control delivery evidence](evidence/0.4.3-control-closure.json) records 20 added
command entries (19 retained controls and a preservation helper), wrapped clients,
GTK schemas/dconf backend and declared native service/privilege owners. DNS
preserves paired root files and profile fields; text size and user settings retain
originals before writes. Shell/CLI Stay Awake share the XDG path and preserving
writer. 64 staged helpers, 18 service checks, 21 auditor regressions, Nix
build/integration and 42 real-output probes pass; five cases reject original code.

Audit: 307 runtime files, 75 unresolved lexical names, 51 inherited locations, no
missing outputs/files or undeclared absolute tools. Nine pending requirements and
absent clean-host inspection keep readiness false. Privileged DNS, native service
recovery, physical radios/displays, migration and new-user-write rollback remain
unproven. Snapshot identities precede documentation; no pin or activation changed.
[Source/recovery inventory](https://github.com/greenermoose/tamlinux/blob/develop/docs/plans/0.4.3-control-closure.md)
tracks the next brightness/display/lock/suspend, theme/assets/capture and
session/native/complete-install work.
