# Owned menu delivery

- **CLI Tool**: Codex CLI (`codex`) `0.162.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Stage**: Develop; no activation or publication.
- **Prompt**:
  > Start work on tamlinux 0.4.2. There should be notes for you from a prior codex session.

The shell module's default extension path now matches the product service:
`$XDG_CONFIG_HOME/tamlinux/menu/extension.jsonc`. Optional extension payloads
remain user configuration. Product sources that supply `desktop/menu/` get
immutable defaults and the owned `tam-menu` entry point; older pinned sources
retain compatibility with their existing default menu delivery.
Menu-default source selection and generated environment are tested with the
menu candidate, while the existing public example remains compatible with its
older source pin. Daily plugin payloads and protocol shadow policy are unchanged.

The example-contract path assertion was updated. Build verification is recorded
after the immutable candidate is selected. Test/Run activation is pending.
