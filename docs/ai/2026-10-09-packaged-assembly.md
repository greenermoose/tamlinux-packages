# 2026-10-09 — Install the shell, plugins and commands from one packaged assembly

- **CLI Tool**: Claude Code (`claude`) `2.1.295`
- **Model**: `claude-opus-5-5`
- **Transcript**: Retained privately by the author.
- **Authorship**: AI-assisted implementation directed by Fred. Claude wrote
  the packages, module change, checks and this record.
- **Prompts**:
  > I have approved it and yes, start 2b

  Fred then chose, among proposed options: name the deploy command
  `tam-deploy`; record a Test by pinning and committing the assembly revision
  in the consumer lock; make Run a promotion to `main` without reinstalling;
  remove the snapshot `test` and `run` commands from `tam-plugin`.

## Change and decisions

The approved deployment contract requires every Tamlinux installation to come
from package outputs of one recorded assembly.

- **Three product packages from one revision.** `tamlinux-shell` now also
  carries the menu defaults, `tam-menu` and the protocol shadow trial.
  `tamlinux-plugins` copies every `fred.*` plugin from `desktop/plugins/`
  without bytecode. `tamlinux-commands` installs each `commands/<name>/`
  with `make install` and runs its `make check` during the build.
- **The module installs only package outputs.** The `source`,
  `sourceRevision`, `pluginSources` and `menuDefaultSource` options are
  replaced by `package`, `pluginPackage`, `commandPackage` and a `plugins`
  selection. Features such as the menu and protocol shadow are package
  metadata, so evaluation never builds a package to inspect it. The protocol
  shadow identity hash is computed from the same files as before.
- **The pending-Test guard is retired.** A Test is now pinned in the consumer
  lock, so an ordinary switch rebuilds the same assembly.
- **`tam` pin.** The pin moves to `tam`'s `main`, which has the `show`
  command the installed check uses; the recipe points the command tests at the
  guide in the source tree instead of an installed one.

## Verification

- `nix flake check`: every output and check passed (19 entries), including the new
  `assembly-contract` check, which builds a fixture product and proves the
  shell, a selected plugin and a command resolve into their packages, an
  unselected plugin is absent and the protocol shadow is not installed.
- Built against the Tamlinux `develop` branch: the shell, plugin and command
  packages build, the three command test suites (`tam-deploy` 20 tests,
  `tam-plugin` lifecycle suite, `tam-work` 38 tests) pass inside the build,
  and the example generation links all eight plugins and every command into
  their packages.
- `tests/portability.py` passed.
