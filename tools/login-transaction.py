#!/usr/bin/env python3
"""Bounded SDDM maintenance steps. Execute only in an approved login transaction.

stop waits for the old user's Wayland sessions AND Hyprland processes to end.
start requires a new active SDDM Wayland session AND a compositor; failure stops
SDDM and returns to the retained recovery VT. Neither command applies login files.
"""
import argparse
import pwd
import subprocess
import sys
import time


class Host:
    def __init__(self, user):
        self.user = user
        self.uid = pwd.getpwnam(user).pw_uid
        self.probe_deadline = None

    def command(self, *args):
        timeout = 10 if self.probe_deadline is None else self.probe_deadline - time.monotonic()
        if timeout <= 0:
            raise TimeoutError("login state query exceeded its deadline")
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=min(10, timeout)).stdout

    def sessions(self):
        self.probe_deadline = time.monotonic() + 3
        ids = [line.split()[0] for line in self.command(
            "/usr/bin/loginctl", "list-sessions", "--no-legend", "--no-pager").splitlines() if line.strip()]
        sessions = []
        for sid in ids:
            # A session may disappear between list and show. Fail closed and retry
            # on the next invocation rather than treating unknown state as stopped.
            text = self.command("/usr/bin/loginctl", "show-session", sid,
                                "-p", "Name", "-p", "Type", "-p", "Active", "-p", "Service")
            values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
            if values.get("Name") == self.user and values.get("Type") == "wayland":
                sessions.append(values)
        return sessions

    def compositor(self):
        result = subprocess.run(["/usr/bin/pgrep", "-u", str(self.uid), "-x", "Hyprland"],
                                capture_output=True, text=True, timeout=2)
        if result.returncode not in (0, 1):
            raise RuntimeError("cannot inspect Hyprland processes")
        return result.returncode == 0

    def stopped(self):
        return not self.sessions() and not self.compositor()

    def started(self):
        return any(s.get("Active") == "yes" and s.get("Service") in ("sddm", "sddm-autologin")
                   for s in self.sessions()) and self.compositor()

    def stop(self):
        self.probe_deadline = None
        self.command("/usr/bin/systemctl", "stop", "sddm.service")

    def start(self):
        self.probe_deadline = None
        self.command("/usr/bin/systemctl", "start", "sddm.service")

    def recover(self, vt):
        # Even a failed stop must not prevent returning to the text console.
        try:
            self.stop()
        finally:
            self.probe_deadline = None
            self.command("/usr/bin/chvt", str(vt))


def wait_for(probe, timeout, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    while True:
        if probe():
            return
        if clock() >= deadline:
            raise TimeoutError(f"login state did not settle within {timeout:g} seconds")
        sleep(min(0.5, max(0, deadline - clock())))


def stop(host, timeout=60, **timing):
    host.stop()
    # A timeout propagates: the caller must not apply files or start SDDM.
    wait_for(host.stopped, timeout, **timing)


def start(host, recovery_vt, timeout=30, **timing):
    try:
        host.start()
        wait_for(host.started, timeout, **timing)
    except BaseException:
        host.recover(recovery_vt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("stop", "start"))
    parser.add_argument("--user", required=True)
    parser.add_argument("--recovery-vt", type=int, required=True)
    args = parser.parse_args()
    if not 2 <= args.recovery_vt <= 63:
        parser.error("retain a text console on VT2–VT63")
    host = Host(args.user)
    try:
        if args.step == "stop":
            stop(host)
        else:
            start(host, args.recovery_vt)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"login-transaction: {error}; keep the recovery console open", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
