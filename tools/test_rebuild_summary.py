#!/usr/bin/env python3
"""Unit tests for prepare-candidate rebuild summarization."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "prepare_candidate", Path(__file__).with_name("prepare-candidate.py")
)
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


class RebuildSummaryTests(unittest.TestCase):
    def test_counts_checks_from_planned_block(self):
        log = """warning: dirty
these 3 derivations will be built:
  /nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-tam-theme-list-checks-1.drv
  /nix/store/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-tamlinux-shell-0.6.6.drv
  /nix/store/cccccccccccccccccccccccccccccccc-hi-checks-1.drv
building '/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-tam-theme-list-checks-1.drv'...
"""
        summary = prepare.summarize_rebuilds(log, 12.5)
        self.assertEqual(summary["drvRebuilds"], 3)
        self.assertEqual(summary["checkRebuilds"], 2)
        self.assertIn("tamlinux-shell-0.6.6", summary["required"])
        self.assertFalse(summary["reusedAllOutputs"])

    def test_empty_when_nothing_planned(self):
        summary = prepare.summarize_rebuilds("everything is already done\n", 0.1)
        self.assertEqual(summary["drvRebuilds"], 0)
        self.assertEqual(summary["checkRebuilds"], 0)


if __name__ == "__main__":
    unittest.main()
