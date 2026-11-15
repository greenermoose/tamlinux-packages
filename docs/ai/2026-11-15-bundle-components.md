# Preserve pinned components during candidate preparation

- **Date:** 2026-11-15
- **Tool:** Codex CLI 0.169.0
- **Model:** gpt-6-astra
- **Transcript:** Retained privately by the author.

## Request

> Let's completely revamp our plan. I want to get 0.6.26 done as soon as possible. Can you start getting it done right now?

## Change

Preserve external component pins when rewriting the workstation bundle lock.
Accept assembly-owned artifact requirements and check their committed recipe
paths and revision ancestry. Existing built-artifact checks still apply.
This lets standalone tools keep their own source branch conventions while the
assembly freezes their recipes and source pins. No candidate was reserved or installed.

## Verification

26 candidate-workflow tests and 9 bundle tests pass. Read-only inspection of
the requested candidate passes all four recorded source requirements.

## Explicit backend request

> Package up and test Tamlinux 0.6.26 using tam-bundle.

Accept the optional backend suffix verbatim and reject a conflicting backend
argument before reservation. 27 workflow tests pass.
