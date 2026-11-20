# Candidate metadata repair without rebuilding the product

- Date: 2026-11-16.
- Tool: Codex CLI 0.169.0.
- Model: `gpt-6.1-sol`.
- Transcript: Retained privately by the author.

Fred directed: “Also relax the candidate rules to allow patching in place.”
He also directed: “Don't waste time making a whole new package and starting
over from scratch. Get this one workig.”

The candidate writer embedded inclusion audit data in a runtime delivery record
whose carried deploy reader accepts a strict field set. Move that audit into
`deliveries/inclusions/`, bound to the version and artifact SHA-256, while
retaining compatibility with historical embedded audits. Frozen checks read
the audit from the exact assembly commit.

The explicit metadata repair preserves the previous frozen state, version,
recipe, component pins and cached bundle bytes. It updates the assembly binding
and invalidates only the changed packaging suite's cached result. It neither
builds software nor promotes or installs a stage.

Verification: the runtime-schema regression failed before the change; all 32
candidate-workflow tests pass afterward, including frozen resume without a
second build, preserved repair history and rejection of changed payloads or
an audit bound to another archive. The 0.6.28 repair reuses the original bundle.
