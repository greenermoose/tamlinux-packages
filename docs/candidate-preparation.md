# Prepare and resume a candidate

Scheduling a component for a future version is a record-only operator action.
It does not prepare a candidate, allocate a version or change source/package
pins. Candidate preparation begins with an explicit Package/Test request.
Both "Package up and test Tamlinux 0.6.2" and the existing "Package and test
the next version of Tamlinux" wording are accepted. A named version must match
the command argument and next unused candidate; a mismatch stops before source
mutation or version reservation.

The operator supplies requested inclusions to `Workflow(..., inclusions=...)`.
Each names its owning source, revision lower bound, source path, package output
and installed artifact. Preparation verifies that selected source contains the
requested work and that the built package actually contains its artifact.
Requirements are frozen in the transaction and delivery record. Missing
contents fail preparation; changed requirements cannot alter an interrupted
or frozen candidate on resume. Sources continue to be selected as whole
develop revisions, rather than independent per-feature commits.

An explicit tam footer pair adds `versions = { command = "x.y.z"; corpus =
"p.d.q"; }` to its requirement (the provider supplies the equivalent JSON
object). These are exact constraints. Check selected source before reservation,
recheck the committed pin, then verify the built `tam --version` and installed
corpus version with corpus lookup bound to that package. A newer command or
corpus does not satisfy the request. Frozen resume preserves the original pair.

Use native component builds while developing. At the packaging boundary, the operator integration calls `tools/candidate-workflow.py` to gather registered work, reserve the next unused patch number, commit selected sources, publish develop, pin exact commits, prepare the native payload and freeze the built assembly. This helper never promotes branches or activates software.

The resumable transaction lives under `$XDG_STATE_HOME/tamlinux/candidate-workflow`. One operation lock prevents competing version allocation. `--resume` retains its version and selection. Source movement, selected edits held by another session and incompatible trial
state stop preparation. Unrelated dirty files outside the packaging session's
claims and registered trials stay local and are not selected; packaging pins
HEAD for those components, and pin-only resumes keep that HEAD while those
local drafts remain. The frozen result is an exact assembly revision, not today's HEAD. A cancelled request retains its reserved number and sources. Component version decisions must be finished under the component's own rules; gathering never guesses a command/corpus version bump. Existing app-specific legacy trials need their recorded restore procedure once before migration to the common trial registry. External dependency pins remain unchanged.

For existing manually selected pins, the lower-level interface remains:

```sh
tools/prepare-candidate.py prepare --product ../tamlinux \
  --parent <40-character-assembly-revision> --scope "What changed"
```

`verify`, `build`, `record`, and read-only `check` remain available for diagnosis. The authoritative ten assembly targets are `DEFAULT_TARGETS`; a partial build cannot freeze a candidate. The consumer generation additionally builds its selected applications and host-specific closure.

Focused checks use the pinned commands/desktop source closure and a controlled native runner. Candidate VERSION, package metadata and unrelated packaging helpers do not invalidate those source checks. Missing checks never count as passing. Build evidence separately binds the assembly inputs and target set; available matching outputs are reused, and Nix restores missing outputs. Every reuse is reported. Command checks have separate derivations: syntax-only commands and the isolated development/deployment fixtures have narrow source inputs; unknown test closures conservatively retain the full product. Native command compilation has its own source inputs and retained build IDs. Evidence is outside repositories under `$XDG_STATE_HOME/tamlinux/candidates`.

Native requirements bind the selected source payload, recipe, modes, links and interface. A compatible prior native archive retains its package version and original provenance. New native content needs a new archive and a separately approved native installation. Existing historical delivery records retain their original exact-version rules.

A successful record freezes the version permanently. Retry an interrupted transaction; never edit a prepared delivery or reuse its number for changed contents. Preserve required native archives and recovery generations. Routine development caches can be removed only when no active trial references them; generation pruning and global Nix garbage collection remain separate recovery decisions.
