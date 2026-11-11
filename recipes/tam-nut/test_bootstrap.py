"""Exercise the packaged scripts and policy against a temporary root."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

RECIPE = Path(__file__).resolve().parent


class Bootstrap(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        (self.root / "usr/bin").mkdir(parents=True)
        self.slot = self.root / "usr/lib/tamlinux"
        self.slot.mkdir(parents=True)

    def executable(self, name, script):
        path = self.root / "usr/bin" / name
        path.write_text(f"#!/bin/sh\n{script}\n")
        path.chmod(0o755)

    def run_helper(self, helper, args=(), inputs=""):
        text = (RECIPE / helper).read_text()
        text = re.sub(r"/usr/bin/(tam-start|tam-bundle|tam-nut|tam|pacman|realpath|systemctl)(?= )",
                      lambda match: f"{self.root}{match.group()}", text)
        text = text.replace("slot=/usr/lib/tamlinux", f"slot={self.slot}")
        shell = "/usr/bin/bash" if helper in ("guard-removal", "user-units-reload") else "/usr/bin/sh"
        return subprocess.run([shell, "-c", text, helper, *args], text=True, input=inputs,
                              capture_output=True, env={"PATH": os.defpath, "HOME": str(self.home)}, check=False)

    def test_only_the_fixed_apply_command_is_delegated(self):
        self.executable("tam-bundle", 'printf "%s\\n" "$@"')
        transaction = "a" * 32
        self.assertEqual(self.run_helper("apply-prepared", (transaction,)).stdout, "apply\n" + transaction + "\n")
        self.assertEqual(self.run_helper("apply-prepared").returncode, 2)
        self.assertEqual(self.run_helper("apply-prepared", ("x" * 32,)).returncode, 2)
        self.assertEqual(self.run_helper("apply-prepared", ("--root", "/tmp")).returncode, 2)
        policy = ET.parse(RECIPE / "org.tamlinux.bundle.apply.policy")
        action = policy.find("action")
        self.assertEqual(action.attrib["id"], "org.tamlinux.bundle.apply")
        self.assertEqual(action.find("annotate").text, "/usr/lib/tam-nut/apply-prepared")
        self.assertEqual([child.text for child in action.find("defaults")], ["no"] * 3)

    def test_console_aliases_fall_back_and_forward_to_the_real_commands(self):
        self.executable("tam-nut", 'printf "%s\\n" "$@"')
        for alias in ("start", "hi"):
            self.assertEqual(self.run_helper(alias).stdout, "welcome\n")
        self.executable("tam", 'printf "%s\\n" "$@"')
        self.assertEqual(self.run_helper("hi", ("argument",)).stdout, "hi\nargument\n")
        self.executable("tam-start", 'printf "%s\\n" "$@"')
        self.assertEqual(self.run_helper("start", ("--list",)).stdout, "--list\n")

    def test_removal_refuses_only_the_providers_needed_by_the_live_bundle(self):
        self.assertEqual(self.run_helper("guard-removal", inputs="arbitrary\n").returncode, 0)
        version = self.slot / "version/demo"
        version.mkdir(parents=True)
        (self.slot / "current").symlink_to("version/demo")
        (version / "BUNDLE").write_text(
            "format 2\nneeds file /usr/lib/libfixture.so\n"
            "needs qml Example.Widgets 1.0 arch=qml-provider\nneeds tam-bundle >= 0.9.0\n"
        )
        self.executable("pacman", """
[ "$1 $2" = '-Ql --' ] || exit 2
case "$3" in
  library) printf '%s\n' 'library /usr/lib/libfixture.so' ;;
  qml-provider|tam-nut|arbitrary) printf '%s\n' "$3 /usr/share/fixture" ;;
  *) exit 1 ;;
esac
""")
        self.executable("realpath", "exit 1")
        self.assertEqual(self.run_helper("guard-removal", inputs="arbitrary\n").returncode, 0)
        for package in ("library", "qml-provider", "tam-nut"):
            result = self.run_helper("guard-removal", inputs=package + "\n")
            self.assertEqual(result.returncode, 1)
            self.assertIn(f"Cannot remove {package}", result.stderr)
        self.assertEqual(self.run_helper("guard-removal", inputs="unknown\n").returncode, 1)

    def test_user_unit_stop_and_retry_preserve_the_active_set(self):
        version = self.slot / "version/demo"
        version.mkdir(parents=True)
        (self.slot / "current").symlink_to("version/demo")
        manifest = version / "MANIFEST"
        manifest.write_text(
            "format 2\np f 0644 sha256:fixture usr/lib/systemd/user/tam-demo.service\n"
            "p f 0644 sha256:fixture usr/lib/systemd/user/tam-inactive.timer\n"
        )
        actions = self.root / "actions"
        failure = self.root / "fail"
        self.executable("systemctl", f"""
echo "$*" >> "{actions}"
case "$2" in
  show-environment|daemon-reload|stop) exit 0 ;;
  is-active) [ "$4" = tam-demo.service ] ;;
  show) echo "/usr/lib/systemd/user/${{5}}" ;;
  start) [ ! -f "{failure}" ] ;;
  *) exit 2 ;;
esac
""")
        transaction = "b" * 32
        self.assertEqual(self.run_helper("user-units-reload", ("stop", transaction)).returncode, 0)
        record = self.home / ".local/state/tamlinux/units" / transaction
        self.assertEqual(record.read_text(), "tam-demo.service\n")
        self.assertEqual(record.stat().st_mode & 0o777, 0o600)
        failure.touch()
        self.assertEqual(self.run_helper("user-units-reload", ("apply", transaction)).returncode, 1)
        self.assertTrue(record.exists())
        failure.unlink()
        self.assertEqual(self.run_helper("user-units-reload", ("apply", transaction)).returncode, 0)
        self.assertFalse(record.exists())
        history = actions.read_text()
        self.assertIn("--user stop -- tam-demo.service", history)
        self.assertIn("--user start -- tam-demo.service", history)
        self.assertNotIn("--user start -- tam-inactive.timer", history)


if __name__ == "__main__":
    unittest.main()
