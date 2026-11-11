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
