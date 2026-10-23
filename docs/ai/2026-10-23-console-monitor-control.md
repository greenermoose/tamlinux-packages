# Console monitor command dependencies

- **CLI Tool**: Codex CLI (`codex`) `0.164.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted package integration directed by Fred.
- **Commit**: The commit introducing this record contains the dependency change.
- **Prompt**:
  > Looks good. I accept. Close the review window. Proceed.

Fred accepted the console monitor design following his request for a monitor
TUI usable without a graphical desktop. Declare Python/curses and brightnessctl
for `tam-monitor`; the DDC and backlight-selection siblings already supply
their own dependencies. The standard command-directory discovery and Makefile
installation include the new command when a later assembly pins its source.

The full command output builds with its checks against an immutable local
development source snapshot, including the new command's focused hardware,
console, wake-guard and pseudo-terminal tests. This verifies development
packaging only. Existing source pins, delivery records and candidate version
remain unchanged; no installation, stage transition or physical acceptance
occurred.
