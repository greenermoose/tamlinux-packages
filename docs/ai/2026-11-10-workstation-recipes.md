# Format-2 workstation recipes

- **Date** 2026-11-10
- **CLI tool** Codex CLI (`codex`) `0.167.0`
- **Model** `gpt-6.1-sol`
- **Transcript** Retained privately by the author.
- **Authorship** AI-assisted recipes and verification.

> Approve 0.8 tool; continue recipes

The development workstation recipe pins libtam, tam, tamlinux-tools and
the Tamlinux product. Libtam supplies build inputs. The tools recipe
contributes only `tam-file-select`. The product recipe stages at
`PREFIX=/usr`, where the builder splits versioned private data from
conventional commands, manuals and vendor files.

The recipe declares the Arch x86-64-v2, glibc and systemd target, file and
version needs, the Quickshell Wayland QML export, and ELF probes.
`SETTINGS` lists common and host paths without personal settings values.
The builder checks declared ELF and script interpreter dependencies.

The first build sealed and verified 3,175 entries from the four pinned
components in a temporary workspace. The new recipe and lock are
independent of the dormant native adapter and the Nix/Home Manager
delivery inputs. Session launch and real-machine acceptance remain
migration gates.

After reviewing the recipe proof in Micro, the developer said “Approve
recipes; continue tam nut”.

The Arch tam nut recipe pins its static tool and bootstrap source. It
packages the rootstock profile, fixed apply helper, polkit action and
active-local-session rule, boot service and native package hooks.
`makepkg --check` passed, including three script/policy fixtures.
The extracted package had root-owned payload, validated polkit XML and a
boot unit accepted by systemd's verifier. Its SHA-256 was
`2ec1d0cfac8436f680364a41c9646f9b173aa7cfa6d2323cee45c15bdef669bf`.
This was a temporary development build. The existing native adapter and
Nix/Home Manager delivery inputs remain pinned.

## Console protocol integration

The development recipes now select libtam 0.6.0, tam command 0.53.0,
the 0.10.0 bundle tool and the gated native console entries.
The fixed apply helper takes the checked transaction id. The required
user action records active product units before stopping them and
retains that list through a failed restart. Four bootstrap fixture tests
pass. These source pins are separate from the native adapter's live pin.
