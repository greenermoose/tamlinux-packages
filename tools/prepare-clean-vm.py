#!/usr/bin/env python3
"""Prepare a signed, pinned clean Arch VM with blocked guest egress.

Creates only a new destination. Does not start QEMU, install software on the host,
attach host disks, or accept any Tamlinux lifecycle stage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check(path, digest):
    if not path.is_file() or sha(path) != digest:
        raise ValueError(f'Missing/changed selected input: {path.name}')


def run(tool, arguments, log):
    if not tool.is_absolute() or not tool.is_file() or not os.access(tool, os.X_OK):
        raise ValueError('Tools must be explicit absolute executables')
    result = subprocess.run([str(tool), *map(str, arguments)], capture_output=True, text=True, timeout=60)
    log.write_text(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError(f'{tool.name} exited {result.returncode}; see {log}')
    return result.stdout


def launch_arguments(qemu, destination, port, memory, cpus, accelerator):
    if accelerator not in ('kvm', 'tcg') or not 1024 <= memory <= 8192 or not 1 <= cpus <= 4 \
            or not 1024 <= port <= 65535:
        raise ValueError('Invalid VM resources, accelerator or SSH port')
    d = destination
    return [str(qemu), '-name', 'tamlinux-043-clean-arch', '-machine', f'q35,accel={accelerator}',
            '-cpu', 'host' if accelerator == 'kvm' else 'max', '-m', str(memory), '-smp', str(cpus),
            '-drive', f'if=pflash,format=raw,readonly=on,file={d / "OVMF_CODE.fd"}',
            '-drive', f'if=pflash,format=raw,file={d / "OVMF_VARS.fd"}',
            '-drive', f'if=none,id=root,format=qcow2,file={d / "guest.qcow2"}',
            '-device', 'virtio-blk-pci,drive=root', '-device', 'virtio-vga',
            '-drive', f'file={d / "seed.iso"},format=raw,media=cdrom,readonly=on',
            '-netdev', f'user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:{port}-:22',
            '-device', 'virtio-net-pci,netdev=net0', '-device', 'virtio-rng-pci',
            '-display', 'none', '-serial', f'file:{d / "serial.log"}',
            '-qmp', f'unix:{d / "qmp.sock"},server=on,wait=off',
            '-pidfile', str(d / 'qemu.pid'), '-daemonize']


def prepare(args):
    manifest = json.loads(args.manifest.read_text())
    if manifest['schema'] != 1:
        raise ValueError('Unsupported VM manifest')
    check(args.image, manifest['image']['sha256'])
    check(args.signature, manifest['image']['signatureSha256'])
    key = args.manifest.parent / manifest['key']['file']
    check(key, manifest['key']['sha256'])
    check(args.firmware_code, manifest['firmware']['codeSha256'])
    check(args.firmware_vars, manifest['firmware']['varsSha256'])
    destination = args.destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('VM destination already exists; refuse replacement')
    if ',' in str(destination) or '\n' in str(destination):
        raise ValueError('VM paths cannot contain QEMU option separators')
    # Validate before any creation. All drive/socket paths are our new files.
    argv = launch_arguments(args.qemu, destination, args.ssh_port, 4096, 2, args.accelerator)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.clean-vm-', dir=destination.parent) as directory:
        temp = Path(directory)
        gnupg = temp / 'gnupg'
        gnupg.mkdir(mode=0o700)
        keyring = temp / 'arch-boxes.gpg'
        run(args.gpg, ['--homedir', gnupg, '--batch', '--dearmor', '--output', keyring, key], temp / 'key.log')
        status = run(args.gpgv, ['--homedir', gnupg, '--keyring', keyring, '--status-fd', '1',
                              args.signature, args.image], temp / 'signature.log')
        if f"[GNUPG:] VALIDSIG {manifest['image']['signingFingerprint']} " not in status:
            raise ValueError('VM signature does not match the pinned signing key')
        payload = temp / 'payload'
        payload.mkdir(mode=0o700)
        for source, name in [(args.image, 'base.qcow2'), (args.firmware_code, 'OVMF_CODE.fd'),
                             (args.firmware_vars, 'OVMF_VARS.fd')]:
            shutil.copyfile(source, payload / name)
        check(payload / 'base.qcow2', manifest['image']['sha256'])
        check(payload / 'OVMF_CODE.fd', manifest['firmware']['codeSha256'])
        check(payload / 'OVMF_VARS.fd', manifest['firmware']['varsSha256'])
        (payload / 'base.qcow2').chmod(0o444)
        (payload / 'OVMF_CODE.fd').chmod(0o444)
        info = json.loads(run(args.qemu_img, ['info', '--output=json', payload / 'base.qcow2'], temp / 'image.log'))
        if info['format'] != 'qcow2' or info.get('backing-filename'):
            raise ValueError('Base image must be a standalone qcow2 image')
        run(args.qemu_img, ['create', '-u', '-f', 'qcow2', '-F', 'qcow2', '-b', destination / 'base.qcow2',
                           payload / 'guest.qcow2', '32G'], temp / 'overlay.log')
        # qemu-img validates the backing file when it exists. The final base path
        # is intentionally unpublished here; use -u to create that exact relation.
        run(args.ssh_keygen, ['-q', '-t', 'ed25519', '-N', '', '-f', payload / 'id_ed25519',
                             '-C', 'tamlinux-clean-vm'], temp / 'ssh-key.log')
        key_text = (payload / 'id_ed25519.pub').read_text().strip()
        seed = payload / 'seed'
        seed.mkdir()
        user_data = {'users': [{'name': 'tamlinux', 'shell': '/bin/bash', 'groups': ['wheel'],
                      'lock_passwd': True, 'sudo': ['ALL=(ALL) NOPASSWD:ALL'],
                      'ssh_authorized_keys': [key_text]}], 'disable_root': True, 'ssh_pwauth': False,
                     'package_update': False, 'package_upgrade': False,
                     'bootcmd': [['systemctl', 'mask', '--now', 'systemd-time-wait-sync.service'],
                                 ['systemctl', 'enable', 'sshd.service'],
                                 ['systemctl', '--no-block', 'start', 'sshd.service']],
                     'runcmd': [['systemctl', 'enable', '--now', 'sshd.service']]}
        (seed / 'user-data').write_text('#cloud-config\n' + json.dumps(user_data, indent=2) + '\n')
        (seed / 'meta-data').write_text('instance-id: tamlinux-043-clean-arch\nlocal-hostname: tamlinux-proof\n')
        run(args.mkisofs, ['-quiet', '-output', payload / 'seed.iso', '-volid', 'cidata',
                          '-joliet', '-rock', seed], temp / 'seed.log')
        record = {'schema': 1, 'stage': 'Develop; VM preparation only', 'manifestSha256': sha(args.manifest),
                  'imageSha256': manifest['image']['sha256'],
                  'signingFingerprint': manifest['image']['signingFingerprint'],
                  'capabilities': manifest['capabilities'], 'accelerator': args.accelerator,
                  'sshPort': args.ssh_port, 'argv': argv,
                  'tools': {name: {'path': str(tool), 'sha256': sha(tool)} for name, tool in {
                      'qemu': args.qemu, 'qemu-img': args.qemu_img, 'mkisofs': args.mkisofs,
                      'gpg': args.gpg, 'gpgv': args.gpgv, 'ssh-keygen': args.ssh_keygen}.items()},
                  'candidateReady': False,
                  'limits': 'Clean base VM only. No Tamlinux/native installation or clean-host/workflow/physical/promotion acceptance claimed.'}
        (payload / 'vm.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        (payload / 'launch.sh').write_text('#!/bin/sh\nset -eu\nexec ' + shlex.join(argv) + '\n')
        (payload / 'launch.sh').chmod(0o700)
        shutil.copyfile(temp / 'signature.log', payload / 'signature.log')
        os.rename(payload, destination)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['manifest', 'image', 'signature', 'destination', 'qemu', 'qemu-img',
                 'mkisofs', 'gpg', 'gpgv', 'ssh-keygen', 'firmware-code', 'firmware-vars']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--ssh-port', type=int, default=22043)
    parser.add_argument('--accelerator', choices=['kvm', 'tcg'], default='kvm')
    args = parser.parse_args()
    try:
        prepare(args)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        parser.exit(2, str(error) + '\n')
    print(f'Prepared isolated clean Arch VM: {args.destination}; no host installation or stage change')


if __name__ == '__main__':
    main()
