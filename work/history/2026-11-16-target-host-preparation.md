# Explicit initial Test host

- **Tool:** Codex CLI 0.169.0.
- **Model:** gpt-6.1-sol.
- **Transcript:** Retained privately by the author.
- **Prompt excerpts:**
  > Package up and test Tamlinux 0.6.28.
  > Reuse valid build and test caches; rerun checks when their inputs change.

Candidate preparation can now record an explicit initial Test host separately
from the machine building the artifact. The request digest includes both.
Resume retains the target and requires the original builder; existing records
without a builder field keep their original host restriction. Invalid host
names stop before reserving a candidate. This changes preparation metadata,
not the product payload or any installation.

Verification: all 29 candidate-workflow tests pass, including target binding,
resume refusal, legacy host restrictions and invalid-target reservation checks.
No physical installation or fleet acceptance is claimed by these tests.
