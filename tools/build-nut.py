#!/usr/bin/env python3
"""Build recorded Arch-based bootstrap media; never write a block device."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def digest(path, algorithm="sha256"):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, algorithm).hexdigest()


def run(*args):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise ValueError(f"{args[0]} failed: {result.stderr[-3000:]}")
    return result.stdout + result.stderr


def verify(source, signature, key, manifest, gpgv):
    for path, expected in [(source, manifest["sourceSha256"]),
                           (signature, manifest["signatureSha256"]),
                           (key, manifest["keySha256"])]:
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise ValueError(f"unverified input: {path.name}")
    with tempfile.TemporaryDirectory() as home:
        status = run(gpgv, "--homedir", home, "--status-fd", "1", "--keyring", key,
                     signature, source)
    if not re.search(r"(?m)^\[GNUPG:\] VALIDSIG " + re.escape(manifest["signerFingerprint"]) + r" ", status):
        raise ValueError("source signature does not match the recorded signer")


def build(args):
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text())
    product_revision = manifest["productRevision"]
    if not re.fullmatch(r"[0-9a-f]{40}", product_revision):
        raise ValueError("productRevision must be an exact Git commit")
    source = Path(args.source).absolute()
    signature = Path(args.signature).absolute()
    key = manifest_path.parent / "release-key.gpg"
    verify(source, signature, key, manifest, args.gpgv)
    # The helper comes from the recorded public commit, never a working file.
    helper = subprocess.check_output(["git", "-C", args.product_repo, "show",
                                      f"{product_revision}:commands/tam-nut/tam-nut"])
    if hashlib.sha256(helper).hexdigest() != manifest["helperSha256"]:
        raise ValueError("recorded helper digest does not match its commit")
    assembly = Path(__file__).resolve().parents[1]
    assembly_revision = run("git", "-C", assembly, "rev-parse", "HEAD").strip()
    for path in [Path(__file__).resolve(), manifest_path, key]:
        tracked = subprocess.check_output(["git", "-C", str(assembly), "show",
                                           f"{assembly_revision}:{path.relative_to(assembly)}"])
        if tracked != path.read_bytes():
            raise ValueError("commit the assembly recipe and inputs before building media")
    destination = Path(args.output_dir).absolute()
    if destination.is_symlink() or any(p.is_symlink() for p in destination.parents):
        raise ValueError("refusing a symlink output directory")
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"tamlinux-bootstrap-{product_revision[:12]}.iso"
    receipt_path = output.with_suffix(".json")
    if output.exists() or receipt_path.exists():
        raise ValueError("output exists; preserve or remove the previous image explicitly")
    tools = Path(args.tools).resolve()
    xorriso, mksquashfs, unsquashfs = [tools / x for x in ("xorriso", "mksquashfs", "unsquashfs")]
    with tempfile.TemporaryDirectory(prefix="tam-nut-", dir=destination) as temp:
        work = Path(temp)
        rootfs = work / "airootfs.sfs"
        run(xorriso, "-osirrox", "on", "-indev", source,
            "-extract", "/arch/x86_64/airootfs.sfs", rootfs)
        rootfs.chmod(0o600)
        added = work / "tam-nut"
        added.write_bytes(helper)
        added.chmod(0o755)
        # Append one new root file. Existing files, ownership, extended attributes
        # and compressed blocks remain in the source filesystem; no root unpack.
        run(mksquashfs, added, rootfs, "-processors", "2", "-no-recovery",
            "-force-uid", "0", "-force-gid", "0", "-quiet")
        actual = subprocess.check_output([str(unsquashfs), "-cat", str(rootfs), "tam-nut"])
        if actual != helper:
            raise ValueError("appended helper failed readback")
        checksums = work / "airootfs.sha512"
        checksums.write_text(digest(rootfs, "sha512") + "  airootfs.sfs\n")
        receipt = {"kind": "development-bootstrap", "source": manifest["sourceUrl"],
                   "sourceSha256": manifest["sourceSha256"], "signerFingerprint": manifest["signerFingerprint"],
                   "productRevision": product_revision, "assemblyRevision": assembly_revision,
                   "helperSha256": manifest["helperSha256"], "rootfsSha256": digest(rootfs),
                   "tools": {tool.name: run(tool, "-version").splitlines()[0]
                             for tool in [xorriso, mksquashfs, unsquashfs]}}
        inner_receipt = work / "bootstrap.json"
        inner_receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        readme = work / "TAMLINUX.txt"
        readme.write_text("Tamlinux development bootstrap (Arch-based)\n\n"
                          "After the live shell starts, run /tam-nut welcome, then /tam-nut inspect.\n"
                          "No disk installation or remote access starts automatically.\n"
                          "The upstream ISO was signature-verified before remastering. This derived\n"
                          "media is unsigned; the original rootfs signature no longer applies.\n")
        temporary = work / "bootstrap.iso"
        run(xorriso, "-indev", source, "-outdev", temporary,
            "-map", rootfs, "/arch/x86_64/airootfs.sfs",
            "-map", checksums, "/arch/x86_64/airootfs.sha512",
            "-rm", "/arch/x86_64/airootfs.sfs.cms.sig", "--",
            "-map", inner_receipt, "/tamlinux/bootstrap.json",
            "-map", readme, "/TAMLINUX.txt",
            "-boot_image", "any", "replay", "-commit", "-end")
        boot = run(xorriso, "-indev", temporary, "-report_el_torito", "plain")
        if "BIOS" not in boot or "UEFI" not in boot:
            raise ValueError("derived image lacks BIOS or UEFI boot metadata")
        receipt["imageSha256"] = digest(temporary)
        receipt["imageBytes"] = temporary.stat().st_size
        temporary.replace(output)
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(output)
    print(receipt_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["manifest", "source", "signature", "product-repo", "tools", "output-dir"]:
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--gpgv", default="gpgv")
    args = parser.parse_args()
    try:
        build(args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"build-nut: {exc}\n")


if __name__ == "__main__":
    main()
