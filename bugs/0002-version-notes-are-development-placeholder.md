# Bug 0002 — Bundle installs show no version notes

- **Status:** Confirmed.
- **Severity:** Medium; the version widget shows nothing about what
  changed in the version under test.
- **Affected:** Workstation bundle deliveries 0.6.27 and 0.6.28
  (`recipes/workstation/bundle`, `tools/candidate-workflow.py`).
- **Fixed:** None yet. Proposed for 0.6.29.
- **Next:** Render the version notes before `tam-bundle build`, pack those
  notes, and fail the build when the packed header names another version.

## Reproduce

Read `share/tamlinux/version-notes.txt` from an installed 0.6.27 or 0.6.28
bundle. Its first line is `Tamlinux 0.6.20-dev`, the content of
`notes/tamlinux-development.txt`. The committed `notes/tamlinux-0.6.28.txt`
starts with `Tamlinux 0.6.28 version notes` and lists the changes, but it is
not in the bundle.

## Expected and actual

Expected: the bundle carries `notes/tamlinux-<version>.txt`, and
`fred.tamversion` shows it.

Actual: two independent faults.

1. `recipes/workstation/bundle` hard-codes
   `file notes/tamlinux-development.txt tree/share/tamlinux/version-notes.txt`,
   so every bundle packs the development placeholder.
2. `CandidateWorkflow._prepare_bundle()` renders and writes
   `notes/tamlinux-<version>.txt` only after `tam-bundle build`, `verify` and
   `pack` have finished, so the rendered notes could not be packed even if
   the recipe named them.

`fred.tamversion` 0.1.5 checks that the notes header matches the installed
version and correctly hides stale notes, so it shows none.

## Workaround

Read `notes/tamlinux-<version>.txt` in this repository.

## Fix and verification

Proposed:

1. In `_prepare_bundle()`, render `notes/tamlinux-<version>.txt` before the
   build and keep the existing review step on it before Test.
2. Build from a temporary copy of `recipes/workstation` whose notes `file`
   line names `notes/tamlinux-<version>.txt`, or add the version-specific
   line to the pinned recipe in `pin-bundle`. Keep
   `notes/tamlinux-development.txt` for development builds only.
3. After `tam-bundle verify`, read `tree/share/tamlinux/version-notes.txt`
   and stop if its first line is not `Tamlinux <version> version notes`.
4. Test in `tests/`: a candidate build packs notes whose header matches the
   version, and a placeholder header fails the build.

Acceptance: after installing 0.6.29, `fred.tamversion` shows the 0.6.29
notes.

## Resolution

Open.
