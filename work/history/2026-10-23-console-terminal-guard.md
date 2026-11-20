# Package the console guard and terminal theme migration

- **CLI Tool**: Codex CLI `0.164.0`.
- **Model**: `gpt-6.1-sol`.
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted delivery and verification, directed by Fred.

## Guiding prompts

> Keep working on Tamlinux 0.5. I'm hoping to be able to try a boot-to-text-terminal soon. Currently when I boot I get dumped directly into a graphical shell. I want to boot to a text shell and then be able to start a graphical shell if I want, or just start using my computer if I don't need a graphical shell.

> By the way, this omarchy state stuff is something we want to remove in Tamlinux 0.5. We shouldn't be looking for any omarchy stuff to run software on my computers.

## Delivery and verification

Pin product `7d3944c06a2fa3a244d05a39d0e6fa539f6a71c1`, including the
foreground console guard and finite migration for four terminals' inherited
theme includes. Build the exact shell and commands and check fresh-session,
installed-components and example-contract without activation. Results:

- Shell: `/nix/store/iqbvrz049zsv6r57qwbr4zd1fqn9asww-tamlinux-shell-0.5.0`.
- Commands: `/nix/store/p7yp147ckm4nzbxq21zkb39csnwbaq3v-tamlinux-commands-0.5.0`.
- Fresh-session: `/nix/store/883xbv5sq9dhgqczx86slcfb4sqjji68-tamlinux-fresh-session-contract`.
- Installed-components: `/nix/store/fhi9i3xqlgapk7l4x8bpmyz1byrwzf49-tamlinux-installed-components`.
- Example-contract: `/nix/store/32942apknclmsvbi5bxnr2i6dxdzkalh-tamlinux-example-contract`.

An isolated probe of the real packaged migration exercises four terminal
configurations, custom XDG roots, apply, retry, rollback and preservation of
later writes. Source checks pass eleven console tests, ten session tests and
28 migration tests. Physical boot, VT switching, locking and credentials remain
pending; none is established by these checks.

This updates Develop; it does not prepare or reuse a numbered candidate.
The existing `deliveries/tamlinux-0.5.0.json` is retained unchanged. The next
prepared assembly must take a new number on the user's instruction. No Test,
Run, release, native installation or boot/login change was performed.
