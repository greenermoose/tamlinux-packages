# Independent boot providers and recovery preparation

- **Date**: 2026-10-16
- **CLI Tool**: Codex CLI (`codex`) `0.163.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted implementation and verification directed by Fred.
- **Prompts**:
  > Make a step by step work plan for Tamlinux 0.4.4e. Decide when to review and pin the independent boot-hook builds. Think carefully about what you are doing; don't just blindly flail around and be especially careful about asking me to do things that don't make sense.

  > This is good. Work through this list. Let me know what you need from me.

Review and retain unchanged upstream-author AUR recipes and exact upstream
source commits for limine-mkinitcpio-hook 1.40.0-1 and limine-snapper-sync
1.32.1-1. Build in a disposable native Arch guest, verify source/recipe hashes
and native archive metadata, and select the exact archives after an isolated
replacement/generation/snapshot/file-restoration rehearsal. Inspect final
packaging overlays: the mkinitcpio-specific EFI hook overwrites the generic
hook. A package-owned hook path is unsuitable for a transaction mask; use a
separate final hook directory and test its precedence through installation.

Retain Gradle's resolved build dependency hashes and the unchanged recipes'
GraalVM checksum verification. This records the build inputs; it does not claim
that Gradle's network resolution is a complete offline reproducibility lock.

Add a bounded boot-checkpoint helper. It captures only a reviewed file list
and exact old native archives, uses GNU tar for ownership/modes/symlinks/ACLs
and xattrs, detects file changes during capture, verifies archived contents
and refuses existing destinations, pacman locks and symlink ancestors.
Read-only status observations retain package reasons, firmware and writer
states. No restore, package installation or boot mutation is automatic.

Verification: both unchanged AUR makepkg builds pass; actual .BUILDINFO recipe
hashes match. Provider staging verifies both selected archives. The native
guest rehearsal passes masked replacement without EFI/firmware changes, UKI
content inspection, both EFI loader targets, nine-to-six history retention and
restoration of the old provider/file tuple while retaining a later settings
write separately. The seven checkpoint tests pass, and an actual protected
host checkpoint verifies. Physical boot and recovery remain Test observations.

The e assembly retains d's unchanged native login artifact. Test/Run and each
privileged host mutation remain separate decisions.
