# Delivered agent skills

The selected shell package carries `share/tamlinux/skills/{tamlinux,diagnose-crash}`.
The desktop skill explains ownership, inspection and the boot/unlock/login
distinction. Crash notifications read the diagnosis skill through the selected
user data endpoint; the skill's upstream MIT notice is retained.

`tamlinux.agentSkills.enable` defaults on when the enabled shell supports this
payload. Home Manager links the selected data tree at
`$XDG_DATA_HOME/tamlinux/skills`. After `linkGeneration`, activation registers
both skills in `.agents/skills`, `.claude/skills`, `.codex/skills`,
`.pi/agent/skills` and `.hermes/skills` under the user's home.

If Home Manager manages a whole directory, the module omits individual
registration inside it. That directory's manager must supply `tamlinux` and
`diagnose-crash` links to the selected data endpoint. Override
`tamlinux.agentSkills.managedDirectories` when another manager owns a whole
directory that Home Manager cannot recognize. Personal skills are preserved;
a colliding regular file, directory or foreign symlink stops registration.

The installer preflights all five directories, removes only leaf symlinks that
resolve under `/usr/share/omarchy` (including dangling links), then registers
the two stable data endpoints. It never removes a regular `omarchy` entry;
that requires its owner's disposition. A post-check fails on any `omarchy`
entry, another inherited link, a missing skill, or a different selected package.

Check the installed selection without changing it:

```bash
python3 -I "$XDG_DATA_HOME/tamlinux/skills/manage.py" --check \
  --store /nix/store/SELECTED-SHELL/share/tamlinux/skills
```

Use `${XDG_DATA_HOME:-$HOME/.local/share}` when XDG_DATA_HOME is unset. The
explicit store argument must come from the selected assembly, rather than
resolving an arbitrary existing link and trusting it.

## Test and rollback preparation

Before the first activation, checkpoint the five discovery directories' two
skill links and any inherited symlinks, including links in whole-directory
sources, and update the workstation's agent instructions and custom links as
part of the same reviewed transaction. Development does not alter them.

For rollback to a pre-skill generation, first run the retained candidate's
`manage.py --uninstall --store STORE` with the same home/data/managed-directory
arguments used at install. This removes only the installer's own stable links;
personal replacements are preserved. Restore the recorded previous links
through their owner and then activate the retained prior generation. Regular
personal entries must never be overwritten to make this check pass.

The contract build tests actual packaged skills, custom XDG paths, fresh
discovery, rejection of a planted inherited link, and its removal on the next
activation. Physical crash-action launch and fresh-agent selection remain
Test evidence to collect on the exact candidate.
