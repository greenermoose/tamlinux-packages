# Bug 0002 — Bundle installs show no version notes

- **Status:** Fix available.
- **Severity:** Medium; the version widget shows nothing about what
  changed in the version under test.
- **Affected:** Workstation bundle deliveries 0.6.27 and 0.6.28
  (`recipes/workstation/bundle`, `tools/candidate-workflow.py`).
- **Fixed:** In source on `develop`; planned for 0.6.29, not yet installed.
- **Next:** After installing 0.6.29, confirm `fred.tamversion` shows its notes.

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

`tam-bundle build` reads the recipe and its `file` sources from the packaging
commit, so the notes must be committed before the build.
`tools/candidate-workflow.py` now does this in the `pin-bundle` step:

1. It renders `notes/tamlinux-<version>.txt` and points the recipe's single
   `file ... tree/share/tamlinux/version-notes.txt` line at it
   (`point_bundle_notes`), then commits both with `VERSION` and the lock.
2. After `tam-bundle verify`, the build stops unless the packed
   `version-notes.txt` is exactly the rendered notes.
3. The later preparation commit checks that the notes did not change after
   the build, instead of writing them for the first time.

Consequence: the notes are part of the bundle. Review them before Test from
the `Pin Tamlinux <version> bundle recipes` commit; a wording change after
that needs a new build. `notes/tamlinux-development.txt` remains for manual
development builds, but the recipe now names the last candidate's notes.

Regression checks in `tests/test_candidate_workflow.py`: the fake
`tam-bundle build` now packs the recipe's `file` entries from the committed
packaging `HEAD`, as the real tool does. The bundle test asserts the pinned
recipe and the packed notes. A new test, which packs the placeholder, must be
refused before any delivery record is written. Both fail on the previous
workflow, and the full suite passes (211 tests). The rewrite was also run on
a copy of the real recipe: one line changed.

Remaining: installed acceptance in 0.6.29.

## Resolution

Open.
