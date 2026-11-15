# Bootstrap correction for refused preparation

- **Tool:** Codex CLI 0.169.0
- **Model:** gpt-6.1-sol
- **Transcript:** Retained privately by the author.
- **Prompt (excerpt):** “Trial artifacts are under /tmp, so verify they still exist and match their recorded hashes before use.”

The native tam nut recipe selects tam-bundle 0.13.1 from tools commit
`3245abb2d4ef21e30360cac61813d90673d5884c`. It retains the reviewed libtam
and product pins. This correction keeps completed transaction history in place
when ownership or runtime preflight refuses the next installation. The source
runtime/ownership regression and full native-tools suite pass before packaging.

Existing bundle archives and their delivery records remain unchanged. Native
installation of this independently versioned bootstrap is a separate approved
operation; selecting the recipe performs no installation or stage transition.
