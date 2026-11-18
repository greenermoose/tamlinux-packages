# Preserve user command lookup during deployment

- **Tool**: Codex CLI `0.169.1`
- **Model**: `gpt-6.2-sol`
- **Transcript**: Retained privately by the author.
- **Guidance** (excerpt):

  > What each user chooses to run is that user's business.

  > Implement the plan.

The deployment contract describes packaged commands under `/usr/bin`
and user command resolution through `PATH`. Installer regression tests
live with the deploy operator in the product repository.
