# SDDM PAM cleanup assembly — 0.4.4g

- **Date**: 2026-10-17
- **CLI Tool**: Codex CLI `0.163.0`
- **Model**: `gpt-6-luna`
- **Assembly commit**: `f5af75e6ef6d62e134210f53eaa8c523e9bc89d8`
- **Product source**: `c0aaeee336874bc15eae0e23f233ac3bd9de2fd9`
- **Transcript**: Retained privately by the author.
- **Prompt**:
  > Implement plan 31, SDDM PAM keyring cleanup.
- **Key decisions**:
  - Pin the candidate assembly to the exact Tamlinux source carrying the
    checkpointed PAM helper and package it in `tamlinux-native`.
  - Keep the PAM mirrors in the consumer and leave them out of the package;
    the SDDM package remains their owner.
  - Keep candidate activation and fresh login proof for Fred's explicit Test.
- **Verification**:
  - Five Nix package and contract outputs built; candidate consistency check
    passed.
  - Native package build and checks passed; its helper payload is root-owned,
    mode `0755`, with archive SHA-256
    `634f75f57eb9771da6239ef197346b97b9e14ee78e100a98cf43a90ac15464c5`.
  - Ten native staging tests and nine PAM transaction fixtures pass.
  - Fresh automatic/password login and Secret Service proof remain pending.
