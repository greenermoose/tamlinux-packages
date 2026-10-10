# tamlinux-packages

Public delivery definitions for [Tamlinux](https://github.com/greenermoose/tamlinux),
[tamlinux-tools](https://github.com/greenermoose/tamlinux-tools),
[tam](https://github.com/greenermoose/tam), and
[libtam](https://github.com/greenermoose/libtam).

This first Develop-stage extraction packages the native C components, provides
reusable Nix package selections and Home Manager shell deployment, and builds a
generic user example. It targets `x86_64-linux` on the existing Arch/Hyprland
host integration. It is not a complete workstation installer or accepted release.

The [deployment contract](docs/deployment.md) requires Test and Run to install
an exact, recorded package assembly through Nix and Home Manager at the same
managed locations. It also records the remaining gaps in this first extraction.

From a checkout:

```sh
nix flake check
python3 tests/portability.py
nix build .#tam .#libtam .#tamlinux-tools .#tamlinux-shell
nix build .#example-home
```

Builds and the example use pinned public inputs. The example username and home
directory are illustrative: set your own values before activation. Build it
first and review [the host prerequisites and limits](docs/first-extraction.md).
No check activates a desktop, starts services, or changes the host package database.

The [0.4.3 clean-host contract and audit](docs/clean-host.md) declare the native
Arch/Hyprland prerequisites and inspect explicit built outputs for missing
commands and inherited software identifiers. Its retained baseline exposes
unfinished desktop closure; the example is not yet a complete clean-host install.

Import `homeManagerModules.default`, enable `tamlinux.shell.enable`, and supply
layout/settings sources. The module installs the shell, plugins and product
commands from package outputs built from one product revision
(`tamlinux-shell`, `tamlinux-plugins`, `tamlinux-commands`), plus `tam` with
its offline guide and `tam-file-select`;
`tamlinux.shell.plugins` selects plugin IDs (default: all in the assembly).
Background and menu paths are configurable. Protocol shadow observation is an
explicit opt-in requiring an assembly that contains it. Deploy an assembly
with `tam-deploy` from the Tamlinux commands; see the
[deployment contract](docs/deployment.md).

The developer baseline installs Bash, editing, C compilation/linking with libc
headers, Make, Git, secure downloads and certificate trust. A consumer can set
`tamlinux.developer.nativeProvided = true` only after verifying equivalent host
tools. `lib.packageSets pkgs` provides `developer` and optional `userTools` lists;
personal applications, vendor editors and their overrides stay with consumers.

Source behavior and ordinary build interfaces belong in their component
repositories. Nix definitions, native package adapters, dependency selection,
assembly and delivery verification belong here. Planned Arch/Void native
recipes, complete desktop dependencies, immutable delivery manifests, and
publication/signing machinery will follow separately.

GNU GPL v3 or later. See [LICENSE](LICENSE) and [AI provenance](AI_PROVENANCE.md).
