import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/build-nut.py"
spec = importlib.util.spec_from_file_location("build_nut", SCRIPT)
nut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nut)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.source, self.signature, self.key = [root / name for name in ["source.iso", "source.sig", "key.gpg"]]
        for path in [self.source, self.signature, self.key]:
            path.write_bytes(path.name.encode())
        self.manifest = {"sourceSha256": nut.digest(self.source), "signatureSha256": nut.digest(self.signature),
                         "keySha256": nut.digest(self.key), "signerFingerprint": "A" * 40}
        self.verifier = root / "verifier"
        self.verifier.write_text("#!/bin/sh\nprintf '%s\\n' '[GNUPG:] VALIDSIG " + "A" * 40 + " 2026-01-01'\n")
        self.verifier.chmod(0o755)

    def verify(self):
        nut.verify(self.source, self.signature, self.key, self.manifest, str(self.verifier))

    def test_expected_digest_and_signer_are_both_required(self):
        self.verify()
        self.manifest["signerFingerprint"] = "B" * 40
        with self.assertRaisesRegex(ValueError, "recorded signer"):
            self.verify()

    def test_each_input_is_verified_before_execution(self):
        for path in [self.source, self.signature, self.key]:
            original = path.read_bytes()
            path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "unverified input"):
                self.verify()
            path.write_bytes(original)

    def test_symlink_source_is_rejected(self):
        target = self.source.with_suffix(".other")
        self.source.rename(target)
        self.source.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "unverified input"):
            self.verify()

    def test_failed_signature_process_stops_build(self):
        self.verifier.write_text("#!/bin/sh\nexit 1\n")
        with self.assertRaisesRegex(ValueError, "failed"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
