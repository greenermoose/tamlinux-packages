# Effective session runtime observations

Run `tools/collect-session-runtime.py` in the selected logged-in account with
explicit `--generation`, `--commands`, `--shell`, `--plugins` and `--report`
paths. It changes no units, settings or applications. The report is created
privately and refuses an existing output file.

The collector observes the actual shell PID/executable, selected environment
fields, mapped files and hashes, unit states and definitions, command resolution
for the selected command package, every plugin manifest the selected plugin
package ships (and any unselected installed plugin), configured resources and
Fontconfig resolution. It detects stale Stay Awake selection,
wrong generation/provider/module roots, command shadowing and inherited mapped
paths or environment variable names. Managed QML links are accepted only when
their targets resolve to the selected output. Nix's wrapped Quickshell executable
is paired explicitly with its public wrapper.

Credentials and arbitrary environment values are not copied. Fontconfig results
and configured resources are recorded separately from actual mapped files;
they do not assert every QML type, asset or font loaded, or that a workflow
passed. Bind these partial observations to a complete immutable source/output/
native/consumer/recovery/capability tuple before using them for acceptance.

The first actual clean Arch VM observation matches 216 command endpoints and
eight plugin manifests, records 191 mapped files, and resolves the two owned
font families. It exposes that VM's old Stay Awake path. Updating the selected
development generation and repeating collection remain required.

After refreshing the VM through the selected immutable generation, 219 command
endpoints and eight plugin manifests match, 190 mapped files are observed, and
the collector reports no findings. The Stay Awake path now matches. Required
complete runtime, workflow and tuple-bound acceptance remain open.

## Latest startup boundary verification

The physical preview initially retained `OMARCHY_PATH` from the host login
environment. Product startup discards prior-owner variables, preserving user
roots and Tamlinux overrides. After safe updates, actual VM and physical
preview runtime match 219 commands and eight plugin manifests, map 190 and 200
files respectively, and report no findings. Settings/GTK checkpoints and the
prior generations are retained; the saved physical monitor layout is unchanged.
The user confirms Dell recording, stopping and saved-video playback.

[Sanitized observations and exact selected outputs](evidence/0.4.3-session-runtime.json)
remain partial evidence. The intermittent native compositor position-loss
diagnostic is still open and the complete independence tuple is not frozen.
