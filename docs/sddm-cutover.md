# Native-session login preparation

The native package supplies a Qt 6 SDDM greeter with visible username, session
and password controls. Its session ComboBox uses SDDM's `name` role and passes
the selected index to `sddm.login`. Keyboard and mouse selection are exercised
against the actual QML with a mock authentication endpoint. The upstream
[SDDM 0.21 theming API](https://github.com/sddm/sddm/blob/v0.21.0/docs/THEMING.md)
defines these roles and the login callback. Those tests cannot establish PAM,
hardware rendering or an actual native-session login.

The native recipe installs:

| Path | Purpose |
| --- | --- |
| `/usr/share/sddm/themes/tamlinux/Main.qml` | Greeter without inherited artwork or fonts |
| `/usr/share/sddm/themes/tamlinux/metadata.desktop` | Qt 6 theme metadata |
| `/usr/share/sddm/tamlinux-hyprland.lua` | Minimal greeter compositor configuration |
| `/usr/lib/sddm/sddm.conf.d/20-tamlinux.conf` | Generic theme/compositor defaults |
| `/usr/share/wayland-sessions/tamlinux.desktop` | Native launcher registration |

Account and automatic-login policy belong in the consumer's `/etc`
configuration. The package supplies no user account or automatic-login default.
It neither removes existing entries nor enables/restarts SDDM. Session command
names remain unchanged until an actual native-launcher login passes.

## First login candidate and later cutover

The first 0.4.4 candidate supplies the greeter, agent skills and a manual
login through the packaged native entry, with retained VT recovery. It keeps
the d native sleep-hook set, current boot settings and existing packages.
The developed zram-draining hook remains in product source outside the
installed defaults. Its physical sleep/resume trial belongs to a later letter.

A subsequent letter carries the coherent login-command rename and normal
automatic login. Boot/update/fallback, physical sleep/resume and package removal
have their own later transactions and evidence. Before removal (0.4.5), retain
a 0.4.4 candidate accepted in Run that works without inherited packages;
the older accepted package can still depend on those packages. Open native-login
and later-write rollback evidence carries forward rather than implying an
intermediate version was accepted in Run.

## Configuration precedence

SDDM reads `/usr/lib/sddm/sddm.conf.d`, then `/etc/sddm.conf.d`, then
`/etc/sddm.conf`. Later values override earlier ones. See the installed
`sddm.conf(5)` manual. Installing vendor defaults alone cannot replace an
existing local ThemeDir, CompositorCommand or Autologin selection.

Before Test, inventory all three locations, package ownership, all X11/Wayland
session search paths (including `/usr/local`), the selected user generation
and `/var/lib/sddm/state.conf`. Record exact bytes, modes, uid/gid, symlink
targets, package identities and absence. Keep checkpoints outside SDDM's
configuration directories. Bind the resulting maintenance configuration to
the exact native package and user generation; refuse changed inputs.

## Explicit maintenance transaction

This is a procedure to prepare and review before activation. An instruction to
develop a candidate does not authorize restarting the display manager.

1. Retain the old native package, user generation and a tested local VT login.
   Capture the configuration/state inventory above and a complete consumer
   source checkpoint. Save later writes separately before every restoration.
2. Stage a reviewed local override with the packaged ThemeDir and
   CompositorCommand. Clear **both** `Autologin.User` and `Autologin.Session`,
   and set `Autologin.Relogin=false`, for this maintenance test. Verify the
   override wins in all configuration layers. Preserve every old session
   entry and the old automatic-login settings in the checkpoint.
3. On explicit Test approval, install the exact packages/user generation and
   the maintenance override. From the retained VT, restart SDDM only after
   saving work. Select **Tamlinux (Hyprland)** in the visible Session control
   and authenticate. Confirm the SDDM journal selects the packaged
   `tamlinux.desktop`; a similarly named UWSM entry is insufficient.
4. Check launcher identity, hardware rendering, all-output surfaces, IPC,
   notifications, authorization and effective session configuration. Record
   exact runtime artifacts. If login fails, return to the VT, stop SDDM,
   archive the new configuration/state and restore original files, package
   and generation before restarting it. Never restore SDDM state while SDDM
   is running. Qt test-mode success alone does not pass this step.
5. After the actual native-session checks pass, prepare the coherent command
   rename and its updated package/generation. Any changed assembly needs its
   own candidate identity and Test. Stage the consumer's normal automatic
   login to `tamlinux.desktop`, retaining its intended user account. Retire
   duplicate local entries from consumer source, manifest and host together.
   Inspect/update saved `Last.Session` deliberately so a retired entry cannot
   return. The greeter honors SDDM's saved session; it does not silently force
   a different entry. Recheck normal login and retain the inverse transaction.

Boot/EFI recovery, kernel/initramfs update/fallback, physical sleep/resume,
later-write-preserving reference rollback and old-package removal require
their separate evidence. This greeter preparation closes none of those cases.

## Development checks

From the product checkout, run the actual interaction tests without a display:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QT_QPA_PLATFORMTHEME= \
  QT_STYLE_OVERRIDE=Basic /usr/lib/qt6/bin/qmltestrunner -input desktop/tests/sddm
```

From this checkout, `python3 -B -m unittest discover -s tests -p
'test_native_integration.py' -q` checks deterministic staging and executes
the actual recipe's `package()` in an isolated destination. For a Qt 6 SDDM
load check, run `sddm-greeter-qt6 --test-mode --theme <staged-theme>` with an
offscreen platform; inspect the log for QML errors before ending the process.
No login or power action is performed in SDDM test mode.

## Later login transactions: bounded shutdown and startup

`tools/login-transaction.py stop --user <account> --recovery-vt <VT>` stops
SDDM, then waits up to 60 seconds for both the account's Wayland sessions and
all its Hyprland processes to disappear. A query error or timeout fails the
step. The reviewed caller must stop there: do not apply login files or start
SDDM. This handles compositors that outlive SDDM's own stop timeout.

After the independently approved package/login-file steps, `start` with the
same arguments starts SDDM and waits up to 30 seconds for an active SDDM
Wayland login and Hyprland process. Failure stops SDDM and switches back to
the retained VT, including when the start command itself failed. Individual
state queries and service operations also have deadlines. Run these privileged
steps only from the verified recovery console after user approval. Keep all
checkpoints; these helpers do not restore files or select another generation.

The d user launcher also waits up to 30 seconds for active, activating or
stopping uwsm session units and any lingering compositor. It fails closed on
query errors. Its immutable `session/Hyprland` wrapper launches
`start-hyprland --path /usr/bin/Hyprland`, preserving uwsm's `Hyprland` service
ID and the `Hyprland` desktop name. The wrapper is package-owned. A startup
failure outside a maintenance transaction still needs the physical VT recovery
check; this is not a root greeter watchdog or physical acceptance proof.

## 0.4.4g PAM keyring transaction

The native package carries `/usr/lib/tamlinux/pam-transaction.py`, staged
from the exact Tamlinux product revision in the assembly. It manages only
`/etc/pam.d/sddm` and `/etc/pam.d/sddm-autologin`; the consumer tracks the
cleaned mirrors and `644` manifest entries, while the `sddm` package remains
the owner. The tool is part of the package payload and does not install either
mirror directly from a checkout.

Before a Test login step, use a verified text console, retain the current
native archive and Home Manager generation, and record the exact assembly and
consumer revisions. Capture `/etc/pam.d/sddm`, `/etc/pam.d/sddm-autologin`,
`/etc/sddm.conf`, all `/etc/sddm.conf.d` files, and
`/var/lib/sddm/state.conf` with hashes, modes, numeric owners and symlink
targets. Record `pacman -Q sddm gnome-keyring pam pambase`, current generation,
and the selected `tamlinux-packages` assembly. Keep that capture outside the
SDDM directories. Recheck package ownership and hashes immediately before the
transaction; a package update or `.pacnew` means the candidate must be
reviewed and reconciled before proceeding.

With Fred's approval for the login step, save work and use the bounded `stop`
procedure above. Once SDDM and the old compositor have ended, invoke the
packaged helper with absolute paths from the retained VT:

```sh
pkexec /usr/bin/python3 -I /usr/lib/tamlinux/pam-transaction.py apply \
  --checkpoint /var/lib/tamlinux/recovery/sddm-pam-0.4.4g
```

The tool accepts only the two exact baseline hashes and hook counts recorded
for candidate g. It creates a root-only checkpoint before changing either
file, writes each file atomically while preserving mode and uid/gid, and
records before/after hashes. A retry accepts only each file's recorded before
or after hash. It refuses when SDDM is active, a path is not a regular file,
or either baseline has drifted. Verify with `verify` before starting SDDM.

```sh
pkexec /usr/bin/python3 -I /usr/lib/tamlinux/pam-transaction.py verify \
  --checkpoint /var/lib/tamlinux/recovery/sddm-pam-0.4.4g
```

For rollback, first capture the current files separately and use a new
preservation directory. The inverse archives both current files and metadata
before restoring the checkpoint; it resumes safely if interrupted:

```sh
pkexec /usr/bin/python3 -I /usr/lib/tamlinux/pam-transaction.py restore \
  --checkpoint /var/lib/tamlinux/recovery/sddm-pam-0.4.4g \
  --preserve-current /var/lib/tamlinux/recovery/sddm-pam-0.4.4g-current
```

Keep the original checkpoint and preserved-current directory. Confirm the
restored hashes and start SDDM only through the separately approved `start`
step. A Home Manager rollback does not restore these root-owned PAM files.

After an SDDM upgrade, compare the package's new PAM defaults and any `.pacnew`
with both tracked mirrors and the recorded baseline. Preserve both versions,
re-review the exact hook count and hash, and prepare a new candidate if the
package defaults changed. Do not let `tam-sync` overwrite package defaults
blindly.

For each fresh login, test Secret Service with one uniquely attributed,
disposable item. This bounded probe stores a fixed non-secret marker, reads it
back, and deletes it; it never queries existing items. Record only pass/fail
and the session identifier, never the returned value:

```sh
set -euo pipefail
probe_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
probe_value="tamlinux-pam-probe-$probe_id"
probe_args=(tamlinux-pam-cleanup candidate 0.4.4g probe-id "$probe_id")
trap 'timeout 10s secret-tool clear "${probe_args[@]}" >/dev/null 2>&1 || true' EXIT
printf '%s\n' "$probe_value" | timeout 10s secret-tool store \
  --label="Tamlinux PAM probe $probe_id" "${probe_args[@]}"
result="$(timeout 10s secret-tool lookup "${probe_args[@]}")"
test "$result" = "$probe_value"
timeout 10s secret-tool clear "${probe_args[@]}"
trap - EXIT
```
