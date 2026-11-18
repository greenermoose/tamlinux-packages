# Bug 0003 — Desktop startup tries to launch missing udiskie

- **Status:** Fix available.
- **Severity:** Low. Desktop startup shows an app failure notification.
- **Affected:** Tamlinux 0.6.28 bundle on systems without `udiskie`.
- **Fixed:** In source on `develop` for 0.6.29.
- **Next:** Confirm the notification is gone at the first 0.6.29 login.

## Reproduce

Start the 0.6.28 desktop on an Arch host without `udiskie` on the session
path. UWSM shows `Command not found: "udiskie"`.

## Expected and actual

The desktop starts without a missing-app notification. The packaged startup
handler still requests `udiskie`, which Home Manager used to supply. The
bundle neither supplies it nor declares it as a native requirement.

## Fix and verification

Tamlinux drops the automatic launch and the legacy Home Manager dependency.
Users mount and unmount removable drives manually. The product's
`desktop/tests/test_session_defaults.py` caught the old launch through the
Lua session entry point and passed after the change.

## Resolution

Open pending installed verification.
