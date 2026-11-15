# Bundle completion packaging inputs

- **Tool:** Codex CLI 0.169.0
- **Model:** gpt-6.1-sol
- **Transcript:** Retained privately by the author.
- **Prompt:** “Implement the plan.”

Updated the workstation lock and native bootstrap source pins to include
hardware bring-up fixes: invoking-user detection, temporary cleanup,
service activation and recovery parent recreation. Bootstrap pkgrel is 3;
revision 2 was already used and must not identify changed payload bytes.
The product source also includes subsequent documentation/fleet navigation fixes.

Verification: nine bundle packaging tests and five bootstrap fixture tests pass.
Native archive build passed after repairing the stale test_bootstrap.py checksum.
The bootstrap is static (no ELF interpreter); archive SHA-256 is
21e0cb01db66edfe6f75fa41c98ec7c8bfba6a00b9d6429e81db5b283be871e1.
Fresh and verified warm-cache builds produced the same 3,277-entry product,
bundle identity prefix 4c323bb32418 (the full identity is in BUNDLE).
Both archives verified and matched byte for byte, SHA-256
cd2755282b01760bb68ca959acedd621adcc820209667a388f293c43c8d46285.
The trial recipe assembly is 91ce28a, selecting product 20ccbfa.
Hardware acceptance remains pending.
No installation or candidate stage move was performed.
