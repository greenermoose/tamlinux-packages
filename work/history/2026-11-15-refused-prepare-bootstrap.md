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

The frozen recipe assembly is `60f48995b2bfaec498adb3c4e99b0265157d577f`.
Native build and all five bootstrap fixture checks pass. The archive is
`tam-nut-0.13.1-1-x86_64.pkg.tar.zst`, SHA-256
`dbdd5a8c9f91cbb791b377e721f5fe7c99ec3c6e33192c5445d9ffa26e56a485`.
Its entries are root-owned; the executable is static. Compared with 0.13.0-3,
the only changed installed file payload is `usr/bin/tam-bundle`; package
metadata changes as expected. New binary SHA-256:
`210aed20a16bbce0c5ab7be2e4827cc317caf71b7c98ecb595a6d91783b62f36`.
