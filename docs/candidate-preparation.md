# Prepare a candidate

Use focused component tests while developing. Once the selected source is
committed, pinned and ready to package, run:

```sh
tools/prepare-candidate.py prepare --product ../tamlinux \
  --parent <40-character-assembly-revision> --scope "What this candidate changes"
```

This inspects versions and pins, runs the required default-theme, keybinding
and user-default checks on an archive of the exact product commit, builds all
ten outputs, verifies their availability, then writes the delivery record.
Native candidates also need `--extra <metadata.json> --native-archive <archive>`.
No step commits, pushes, promotes or activates software.

Progress names the current phase, elapsed time and log location. Evidence lives
outside the repositories under `$XDG_STATE_HOME/tamlinux/candidates/<version>`;
`--evidence` selects another directory. Repeating an interrupted preparation
reuses focused checks only when their input fingerprint matches. Nix reuses
valid output paths during every build, so completed outputs are not rebuilt.

The fingerprint includes VERSION, the flake and lock, Nix recipes, Python
preparation tools, required target names and focused-test policy. Changes to
any of these invalidate the evidence. Recording refuses missing checks, stale
evidence, partial target sets and unavailable outputs. Missing product history
is a failed consistency check. Additional metadata cannot replace mandatory
verification fields.

The separate `verify`, `build`, `record` and read-only `check` commands remain
available for diagnosis. `build --target` can build a subset, but that evidence
cannot freeze a candidate. The authoritative ten targets are `DEFAULT_TARGETS`
in the script: shell, plugins, commands, tam, libtam, tools, and the assembly,
installed-components, fresh-session and example contracts.

A successful record freezes the version. After that, use its committed assembly
for Test. A changed assembly needs the next candidate number; preparation never
rewrites an existing delivery. Workstation readiness and user authorization are
separate from package preparation.
