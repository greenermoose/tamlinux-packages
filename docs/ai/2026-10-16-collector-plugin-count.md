# Runtime collector plugin check follows the selection

- **CLI Tool**: Claude Code (`claude`) `2.1.301`
- **Model**: `claude-opus-5-5`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted; written by the agent under Fred's direction.
- **Commit**: `2e51195`
- **Prompts**:
  > Codex is running now, so there may be a coordination issue. But try to start on 1 to 3 and see whether codex has added the reboot result to the test record. It should be on that.

  "1" is a review finding from the installed 0.4.4-c: the runtime collector
  expected exactly eight plugins, while 0.4.4-c ships nine.

## Implementation

`tools/collect-session-runtime.py` already built its plugin rows from the
manifests the selected plugin package ships, but then required exactly eight
rows, so every 0.4.4-c collection reported a false finding. The comparison is
now a separate `plugin_payload()` function. It returns a row per selected
manifest and also lists installed `fred.*` plugins the selection does not
contain. The finding fires on an empty selection, a missing or different
installed manifest, or an unselected installed plugin. Reports gain an
`unselectedPlugins` list; existing fields are unchanged.
`docs/session-runtime.md` describes the check; its earlier eight-plugin
results are historical and unchanged.

## Verification

- New test with nine plugins: all match; a removed manifest is reported; an
  extra installed plugin is listed.
- Whole `tests/` suite: 107 pass.
- Not run against a live session; the next letter's runtime collection is
  the end-to-end check.
