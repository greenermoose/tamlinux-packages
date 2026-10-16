# Letter candidate preparation helper

- **CLI Tool**: Claude Code (`claude`) `2.1.301`
- **Model**: `claude-opus-5-5`
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > Yes, please start on those. Are you able to claim all the paths you need? Can you coordinate with codex and agy?

  > Tamlinux 0.4.4c's source is settled. Codex has released all claims. I'm finishing up work before proceeding with testing automatic login. Please finish up everything you've been working on. And let me know what product-source is. Do we need to keep that?

  "Those" include the agent's proposal for a script that performs the
  repeated bookkeeping of preparing a letter candidate.

## Implementation

`tools/prepare-candidate.py` has five independent steps. `version` writes the
next letter and refuses one that has a delivery record (letters are never
reused) or does not advance. `pin INPUT=REV` accepts only exact 40-character
commits, rewrites that input's URL alone, runs `nix flake update` for it and
confirms the lock resolved the requested commit. `build` runs
`nix build --no-link --json` for the standard outputs and checks, keeping the
log and output list in the private state directory. `record` writes
`deliveries/tamlinux-<version>.json` from the lock and the build evidence,
refuses to overwrite an existing record, and accepts extra fields without
letting them replace the derived ones. `check` compares `VERSION`, the
`flake.nix` pins, the lock, the product `VERSION` at the pinned revision and
an existing record. The interface follows constraints from the agent that
prepares candidates: optional steps, exact identities, retained letters and
receipts, evidence outside repositories, and no implicit promotion or
activation.

## Verification

- 7 tests with a stand-in `nix`, including a full version-pin-build-record
  run, refusals that leave files unchanged, a failed build, drift detection
  and a check that only `flake update` and `build` are ever invoked. They
  caught a pin that replaced every occurrence of a shared revision; it now
  rewrites only that input's URL.
- `check` reports the committed 0.4.4-c assembly consistent.
