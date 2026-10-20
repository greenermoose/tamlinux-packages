# Candidate preparation accepts plain patch versions

- **CLI Tool**: Claude Code (`claude`) `2.1.305`
- **Model**: `claude-sonnet-5-5`
- **Transcript**: Retained privately by the author.
- **Prompt**:
  > For future Tamlinux versions, let's stop using the letters and bump the patch level. So rather than 0.4.5a and 0.4.5b, do 0.4.5 and then 0.4.6.

`tools/prepare-candidate.py` already parsed a plain `X.Y.Z` and ordered it
after earlier letters, and `nix/packages/default.nix` already passed it
through unchanged, so no behavior changed. The tool's wording, the deployment
guide and a new test now say that candidates are plain patch numbers from
0.4.5, that a prepared number is never reused, and that letters ended with
0.4.4-m.

Verification: the eight `tests/test_prepare_candidate.py` tests pass,
including a plain-number sequence 0.4.5 then 0.4.6 after the letters, a refused
reuse and a refused step backwards.
