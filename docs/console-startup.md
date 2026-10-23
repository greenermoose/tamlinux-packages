# Console-first delivery

Tamlinux 0.5 develops a visible text boot and explicit desktop launch. The
selected minimal root-stock and `tam-nut` provide the starting environment;
this work does not redesign their upstream boot media or firmware. The
managed startup policy applies after choosing Tamlinux to boot.

The native integration recipe no longer depends on SDDM, installs greeter
assets or registers a graphical session chooser. Its `tam-session` command
is an explicit compatibility entry into the installed `tam-desktop` endpoint.
The old SDDM PAM repair remains historical source; it is not packaged.

The user session module delivers `tam-desktop` when the selected product
supports it. It is a console command, not a login/profile hook. The shell,
portals and desktop agents must follow the user graphical-session lifecycle,
not ordinary text login. A Home Manager activation does not enable graphics.

Host boot configuration remains a native-system responsibility: select
`multi-user.target`, retain VT1 and a recovery VT, remove display-manager
startup, remove Plymouth and graphical boot files, and enable normal early
kernel/initramfs and service progress. Text encrypted-root unlock, keyboard,
keymap/font, generated boot images and recovery must be checked together.
GPU/KMS support for a text framebuffer and optional desktop remains installed.

Migration is not a recursive package purge or a direct edit of `/usr`.
Install the recorded replacement native package, prepare and inspect text
boot images, and remove the reviewed display-manager/splash packages through
the native manager. Preserve shared libraries and existing recovery routes.
Each boot, login or removal step needs its own approval and rollback point.
Do not stop a running desktop merely to prepare next-boot configuration.

Prove the first workstation before trying the second. Require text boot and
unlock, a useful terminal with agents, direct desktop startup/exit, repeat
start, locking/VT recovery, and baseline plus three cold-boot timings. Keep
those observations bound to their exact installed assembly; source/package
checks alone do not pass physical startup acceptance.

Product design: [console-first startup](https://github.com/greenermoose/tamlinux/blob/develop/docs/plans/console-first-startup.md).

The explicit launcher now holds the originating text shell until graphical
shutdown is confirmed, blocks keyboard suspension, discards queued input and
restores terminal settings on return. Another VT provides text work and
recovery while the desktop runs. Existing upgraded terminal configurations
also need the finite theme-include migration; fresh defaults alone do not
replace an inherited application file. Preview and apply with the installed
operator and a new journal, preserving personal settings and originals.

The guarded launcher and migration are pinned and pass the fresh-session,
installed-components and example checks. A probe of the real packaged
migration passes apply/retry/rollback in isolated XDG roots for four terminals.
[Sources and results](ai/2026-10-23-console-terminal-guard.md).
These Develop builds do not replace or modify the earlier 0.5.0 candidate
record; the next prepared assembly needs a new number.

Develop verification on 2026-10-23: the final product pin's fresh-session
contract passes; 15 console/session/native-entry tests, 56 deployment tests,
10 native-staging tests and eight native-collector tests pass. A native Arch
archive builds and passes file-list/dependency inspection. These checks do
not establish physical boot or desktop-locking acceptance.
[Exact sources and build results](ai/2026-10-23-console-first-startup.md).

Candidate 0.5.1 now binds the guarded launcher, terminal migration and rebuilt
native package in its [delivery record](../deliveries/tamlinux-0.5.1.json).
All nine package/contract targets and the actual native archive pass their
preparation checks. Exact Test and individually approved host steps are still
required; no physical boot or installed-removal result is claimed.

Candidate 0.5.2 delivers the verified multi-root settings checkpoint operator;
its [delivery record](../deliveries/tamlinux-0.5.2.json) binds all nine built
outputs and the rebuilt native archive. The actual packaged operator passes
an isolated shared/host source-root round trip with later writes retained.
0.5.1 remains unchanged. Preparation leaves Test separate; capture new live
checkpoints with this exact packaged operator before any approved activation.
[Preparation evidence](ai/2026-10-23-console-candidate-0.5.2.md).
