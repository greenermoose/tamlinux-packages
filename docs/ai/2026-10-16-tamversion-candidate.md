# Small 0.4.4-b version-display candidate

- **Tool**: Codex CLI `0.163.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Prompt**:
  > Make 0.4.4b just a+tamversion, bump VERSION in both repos, and hand it to me for Test before any login work.

The b assembly retains a's dependency pins, package recipes and native session
payload. It changes only the product source to add `fred.tamversion` and bumps
both repositories' VERSION files to `0.4.4-b`. The plugin output discovers the
new directory automatically. The label reads the running shell's packaged
version, rather than the plugin version or selected checkout version.

Candidate preparation grants no Test, Run or release promotion. Native login,
autologin, boot, sleep and removal work are outside this candidate.

Exact source revision, outputs and checks are recorded in
[`deliveries/tamlinux-0.4.4-b.json`](../../deliveries/tamlinux-0.4.4-b.json).

## Validation

- Source `04273de90d65b9df965747df793999ecd4894944`, directly after a.
- Both VERSION files read `0.4.4-b`; only the product source lock changes.
- Shell, plugins and commands build successfully. Installed-components and
  example Home Manager contract checks pass.
- 590 desktop tests pass, one historical adapter check skipped.
- The built shell launcher overrides a stale inherited version with `0.4.4-b`,
  discovers all nine packaged plugins, and the built widget renders
  `Tamlinux 0.4.4b` offscreen at positive width and height.
- Session/native/agent-skill source is byte-identical to a. No activation.
