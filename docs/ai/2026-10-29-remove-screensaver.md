# Remove the screensaver

- **CLI Tool**: Codex CLI `0.165.0`
- **Model**: `gpt-6.1-terra`
- **Transcript**: Retained privately by the author.
- **Prompt**:

  > One thing I want to do is remove all screensaver code from Tamlinux. We blank the screen, then enter energy-saving modes. We do not run screensavers that show images when we are away from the computer. Any code that runs a traditional screensaver is wasteful and unnecessary and should be removed entirely from Tamlinux.

- **Work**: Removed the screensaver-only provider and package contracts; retained the other provider entries and added installed-output absence checks.
- **Verification**: Focused source checks; packaged and physical verification remain pending.
