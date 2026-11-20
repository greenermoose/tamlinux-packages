# Session bootstrap after package upgrades

- **CLI Tool**: Codex CLI (`codex`) `0.166.0`
- **Model**: `gpt-6.1-terra`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted change directed by Fred.

> Address the findings.

After the 0.5.11 package was installed, the active compositor still loaded older session defaults even after a reload. The managed session bootstrap now resolves the active shell link each time its entry is loaded. An existing session that started from an older fixed bootstrap must start a fresh session once to pick up the new bootstrap; subsequent reloads follow the selected package. The fresh-session contract checks the bootstrap. No session restart or deployment was performed.

Verification: the fresh-session Nix contract passed, and the managed shell link resolves to the selected package’s session entry.
