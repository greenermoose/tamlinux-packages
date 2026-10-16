# Native SDDM greeter preparation for 0.4.4-a

- **CLI Tool**: Codex CLI `0.163.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Prompt**:
  > Continue work toward the test release of Tamlinux 0.4.4.

## Change

Provide an original Qt 6 greeter with visible username, session and password
controls, keyboard navigation, authentication failure/retry, bounded saved-session
selection and duplicate submission prevention. The native package stages the
QML/metadata, minimal Hyprland configuration and generic SDDM vendor drop-in.
Account and automatic-login policy remain consumer-owned. Existing local
configuration takes precedence and needs an explicit preserving transaction.
Session command renames wait for a real native-entry login.

The delivery documentation records maintenance-test ordering, precedence,
configuration/state checkpoints, later-write preservation, VT recovery and the
manual-login gate before normal automatic login changes. No installed candidate,
SDDM configuration, native package, boot setting or Test/Run/Release ref changes.

## Verification

- Actual QML interaction tests: five cases pass (seven QtTest results including
  setup/cleanup), covering mouse selection, keyboard selection, login arguments,
  retry, missing users/sessions, stale saved index and 640x480 layout.
- SDDM 0.21.0 Qt 6 test mode loads the actual theme offscreen without QML errors;
  the test proxy has no daemon socket, as expected. The event loop is ended by
  timeout after loading. This establishes neither PAM nor native-session login.
- Nine native staging tests pass, including execution of the actual recipe's
  package function and byte/mode checks for all four greeter artifacts, with
  no files installed under etc or usr/local.
- Greeter compositor configuration passes Lua syntax validation.

- Actual native build/check/package succeeds with makepkg --nodeps; no package
  or dependency installation occurs. The final archive contains all four SDDM
  files and no etc or usr/local payload. The source archive digest is
  `7cf97a422c5b1a8dd860cb5e01c2e66fd98466f6d27cd6c8701e180d2919cf53`.
- All 22 explicit native source files match product commit `236b92a`.
- Pinned Nix checks build successfully:
  - `/nix/store/5ipdbwmnrlrcbvrz540sflilxwbinbnk-tamlinux-agent-skills-contract`
  - `/nix/store/b45rqp0bghm1yrhm38divdqvnh3xaikx-tamlinux-assembly-contract`
  - `/nix/store/fmhazpnb7ypkysph9a2hpcv8fhfzwpj2-tamlinux-installed-components`
