# Retire the previous default game selection

- **CLI Tool**: Codex CLI (`codex`) `0.167.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted implementation directed by Fred.

## Guiding prompts

> Let's remove all the games that we installed and start over. Can you do that now? I can't remember which version of Tamlinux added games, but I want to remove the ones we have now and find new ones for 0.6.19.

> I want science simulations and learning games.

> The start menu command should have an AI Agents section. Does it?

> Before downloading any games, make a list and I'll review it later.

> The cellular automata program would be cool to have. Make a list and include where to get games like that.

## Changes

Emptied the default `terminalGames` package set, retiring the eleven-package
selection introduced in 0.6.1. Kept the module's enable and package-list options
for future selections and consumer overrides. Replaced the old operational
catalog with the reset status. The fresh-session contract checks that the
retired executables are absent and that required activities remain installed;
AI Agents entries use separately managed, optional CLI tools.

No replacement games were downloaded or selected. Existing installations,
saves, prior generations and Nix store contents were left in place. Activation
belongs to a separately approved candidate transition.

## Verification

Both edited Nix files parse. Pure evaluation of the default game set returns
`[ ]`. The source `start` tests passed in the product repository. Full packaged
session-contract Python block passed with optional agents absent and present,
and correctly rejected a missing required activity. Full packaged session
validation remains pending: host deployment status could not connect
to the Nix daemon. No assembly pins or candidate versions were changed.
