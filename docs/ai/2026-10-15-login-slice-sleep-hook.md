# Pin the login-only source with the d sleep-hook set

- **CLI Tool**: Codex CLI `0.163.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > Please continue working toward Tamlinux 0.4.4. Let me know if there are any decisions I need to make.

  > Keep the existing hook for a (recommended)

## Change

Pin product `9cc5e6f`, which preserves the new zram-draining hook and its
regression suite outside the installed defaults. The a native package keeps
the d sleep-hook set. The initial candidate focuses on the greeter, skills
and manual native login with VT recovery; normal automatic login/command
renames and boot/update/fallback/sleep/removal follow in later letters.

Document the pre-removal Run fallback requirement. Preserve all actual native
login, physical and later-write rollback proof obligations. No Test or Run
reference, native installation, user activation or boot setting is changed.

## Verification

- Nine native staging/recipe tests pass.
- Product's 14 deferred actual-hook regression cases pass; the hook bytes
  are preserved exactly and d vendor-default regular files are unchanged.
