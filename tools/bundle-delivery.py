#!/usr/bin/env python3
"""Record an already verified bundle built from a frozen recipe assembly."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = re.compile(r"[0-9a-f]{40}\Z")
HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True, stderr=subprocess.PIPE
    ).strip()


def publish(path: Path, writer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            writer(stream)
            os.fchmod(stream.fileno(), 0o644)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


def read_metadata(stream) -> dict:
    stream.seek(0)
    metadata = None
    with tarfile.open(fileobj=stream, mode="r|*") as archive:
        for entry in archive:
            if entry.name == "capture" or entry.name.startswith("capture/"):
                raise ValueError("a public delivery cannot contain a private settings capture")
            if entry.name != "BUNDLE":
                continue
            if metadata is not None or not entry.isfile() or entry.size > 1024 * 1024:
                raise ValueError("invalid bundle metadata")
            metadata = archive.extractfile(entry).read().decode("utf-8")
    if metadata is None:
        raise ValueError("bundle metadata is missing")
    values = {}
    sources = {}
    profile = None
    for line in metadata.splitlines():
        key, separator, value = line.partition(" ")
        if not separator:
            raise ValueError("invalid bundle record")
        if key == "source":
            name, revision = value.split()
            if name in sources or not REVISION.fullmatch(revision):
                raise ValueError("invalid or repeated source")
            sources[name] = revision
        elif key == "target" and value.startswith("profile "):
            if profile is not None:
                raise ValueError("repeated rootstock profile")
            profile = value.removeprefix("profile ")
        elif key in ("format", "name", "version", "hash"):
            if key in values:
                raise ValueError("repeated bundle identity")
            values[key] = value
    if (values.get("format") != "2" or not HASH.fullmatch(values.get("hash", "")) or
            not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", values.get("version", "")) or
            values.get("name") != "tamlinux" or profile != "arch-systemd" or
            "packaging" not in sources or "tamlinux" not in sources):
        raise ValueError("expected an identified Arch workstation bundle")
    values["sources"] = sources
    values["profile"] = profile
    return values


def source_pins(root: Path, revision: str) -> dict:
    text = git(root, "show", revision + ":recipes/workstation/tamlinux.lock")
    lines = text.splitlines()
    if not lines or lines[0] != "format 1":
        raise ValueError("unsupported recipe lock")
    pins = {}
    for line in lines[1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if (len(fields) != 4 or fields[0] != "component" or fields[1] in pins or
                not REVISION.fullmatch(fields[3])):
            raise ValueError("invalid recipe lock")
        pins[fields[1]] = fields[3]
    return pins


def record(root: Path, archive: Path, tool: Path, output: Path, cache: Path) -> dict:
    fd = os.open(archive, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("bundle must be a regular archive")
        subprocess.run([str(tool), "verify", str(archive)], check=True)
        metadata = read_metadata(stream)
        assembly = metadata["sources"]["packaging"]
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", assembly, "HEAD"], check=True)
        pins = source_pins(root, assembly)
        sources = {name: revision for name, revision in metadata["sources"].items() if name != "packaging"}
        if pins != sources:
            raise ValueError("bundle sources differ from the frozen recipe lock")
        version = metadata["version"]
        if git(root, "show", assembly + ":VERSION") != version:
            raise ValueError("bundle version differs from the frozen recipe assembly")
        if output.name != f"tamlinux-{version}.json":
            raise ValueError("delivery filename must name the exact version")
        stream.seek(0)
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        after = os.fstat(stream.fileno())
        named = archive.stat(follow_symlinks=False)
        identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_ctime_ns)
        if identity(before) != identity(after) or identity(before) != identity(named):
            raise ValueError("bundle changed during verification")
        cached = cache / (digest + ".tbundle")
        if cached.exists():
            with cached.open("rb") as retained:
                if hashlib.file_digest(retained, "sha256").hexdigest() != digest:
                    raise ValueError("existing cached artifact has different bytes")
        else:
            def copy_verified(destination):
                stream.seek(0)
                copied = hashlib.sha256()
                while chunk := stream.read(1024 * 1024):
                    destination.write(chunk)
                    copied.update(chunk)
                if copied.hexdigest() != digest:
                    raise ValueError("bundle changed while copying into the artifact cache")
            try:
                publish(cached, copy_verified)
            except FileExistsError:
                with cached.open("rb") as retained:
                    if hashlib.file_digest(retained, "sha256").hexdigest() != digest:
                        raise ValueError("concurrent cached artifact has different bytes")
        with cached.open("rb") as retained:
            if hashlib.file_digest(retained, "sha256").hexdigest() != digest:
                raise ValueError("cached artifact verification failed")
        value = {
            "format": 1, "backend": "tam-bundle", "version": version,
            "recipeAssembly": assembly, "components": pins,
            "rootstock": metadata["profile"], "minimumTool": "0.13.0",
            "artifact": {
                "name": f"tamlinux-{version}-{metadata['hash'][7:19]}.tbundle",
                "sha256": digest, "bundleHash": metadata["hash"],
                "bundleId": f"tamlinux-{version}-{metadata['hash'][7:19]}",
            },
        }
        payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        publish(output, lambda destination: destination.write(payload))
        return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--tool", type=Path, default=Path("/usr/bin/tam-bundle"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path(
        os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
    ) / "tamlinux/bundles")
    args = parser.parse_args()
    try:
        value = record(ROOT, args.archive.resolve(), args.tool.resolve(), args.output, args.cache)
    except (OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"bundle-delivery: {error}\n")
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
