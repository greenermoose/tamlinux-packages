# 2026-10-20 — Single-owner input-method startup

- **CLI Tool**: Codex CLI `0.163.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted implementation directed and reviewed by Fred.
- **Prompts**:
  > What's next for Tamlinux 0.4.4?

  > Close the evidence gaps.

  > Looks good. Close the review window and proceed.

Fred approved the public input-startup plan before implementation. Fresh Arch
VM evidence exposed competing vendor XDG and native systemd startup paths.
The session module supplies a default Hidden=true override with explicit
consumer precedence; the native unit restarts only on failure, respecting a
successful exit when another instance already owns the bus name.

The repair is prepared as the next unused Develop letter, 0.4.4-l. This is
no authorization to promote, install on the workstation, or release it.

Verification: eight native-default tests pass. The Nix package builds, fresh
session contract (including explicit consumer override precedence), installed
components and example contract pass. Native source commit is
`1aa4eaf51046d05c74142935c7ed39486315f8d6`; the VM user assembly is
`08db32396673141c3ef731242289b7f67a443315`.

The recorded native archive and exact user assembly pass two disposable Arch
VM logins: one bus owner matches the native unit PID, no active vendor autostart,
zero restarts stable over five seconds per login, no runtime findings and all
nine selected plugins. A separately selected Fcitx instance keeps its bus name;
the native unit exits 0 and remains inactive with zero restarts. No host package
or login configuration changed. This does not establish physical acceptance,
final-candidate preserving rollback, normal-delay sleep or complete Run recovery.

The implementation commit contains this record; inspect Git history for exact
source identity. No transcript identifiers or private evidence paths are public.
