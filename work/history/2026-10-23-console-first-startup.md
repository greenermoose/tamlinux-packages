# Console-first package delivery

- **CLI Tool**: Codex CLI `0.164.0`.
- **Model**: `gpt-6.1-sol`.
- **Transcript**: Retained privately by the author.
- **Authorship**: Fred approved the startup plan; Codex implemented delivery
  changes and verification.

## Guiding prompts

> Anything that provides or forces a graphical login or shows graphics during the boot process should be removed from Tamlinux. That is wasteful extra stuff I do not need or want.

> When my machines boot, I want to see the normal text-only boot sequence so I can see exactly what they are loading and what is happening as soon as possible in the boot process.

Approval, excerpt:

> I approve. Proceed. You can close the review window. Ask if you have any further questions.

## Changes and verification

Remove SDDM, its greeter/vendor configuration, chooser registration and the
old PAM repair from the native package recipe and selected source manifest.
Keep the explicit native entry, now routed through the installed validated
`tam-desktop`. Deliver the new endpoint and feature through the shell package
and user session module. Native ownership checks follow the explicit command.

Ten native-staging/recipe tests and eight native-collector tests pass, including actual package() extraction,
absence of greeter/chooser/PAM files and absence of SDDM/Plymouth dependencies.
The native Arch package also builds through makepkg's build/check/package
phases with `--nodeps --nosign --noconfirm`; host dependency checking was
skipped, and no installation was performed. Inspection of the real archive
confirms the removed files and dependencies. Source-tar SHA-256:
`80a6dabc3cdcf37f2a6bf2346e46d6b174fd995aa1c7f6cbde7abc0940619740`;
archive SHA-256:
`b5fbc4fdc26bf340396f2f0e5a327eb0a2e37dff054d7bdeff8375f6bf36e6a1`.
This disposable Develop build is not a prepared candidate.

The fresh-session Nix contract exercises the delivered command when the
selected product supports it. Its first run exposed public help calling a
native `/usr/bin/python3` in the Nix build environment. The product's public
shell entry now handles help without native providers; delivery pins that
exact fix, `c6340a5d4f5fb2f8d47580d575b3442fb7990a27`.

The pinned `checks.x86_64-linux.fresh-session` build now passes, including
actual installed `tam-desktop --help`, its managed endpoint, the no-wait
launcher and existing fresh-session contracts. Result:
`/nix/store/l1g4q4g38p58yldxf9kp67f97yvbprd6-tamlinux-fresh-session-contract`.
No physical login/locking/boot result, candidate promotion or activation is
claimed. The selected minimal root-stock and bootstrap media are unchanged;
proof on the first workstation precedes the second.

Final product pin: `f266074dc52e68a63c369042726535751abea94b`. It also removes
obsolete first-install guidance about enabling graphical login; all 56
deployment-command tests pass. The launcher/native files are unchanged from
the earlier checked source. The fresh-session contract also passes on this
final pin, producing
`/nix/store/zf78hvpayn4vy5vlzy9b4fa4skclxf4g-tamlinux-fresh-session-contract`.
