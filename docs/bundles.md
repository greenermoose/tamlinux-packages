# Native product bundles

`recipes/` and `tamlinux.lock` build the product with tam-bundle 0.5.0 or
later. They are a development integration alongside the existing delivery;
they do not select a workstation's Test or Run candidate.

```sh
tam-bundle build recipes tamlinux.lock -o /var/tmp/tamlinux-dev --version 0.6.20-dev
tam-bundle verify /var/tmp/tamlinux-dev
tam-bundle needs /var/tmp/tamlinux-dev
```

`--repos DIR` uses exact locked commits from local clones before fetching.
The recipes and lock must be committed together before building; the bundle
records that packaging commit as well as every component commit. The notes
file comes from that commit. Candidate preparation must select matching
version notes and bind an exact built bundle before any Test approval.

libtam is a build-only dependency, including the display/session libraries.
The product recipe builds all commands, shell, plugins and owned data through
the top-level Makefile. The tools recipe installs only tam-file-select:
tam-bundle itself belongs to the native adapter so it can always roll back
a broken product. The manual index is built, hashed and switched with its
pages. Third-party commands, libraries and fonts remain native dependencies.

Before switching a workstation, compare the new file list against its
recorded delivery. Nix command wrappers and compressed manual aliases are
packaging differences; missing commands or product data must be explained.
User configuration and user-manager activation are separate migration steps.
