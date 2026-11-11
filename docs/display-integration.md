# Display workspace package integration

The workspace helper's output-targeted action requires the paired native
corrections. Build and verify these before choosing a Test candidate. This
procedure never authorizes installation, session restart or a stage move.

The provider selection freezes Hyprland **0.56.2-4.2** and Aquamarine
**0.15.1-1.2**, their archive digests, exact recipes and all patch hashes.
The source commits are recorded in each recipe's `origins.json` and in
`contracts/providers/selection.json`. Existing DPMS, idle-inhibit and null
connector guards remain in the patch stack. The exported native logger
layout and upstream release identity are preserved for plugin compatibility;
archive digests distinguish the corrected builds.

Build the native packages with `makepkg` as the user. For Hyprland, set
`CMAKE_BUILD_PARALLEL_LEVEL` to a suitable number (default two). Build
Aquamarine first. A development root containing its library can be used via
`LD_LIBRARY_PATH` for the version-only entry and the synthetic logger proof;
no compositor or real DRM backend is started by those checks. The three
Aquamarine fake-backend tests are `attachments`, `output`, and `commitThread`.
The real-window test belongs to an explicitly scheduled trial.

After committing the product sources, build `tamlinux-shell` and
`tamlinux-plugins` plus `tamlinux-commands` from that exact revision through Nix. An integration build
may use `--override-input tamlinux git+file://...?...rev=<commit>` with
`--no-write-lock-file` against an immutable assembly revision. It does not
change an existing candidate or consume a version. Record both revisions
and the actual package output paths. Candidate preparation later freezes
the selected sources through its normal recorded assembly.

Run `python3 tools/check-display-integration.py` with:

- `--product`: the product Git repository containing the selected revision;
- `--plugins`, `--shell` and `--commands`: the three Nix output roots;
- `--hyprland` and `--aquamarine`: the selected native archives.

The check compares the packaged widget, shared queue, both helper entry points and backend
with the revision carried by the shell package. The only allowed content
transformation is Nix's standard Python shebang relocation, preserving `-I`
and every script-body byte. Native source
patches must match that same revision. It validates the archive and recipe
closure digests, `.PKGINFO`, `.BUILDINFO`, required files and correction/guard
markers in ELF payloads. Marker checks supplement reviewed local builds;
they do not prove behavioral correctness or authenticate untrusted builds.
The result is an integration receipt, with physical acceptance pending.

The local preparation retains the two selected archives and receipt in
`result-plan54-native/` (ignored build output). Source snapshots and build
trees can be removed after these identities are recorded. Do not retain
an unused `hyprpm` archive merely because the split recipe produced it.

Before Test, revalidate this receipt against the final committed assembly
and candidate packages. Record the previous user generation and the accepted
recovery anchor. Each native package transaction requires its own approved
step and a short pre-change Snapper rollback point. Any logout/login needs
its own approval. First verify the actual helper and compositor journal
routes and quiet idle, then perform the approved Dell switching matrix.
Source checks and a successful `--version` do not pass physical continuity.
Run and Release remain separate decisions.
