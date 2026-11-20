# Console monitor command dependencies

- **CLI Tool**: Codex CLI (`codex`) `0.164.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted package integration directed by Fred.
- **Commit**: The commit introducing this record contains the dependency change.
- **Prompt**:
  > Looks good. I accept. Close the review window. Proceed.

  > Please install it.

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

## 0.5.3 installation candidate

Prepare **0.5.3** from product
`79c66c39ea793585a97aa23b91f2e2d2a578b400`, retaining the other component pins
from 0.5.2. All nine product/component/contract outputs build, including the
commands package with 25 monitor tests; nine candidate-tool tests pass. The
packaged monitor command's help and metadata-only JSON listing work with an
empty user PATH and no compositor environment.

The native integration tree is unchanged at
`2ebaed15cfcac835bc682c147ef1c2673d65b936`. Reuse the installed 0.5.2 native
package and existing recovery provider; no boot/login, native package or
mutable settings transaction is needed for this user-command update. The
[delivery record](../../deliveries/tamlinux-0.5.3.json) binds the source,
outputs, checks and retained native artifact. Candidate preparation is complete;
installation remains gated by the exact Test instruction and its displayed
stage plan. No stage promotion or activation has occurred during preparation.
