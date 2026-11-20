# Start menu delivery preparation — 2026-10-29

- **CLI Tool**: Codex CLI (`codex`) `0.165.0`
- **Model**: `gpt-6.1-sol`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted implementation and documentation directed and approved by the maintainer.
- **Product implementation**: [7d53a9a](https://github.com/greenermoose/tamlinux/commit/7d53a9a).
- **Initial delivery scope**: documentation of 0.5.10 requirements. The subsequent package preparation is recorded below.

## Guiding prompts

> For Tamlinux 0.5.10, right-clicking the top bar anywhere there is not an icon should launch a start menu that includes two sections: a) the Quick Launch menu, and b) a configuration settings menu that lets you do things like change the color palette, font size, etc. of the graphical shell. This should be available anywhere on the screen via SUPER + Right Mouse Click, but works without SUPER in any area of the topbar not already devoted to another app. Ask if you have questions about this new menu.

> Do research on front end design, HCI, and UI/UX design. What do you recommend after that, two expandable sections or one list with section headings?
> 
> Appearance changes should affect the shell, supported apps, and terminals.
> 
> Revise the plan before showing it to me.

> Looks good. Make it so. Close the review window. Then proceed to implement the plan.

## Delivery requirements

The preparation plan includes the approved combined Start menu and its two
opening gestures. The packaged binding replaces resize on SUPER + right-click;
resizing moves to SUPER + ALT + right-drag. Consumer activation preserves and
retires the exact legacy Quick Launch override only with a selected package
at 0.5.10 or later, rejecting custom overrides for review. A generation rollback
alone cannot restore the source behind a live link, so retain its preserved
settings in the Test recovery scope.

Product checks include the 720-test desktop suite (81 skipped), final targeted
Start/JSONC/service checks and 22 appearance/control checks. Consumer activation
has four passing tests and a Nix syntax check. These are development checks;
the implementation phase prepared no assembly and claimed no physical acceptance.

## Package preparation after the reported failure

The maintainer reported:

> It doesn't work. I tried right mouse click on the top bar. Nothing.

The running 0.5.9 shell contained no Start handler. Source had been developed
but not delivered. Preparation now selects product
`3890ff60e0d6dbe5cd6bac7af01538158a264991` with VERSION 0.5.10, preserving the
other component and dependency pins. The delivery record binds ten built
outputs and the matching native archive. Native staging uses an exact Git
archive to retain recorded file modes; immutable store modes are read-only.

The installed-components check found a missing Python runtime dependency in
the new text-size recovery path. Its wrapper now provides Python explicitly;
all ten package/contract targets then passed. Native makepkg build/check/package
and archive verification passed. Candidate preparation and archive checks
completed 25 focused tests. No activation or native installation occurred;
the maintainer's Test instruction and physical acceptance remain outstanding.
