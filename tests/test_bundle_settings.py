"""The portable UX list covers generated defaults without taking browser state."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BundleSettings(unittest.TestCase):
    def test_browser_registrations_are_selected_without_browser_profiles(self):
        lines = (ROOT / 'recipes/workstation/SETTINGS').read_text().splitlines()
        paths = dict(line.split()[::-1] for line in lines if line.startswith(('common ', 'host ')))
        browsers = ('chromium', 'google-chrome', 'google-chrome-beta', 'google-chrome-unstable',
                    'BraveSoftware/Brave-Browser', 'BraveSoftware/Brave-Browser-Beta',
                    'BraveSoftware/Brave-Browser-Nightly', 'microsoft-edge', 'microsoft-edge-dev')
        for browser in browsers:
            self.assertNotIn('.config/' + browser + '/', paths)
            for host in ('copy_url', 'ytdlp'):
                self.assertEqual(paths[f'.config/{browser}/NativeMessagingHosts/org.tamlinux.{host}.json'], 'common')
        for name in ('menu/', 'chromium/extensions/', 'session/hyprland.lua', 'hyprland/', 'screensaver/',
                     'backgrounds/', 'clock/', 'defaults/', 'macros.json', 'tam-edit/', 'themes/'):
            self.assertEqual(paths['.config/tamlinux/' + name], 'common')
        for name in ('monitors.lua', 'input.lua'):
            self.assertEqual(paths['.config/tamlinux/hypr/' + name], 'host')
        for state_common in ('shell.toml', 'current/theme.name', 'current/background.selection',
                             'defaults/editor', 'settings/weather.json', 'settings/tides.json',
                             'desktop-mode', 'workspace-layouts/', 'toggles/'):
            self.assertEqual(paths['.local/state/tamlinux/' + state_common], 'common')
        self.assertEqual(paths['.local/state/tamlinux/toggles/hypr/'], 'host')
        self.assertNotIn('.local/state/tamlinux/', paths)
        self.assertNotIn('.local/state/tamlinux/current/theme/', paths)
        self.assertNotIn('.local/state/tamlinux/theme-generations/', paths)
        self.assertFalse(any(p.startswith(('/etc/', '.ssh/', '.codex/', '.gnupg/')) for p in paths))
