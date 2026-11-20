# Native display corrections and user-package correspondence

- **CLI Tool:** Codex CLI `0.167.1`
- **Model:** `gpt-6.1-sol`
- **Transcript:** Retained privately by the author.
- **Prompt:**
  > For [redacted: private plan reference], finish shared metadata, remaining queue/retry gates, full Hyprland build and package integration before an exact-candidate Test and Dell trial.

The frozen native provider recipes add the exact product-reviewed display
patches to their existing DPMS/idle/connector guards. Hyprland 0.56.2-4.2
and Aquamarine 0.15.1-1.2 build with native Arch makepkg. The Hyprland build
uses four compile workers, preserving the recipe's configure flags; the
recipe supports a bounded `CMAKE_BUILD_PARALLEL_LEVEL`. Build tools are
unpacked from cached Arch packages into temporary storage, without changing
the installed system. Debug splitting and LTO were disabled for this build.
The Hyprland link uses the existing ABI-compatible Aquamarine soname; its
version-only entry also runs against the staged corrected library.

The archive identities and source commits are frozen in the native provider
selection. `check-display-integration.py` binds both native archives and
recipe closures to the exact product patches and actual Nix user-package
files. Eleven synthetic regressions cover exact pairing, changed archives,
changed recipes, relabeled builds, missing corrections, mixed user sources and a stale standalone command helper and strictly validated Python shebang
relocation with unchanged isolated mode/body.

Verification: full Hyprland package compile/link; Aquamarine package build
and three fake-backend tests; native archive metadata/recipe/payload checks.
The final Nix build succeeds for shell, plugins, commands and tools:
product `ea21f86`, recipe `9a309a9`, libtam `67cffd5`, tools `b92c4f5`.
The complete tools `make test` passes on the Arch host with mandatory private
PID/mount namespaces. Both workspace package entry points share temporary
intent and retain the newest generation in a no-IPC smoke test. The native
and user-package correspondence receipt records all exact identities.
The root cause of physical Dell blanking is not established; the source fix
removes a concrete focus-cycling path and logging supports any recurrence.
The command-package build exposed the journal launcher's missing native C
classification: its check had no libtam headers. Register it as a native
payload, giving its build/check/install the selected library. The integration
build also selects exact committed libtam/tools revisions through temporary
Nix overrides because current Develop uses the bundle guard missing from the
old frozen candidate's library. The committed tools build also needs the matching static glibc output for
its standalone tam-bundle binary; supply its path only to the static target. Putting static libc on every
link path also breaks the dynamic sanitizer test build, so the narrow Nix
Makefile substitution scopes it to `tam-bundle` and fails if the target changes. Declare Python for the journal tests and relocate their fake editor's
interpreter. The hermetic tools check runs portal/CLI tests, journal tests,
sanitizer-binary compilation and manual checks. Native bundle process,
mount and Arch-database proofs run separately on the host with their
private PID/mount guards intact; they cannot use the Nix sandbox's layout.
Candidate pins remain unchanged.

No package is installed and no Test, Run or Release is promoted.
