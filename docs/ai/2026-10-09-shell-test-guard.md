# 2026-10-09 — Protect a pending shell Test

- **CLI Tool**: Codex CLI `0.162.0` (live checked).
- **Model**: `gpt-6.1-sol`.
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted development directed by Fred.
- **Commit**: The guard commit carrying this record.

> Take a look at the status of the tamlinux project and the current plan. Are there any deficiencies or mistakes in the plan that should be corrected now? I've got agy working on the tam command, but I want you to get you working on the most important next project to do for the tamlinux project overall. Also, what should I test before accepting Tamlinux version 4.0.1?

A Home Manager activation now refuses to replace the candidate recorded in
pending shell Test metadata. Matching candidates and normal Run state are
allowed; malformed state fails closed before link changes. Deliberate component
Test/Run/back transitions remain the deployment helper's responsibility.

Verification: a Nix check runs the actual generated activation fragment against
absent, normal, matching, mismatching and malformed state. All eight flake checks
passed, including the built generic Home Manager example. Packaging
portability references and whitespace checks passed. No host activation is
performed by the check; selecting the module remains a consumer operation.
