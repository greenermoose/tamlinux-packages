# First extraction: scope and host contract

The first candidate preserves the existing Arch/Hyprland shell deployment
interface while moving its reusable Nix implementation here. It does not replace
the compositor, root filesystem, boot stack, graphics driver, or native package
owners. It has not been promoted to Run, published, or released.

The product source remains pinned to `f618970` (source version `0.3.3`) for the
baseline shell. Newer plugin consolidation is distinct and has not been accepted
as a delivery. The flake lock records exact component and build-input revisions.
`deliveries/` describes this candidate; a packaging commit identifies the assembly
recipe independently from the component versions.

## Host prerequisites

The current shell source starts `/usr/bin/quickshell` through `/usr/bin/python3`
and consumes the native Qt/QML, Hyprland, systemd user session, graphics, D-Bus,
PipeWire, NetworkManager, BlueZ and portal stack. Existing Tamlinux desktop action
helpers must be available in the session PATH for their respective panels and
actions. Packaging those helpers and the complete native dependency manifest is
unfinished. The example proves user-layer construction; it does not prove
runtime feature parity on a fresh host. The host supplies networking and hardware
support. Compiler smoke checks do not test Internet access or boot recovery.

The example includes generic settings and a built-in tray with no personal
plugins. Services retain the current shell interface. A full desktop delivery
must add source-owned defaults, accepted plugin payloads and native integration
before workstation acceptance. No private source is an input to the example.

## Mutable configuration and recovery

Public layout/settings sources are store-backed examples. Consumers that capture
panel writes can instead manage their mutable configuration explicitly and leave
these options unset. Out-of-store user preferences require their own revision or
backup: Home Manager rollback does not freeze them. Plugin roots remain directory
links into the store, leaving their parent writable for deliberate test overrides.
Activation refuses active plugin override links and recovery state.

Keep the existing Home Manager generation and native package state before testing
a consumer. Build and compare units, launch environment, package selections,
file contents/modes/link targets, and plugin digests first. Activate only through
the component lifecycle with an established recovery route. A test/Run shell pin
and protocol-trial identity must be preserved explicitly during later activation.

## Deferred ownership work

Reconcile consolidated plugin code with accepted payloads before selecting it.
Move remaining desktop commands/defaults to Tamlinux and independent utilities
to tamlinux-tools as separately reviewed source changes. Add delivery-controlled
installed product versioning after those sources form one accepted assembly.
Then complete the Arch adapter, private fleet split/capture and isolated recovery
proof. Void and nut assembly retain their separate roadmap and acceptance work.
