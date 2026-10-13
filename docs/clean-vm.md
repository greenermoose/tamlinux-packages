# Clean Arch VM preparation

`tools/prepare-clean-vm.py` prepares a new isolated local development VM from
`contracts/providers/vm/selection.json`. The dated Arch cloud image, detached
signature, published arch-boxes key and UEFI firmware are pinned by digest.
The signature must match the selected signer. Preparation refuses an existing
destination and never starts a VM or installs host software.

Supply explicit local input/tool paths through the script's required arguments
(`--help` lists them). Keep VM disks, keys and logs outside the source clone.
The output contains a read-only base, a separate 32 GiB overlay, private UEFI
variables, a generated SSH key, a cloud-init seed, `vm.json` and `launch.sh`.
Review `vm.json` before starting `launch.sh` with host KVM access.

QEMU uses its own disks, virtual graphics, a private QMP socket, a serial log and
loopback-only SSH forwarding. It attaches no host directory or physical device.
Guest outbound traffic is blocked by the user-network restriction. Cloud-init
creates a key-only `tamlinux` account with passwordless guest administration;
root SSH and password authentication are disabled. The seed queues SSH startup
without blocking cloud-init, and disables the guest time-sync wait that cannot
complete offline. QEMU's virtual RTC supplies the guest time.

A successful bootstrap has `cloud-init status` reporting done, no failed units,
stock Arch package identities and only independent Arch repositories. Retain
the exact baseline before any installation. Transfer reviewed, verified native
archives and immutable software closures over the private SSH link, then
install inside the guest. Do not enable guest egress to make missing staging
silently succeed. Record every transferred artifact and resulting owner.

VM software checks cover fresh configuration, login, modules, workflows and
recovery only when actually executed. Virtual displays and disks do not prove
physical PAM/lock interaction, brightness/device permissions, display power,
clamshell behavior or sleep/resume on the reference machine. The manifest and
reports always leave complete candidate readiness false until the independent
acceptance gate is satisfied. Preparation changes no Test/Run/Release stage.
