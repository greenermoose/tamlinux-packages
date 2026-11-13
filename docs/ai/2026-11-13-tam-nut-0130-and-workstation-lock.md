# `tam-nut 0.13.0`, workstation lock pins, and host-scoped `desktop-mode`

Updates the format-2 bootstrap recipe and workstation bundle inputs to the
verified `develop` source commits and moves `.local/state/tamlinux/desktop-mode`
to host scope:

- **`tam-nut 0.13.0` recipe (`recipes/tam-nut/PKGBUILD`):** updates `pkgver`
  to `0.13.0` and pins `_libtam=37c0dbd2194981e23215a7edad1575fa10bdfb1e`,
  `_tools=3096a17a3775c8248b192fa2e488109ecdee61e9`, and
  `_product=facb1495c3217d615c5d3ced6e172d638c35140a`.
- **Workstation source pins (`recipes/workstation/tamlinux.lock`):** updates
  `libtam`, `tam` (`5a503a37ef027c1d07dcba7e6d6481464eef7b8e`), `tamlinux-tools`,
  and `tamlinux` to matching `develop` commits.
- **Workstation UX portability (`recipes/workstation/SETTINGS`,
  `tests/test_bundle_settings.py`):** changes `.local/state/tamlinux/desktop-mode`
  from `common` to `host` per review, keeping per-display session mode
  host-local like `toggles/hypr/`, `monitors.lua`, and `input.lua`.

Verification: clean uninstalled `tam-nut-0.13.0-1-x86_64.pkg.tar.zst` build
(static ELF `usr/bin/tam-bundle` with `tam-bundle 0.13.0 (record format 2)`,
root-owned archive entries, valid Polkit XML policies, `systemd-analyze verify`
on `tam-bundle-apply.service`, and 4 `recipes/tam-nut/test_bootstrap.py`
tests); plus 69 tests across `test_bundle_comparison`, `test_bundle_delivery`,
`test_bundle_settings`, `test_nut`, `test_candidate_workflow`,
`test_prepare_candidate`, and `test_display_native_recipes`.

- **Date:** 2026-11-13
- **CLI Tool:** Antigravity CLI (`agy`) `1.5.8`
- **Transcript:** Retained privately by the author.
- **Authorship:** AI-assisted packaging update, documentation and tests.

## Guiding prompts

> Plan the next milestone for [redacted: private backlog reference].
>
> Approve. proceed
>
> desktop-mode should switch to host
