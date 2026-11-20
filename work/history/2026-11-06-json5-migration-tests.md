## Session: 2026-11-06 — Run the json5 migration tests in the installed components check

- **CLI Tool**: `claude` `2.1.318`
- **Model**: Claude Opus 5.5 (`claude-opus-5-5`)
- **Commits**: `811609e`, `5481609`
- **Authorship**: AI-assisted, directed by Fred.
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > Answers to open questions:
  >
  > 1 yes
  > 2 skip with a clear reason
  > 3 delete them
  > 4 a failing suite should stop a candidate
  >
  > Update the plan. Close it if you have no further questions for me. With those questions answered, I approve the plan and authorize you to proceed.

### Work

`tamlinux` now skips its `json5` migration tests where Python lacks the module. This
check runs them with a Python that has it, so they are still enforced, and it fails
if any is skipped.

`test_prepare_candidate` had failed since `prepare` began building fleet profiles by
default. It tests check reuse, so it now skips them. All 165 unit tests pass from a
clean clone, and a candidate now has to pass them.

### Verification

`nix build .#checks.x86_64-linux.installed-components` built, and ran all 47 migration
tests.
