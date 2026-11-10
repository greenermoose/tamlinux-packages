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

## Verification

The first full build and a warm-cache repeat produced the same bundle hash,
`480b39d1cc1fdcff46f88dc59c286dc25d3e08c9f96ef3765644f87d4e90c5ea`,
with 3,085 manifest entries. Verification passed. Comparing the five old
component outputs found 2,622 common logical file paths, no missing product
commands or owned assets, and these differences:

- 124 third-party font files are native-package dependencies.
- The source-revision file is replaced by BUNDLE's source records.
- Added: two bundle metadata files, one manual index, five user units,
  four newer corpus pages and one plugin README.

The comparator normalizes Nix's hidden wrapper originals and compressed
manual paths; an unexplained removed command fails its regression test.

The adapter preparer can include the rollback tool and libtam from exact
lock-file commits, preserving Git's executable bits. Its package leaves
the product slot empty and installs the tool and polkit policy outside it.
Environment settings append the new prefix for dormant bring-up. The
development recipe carries no session restart steps; active candidate
recipes must add them at the separately approved cutover.
