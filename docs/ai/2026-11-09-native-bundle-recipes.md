# Native bundle recipes

- **CLI Tool:** Codex CLI 0.167.0
- **Model:** `gpt-6.1-sol`
- **Transcript:** Retained privately by the author.
- **Commits:** The commit adding this record and subsequent fixes naming it.
- **Authorship:** Codex implemented the approved native bundle recipes.

## Guiding prompt

> Pick up where claude left off and work on tam-bundle. The goal is to finish tam-bundle and start using it on [redacted: host].

## Implementation

Four recipes pin libtam, tam, tamlinux-tools and the product. libtam supplies
private core, portal and display/session libraries; tam-bundle is excluded
from the product output. Notes and the packaging commit are recorded along
with the component sources. The initial version is explicitly a development
bundle; no candidate is reserved or promoted by adding these recipes.

Build and file-comparison results are recorded as the integration completes.
