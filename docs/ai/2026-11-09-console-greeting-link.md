# Session: 2026-11-09 — A fixed path for the console greeting

- **CLI Tool**: `claude` `2.1.319`
- **Model**: Claude Opus 5.5 (`claude-opus-5-5`)
- **Authorship**: AI-assisted, directed by Fred.
- **Transcript**: Retained privately by the author.
- **Prompts**:
  > Keep going. Push main. What else?
  >
  > yes

  "yes" accepted the recommendation that Home Manager link the deployed
  greeting to a fixed path in the home folder, and that the workstation's
  `/etc/issue.d/70-tamlinux.issue` point at it.
- **Key Decisions & Implementation Notes**:
  - The shell module links `share/tamlinux/console/welcome.issue` from the
    selected `tamlinux-shell` to `~/.local/share/tamlinux/console/welcome.issue`
    when the product has the console welcome. The greeting now carries the
    version ("Welcome to Tamlinux <version>!").
  - agetty shows the native package's version-independent
    `/usr/lib/issue.d/70-tamlinux.issue`; a same-named `/etc/issue.d` file
    replaces it. A host that links that file to the fixed path shows the
    selected version, and it follows Test, Run and rollback with no root step.
    The host link itself is administered separately, not by this module.
  - A version in the native package was the alternative; it was set aside
    because every candidate would then need an approved native install.
- **Verification**:
  - Both Nix files parse. The example contract asserts the link and checks
    the activated file contains the greeting; it was not evaluated in this
    session because the Nix daemon was not running. Candidate packaging runs it.
