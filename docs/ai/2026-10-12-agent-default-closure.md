# 0.4.3 retained agent defaults and first microphone controls

- **CLI Tool**: Codex CLI `0.162.1` (checked live).
- **Model**: `gpt-6.1-sol` (runtime detected).
- **Transcript**: Retained privately by the author.
- **Stage**: Develop. No source pin, letter or installed candidate changed.

## Guiding prompt (excerpt)

> I accept your assessment of Hermes. Proceed with that in mind. I also accept the following recommendations from your 18-step-0.4.3-next-slice report
>
> 1) Transfer tam-default-agent into tamlinux/commands
> 2) Remove OpenClaw branches
> 3) Inspect every helper and tool edge before adding delivery wrappers.
> 4) Verify state read/write agreement with isolated HOME/XDG paths, alias selection,
> installation failure without changing the default, unbuilt Hermes stubs, prompt
> argv and retired selections.
> 5) Extend the existing installed-helper harness;
> reuse its recorded terminal/service boundaries without running real agents or
> installers.
> 6) Then build the changed command output and installed integration
> under short exclusive claims, run actual-output probes, and audit all five outputs
> with `--format compact --report /tmp/0.4.3-agent-audit.json`.
> 7) Afterward, take one controls caller chain at a time: audio/network/power controls
> and plugin setters. Inspect mutable writers before choosing the first controls
> batch; monitor brightness/text size reach hardware, theme and terminal writers
> and should not be treated as two isolated scripts.

## Delivery implementation and verification

Codex declared coreutils, GNU grep and Mise for the default-agent setter, and
WirePlumber/PulseAudio clients plus GNU awk for microphone default/capture-stream
routing. Same-output helpers take precedence; selected applications, application
PATH and terminal/audio session facilities remain independent providers.

The existing real-output probe harness now verifies paired XDG state, successful
user-install selection without an installer, literal prompt argv, retired installed
or unbuilt stubs, invalid installation requests and isolated unavailable audio
server boundaries. No real agent, installer or live audio service is invoked.

[Evidence](../evidence/0.4.3-agent-default-closure.json) retains both exact source
snapshots and five-output identities. Nix command builds run 22 then 25 staged
installed-helper regressions; installed-component integration passes. Actual-output
probes pass 23 then 24 checks. Audits report 99 then 98 unresolved lexical names,
52 inherited locations, zero missing outputs/files and zero undeclared absolute
tools. Nine pending requirements and no host inspection keep readiness false.
The agent-stage full audit is also retained at the requested development artifact
path; the controls stage uses a separate audit artifact. Source snapshots precede
documentation-only additions; these are not complete pinned assembly candidates.
