"""The old compositor outlives SDDM; no native action runs in these tests."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("login_transaction", Path(__file__).resolve().parents[1] / "tools/login-transaction.py")
login = importlib.util.module_from_spec(spec)
spec.loader.exec_module(login)


class FakeHost:
    def __init__(self, stopped=(), started=()):
        self.events = []
        self.stop_states = iter(stopped)
        self.start_states = iter(started)

    def stop(self): self.events.append("stop")
    def start(self): self.events.append("start")
    def stopped(self): return next(self.stop_states, False)
    def started(self): return next(self.start_states, False)
    def recover(self, vt): self.events.extend(["stop", f"vt{vt}"])


class LoginTransactionTests(unittest.TestCase):
    def timing(self):
        self.now = 0
        def sleep(seconds): self.now += seconds
        return {"clock": lambda: self.now, "sleep": sleep}

    def test_slow_shutdown_is_fully_gone_before_apply_or_start(self):
        host = FakeHost(stopped=[False] * 34 + [True], started=[False, True])
        timing = self.timing()
        login.stop(host, **timing)
        host.events.append("apply")
        login.start(host, 3, **timing)
        self.assertEqual(host.events, ["stop", "apply", "start"])
        self.assertGreaterEqual(self.now, 17)

    def test_shutdown_timeout_never_applies_or_restarts(self):
        host = FakeHost()
        with self.assertRaises(TimeoutError):
            login.stop(host, timeout=2, **self.timing())
            host.events.append("apply")
            login.start(host, 3)
        self.assertEqual(host.events, ["stop"])
        self.assertEqual(self.now, 2)

    def test_failed_autologin_stops_sddm_and_switches_to_recovery(self):
        host = FakeHost()
        with self.assertRaises(TimeoutError):
            login.start(host, 3, timeout=2, **self.timing())
        self.assertEqual(host.events, ["start", "stop", "vt3"])

    def test_start_command_failure_also_returns_to_console(self):
        host = FakeHost()
        def fail(): raise subprocess.CalledProcessError(1, "systemctl")
        host.start = fail
        with self.assertRaises(subprocess.CalledProcessError):
            login.start(host, 4)
        self.assertEqual(host.events, ["stop", "vt4"])

    def test_probe_error_is_not_evidence_of_shutdown(self):
        host = FakeHost()
        host.stopped = lambda: (_ for _ in ()).throw(ValueError("bad state"))
        with self.assertRaises(ValueError): login.stop(host, **self.timing())
        self.assertEqual(host.events, ["stop"])

    def test_wayland_or_process_alone_blocks_shutdown(self):
        host = login.Host.__new__(login.Host)
        for sessions, compositor in [([{}], False), ([], True), ([{}], True), ([], False)]:
            host.sessions = lambda: sessions
            host.compositor = lambda: compositor
            self.assertEqual(host.stopped(), not sessions and not compositor)

    def test_started_requires_active_sddm_session_and_process(self):
        host = login.Host.__new__(login.Host)
        for service, active, compositor, expected in [
            ("sddm-autologin", "yes", True, True), ("sddm", "yes", True, True),
            ("login", "yes", True, False), ("sddm", "no", True, False),
            ("sddm", "yes", False, False)]:
            host.sessions = lambda: [{"Service": service, "Active": active}]
            host.compositor = lambda: compositor
            self.assertEqual(host.started(), expected)

    def test_recovery_switches_even_if_sddm_stop_fails(self):
        host = login.Host.__new__(login.Host)
        with patch.object(host, "stop", side_effect=RuntimeError("stop failed")), patch.object(host, "command") as command:
            with self.assertRaises(RuntimeError): host.recover(3)
            command.assert_called_once_with("/usr/bin/chvt", "3")
