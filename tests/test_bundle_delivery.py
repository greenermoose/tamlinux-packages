"""Frozen recipe identity, public artifact capture and atomic publication."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "tools/bundle-delivery.py"
SPEC = importlib.util.spec_from_file_location("bundle_delivery", SCRIPT)
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)


class BundleDelivery(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / "repo"
        recipe = self.repo / "recipes/workstation"
        recipe.mkdir(parents=True)
        (recipe / "tamlinux.lock").write_text(
            "format 1\ncomponent tamlinux https://example.invalid/product " + "1" * 40 + "\n"
        )
        (self.repo / "VERSION").write_text("9.8.7\n")
        for args in (("init", "-q", str(self.repo)),
                     ("-C", str(self.repo), "add", "recipes/workstation/tamlinux.lock", "VERSION"),
                     ("-C", str(self.repo), "-c", "user.name=Fixture",
                      "-c", "user.email=fixture@example.invalid", "commit", "-qm", "recipe")):
            subprocess.run(["git", *args], check=True)
        self.assembly = delivery.git(self.repo, "rev-parse", "HEAD")
        self.tool = self.root / "verify"
        self.tool.write_text('#!/bin/sh\n[ "$1" = verify ]\n')
        self.tool.chmod(0o755)
        self.archive = self.root / "bundle.tbundle"
        self.output = self.root / "tamlinux-9.8.7.json"
        self.cache = self.root / "cache"
        self.bundle()

    def bundle(self, revision="1" * 40, private=False):
        metadata = (
            "format 2\nname tamlinux\nversion 9.8.7\nhash sha256:" + "a" * 64 + "\n"
            "target profile arch-systemd\nsource tamlinux " + revision + "\n"
            "source packaging " + self.assembly + "\n"
        ).encode()
        with tarfile.open(self.archive, "w") as archive:
            entry = tarfile.TarInfo("BUNDLE")
            entry.size = len(metadata)
            archive.addfile(entry, io.BytesIO(metadata))
            if private:
                entry = tarfile.TarInfo("capture/CAPTURE")
                archive.addfile(entry, io.BytesIO(b""))

    def record(self):
        return delivery.record(self.repo, self.archive, self.tool, self.output, self.cache)

    def test_record_binds_the_frozen_recipe_and_public_archive(self):
        result = self.record()
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.assertEqual(result["recipeAssembly"], self.assembly)
        self.assertEqual(result["artifact"]["sha256"], digest)
        self.assertEqual(result["components"], {"tamlinux": "1" * 40})
        self.assertEqual((self.cache / (digest + ".tbundle")).read_bytes(), self.archive.read_bytes())
        self.assertEqual(json.loads(self.output.read_text()), result)
        self.assertNotIn(str(self.root), self.output.read_text())
        with self.assertRaises(FileExistsError):
            self.record()
        self.assertEqual(json.loads(self.output.read_text()), result)

    def test_source_mismatch_is_refused_before_publication(self):
        self.bundle(revision="2" * 40)
        with self.assertRaisesRegex(ValueError, "frozen recipe lock"):
            self.record()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.cache.exists())

    def test_private_capture_cannot_become_a_public_delivery(self):
        self.bundle(private=True)
        with self.assertRaisesRegex(ValueError, "private settings"):
            self.record()
        self.assertFalse(self.output.exists())

    def test_copy_mutation_does_not_publish_a_poisoned_cache_entry(self):
        original = delivery.publish
        def changed(path, writer):
            if path.parent == self.cache:
                self.archive.write_bytes(b"changed while copying")
            return original(path, writer)
        with patch.object(delivery, "publish", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "changed while copying"):
                self.record()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_failed_publication_preserves_the_existing_record(self):
        self.output.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            delivery.publish(self.output, lambda stream: stream.write(b"replacement"))
        self.assertEqual(self.output.read_bytes(), b"existing")
        missing = self.root / "incomplete"
        def fail(stream):
            stream.write(b"partial")
            raise OSError("interrupted")
        with self.assertRaises(OSError):
            delivery.publish(missing, fail)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
