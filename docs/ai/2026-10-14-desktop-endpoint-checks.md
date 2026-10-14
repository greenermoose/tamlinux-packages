# 2026-10-14 — Paired browser delivery and actual session endpoint observations

- **CLI Tool**: Codex CLI `0.162.1`, dynamically checked.
- **Model**: `gpt-6.1-sol`, verified from runtime metadata.
- **Transcript**: Retained privately by the author.
- **Prompt**:
  > Resume from the Tamlinux 0.4.3 handoff.

Delivered the product extensions and org.tamlinux native-host registrations
from the paired command output, with declared clipboard/Python/download/media
runtime dependencies. Managed Chromium flags are separately enabled so an
existing file can be preserved and reconciled before activation. The session
contract checks exact host paths and extension origins.

The runtime collector discovers actual UWSM instance units instead of
inspecting a guessed inactive instance. It records the running compositor and
non-activating D-Bus owner/PID/executable observations for notifications,
portals and the keyring. Credential values are excluded.

Verification: 87 delivery tests pass; immutable commands/shell/plugins and the
fresh-session contract build offline. The isolated Arch VM runs
wayland-wm@Hyprland.service, maps the native compositor, and resolves the
notification, GTK/Hyprland portal and keyring processes. Actual Chromium native
messaging copy and loopback download probes pass. FileChooser selection and
cancellation return the expected responses; ScreenCast returns a PipeWire
stream after configuring the VM software-rendering capability. The test
requests follow the [portal API](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html).

The preparation preserves the prior VM generation and settings checkpoint;
no normal-account stage transition occurs. Exact final tuple binding and
remaining physical/native recovery evidence stay in the independence gate.

A graphical-user-manager pkexec request activates the registered Tamlinux
authentication agent; Escape dismisses it with exit 126 and the agent returns
to its idle state. A plain SSH-origin request has no session agent.

Final committed-output verification: both actual Chromium keyboard shortcuts,
native-message copy/download, successful and cancelled graphical authorization,
and original/later-write Chromium settings recovery pass. Runtime resolves
221 commands and eight plugin manifests with no findings. Temporary VM
authentication credentials are restored exactly. The [build/evidence envelope](../evidence/0.4.3-browser-endpoints.json) identifies the committed artifacts and
distinguishes the preceding-generation portal reports.
