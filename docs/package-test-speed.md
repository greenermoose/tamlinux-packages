# Package/Test speed

Tamlinux 0.6.6 focuses on cutting Package→Test machine time. Timing lives in
`improvements-fred-tamlinux/timing/`.

## Measured baseline (0.6.2–0.6.5)

Freeze sat at about 5.3–5.5 minutes. The Nix `assembly` phase was about
305–314 s (~95%). Build logs showed ~130 command-check derivations rebuilt
because most checks used `src = product`, so a VERSION bump invalidated them
all. Native archives and `tam`/`libtam`/`tamlinux-tools` already reused.

## What changed

1. **Instrumentation** — `prepare-candidate.py build` writes `rebuilds.json`
   (check/drv rebuild counts and top names) beside `build.log`. `fred-stage`
   copies a short summary into the timing ledger notes.
2. **Narrow check sources** — every command check uses a filtered
   `builtins.path` (`checkSource`). Multi-command integrators in
   `fullProductCheckNames` get `commands/` + `desktop/` + `share/` + LICENSE
   only (not VERSION/`docs/ai`), so candidate stamps do not rebuild them.
   Other checks list sibling commands in `extraCheckCommands`; desktop
   fixture checks list `desktop/` explicitly.
3. **Version-stable payloads** — `tamlinux-shell-payload-1`,
   `tamlinux-plugins-payload-1` and `tamlinux-commands-payload-1` exclude
   candidate VERSION stamps. Thin versioned wrappers only stamp metadata;
   the commands wrapper keeps derivation `.version` for assembly-contract.
   Shell payload filters must keep parent dirs (`share`) so `share/nftables`
   is reachable. Commands payload desktop filter includes only
   `desktop/assets`, `desktop/browser`, and `desktop/theme` so session/shell
   edits do not rebuild the ~130-command payload.
4. **Consumer prepare reuse** — `fred-stage prepare test` evals
   `activationPackage.outPath` first and reuses a realized store generation
   before calling `tam-deploy preflight` (0.6.9 restores this path; the
   earlier preflight-first branch skipped reuse).
5. **Deploy phase times** — `tam-deploy` records `phaseTimes` on successful
   install (preflight, realize, activate, shellRestart, verify, total).

## Acceptance path

Warm Package→Test after a small product delta should show assembly well under
100 s with `rebuilds checks=` far below ~130, and machine total under ~60 s
once prepare/deploy reuse lands in the measured run.
