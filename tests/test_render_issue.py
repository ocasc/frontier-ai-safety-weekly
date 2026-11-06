#!/usr/bin/env python3
"""Regression tests for the public long-image renderer (synthetic data only)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("render_issue", ROOT / "scripts/render_issue.py")
assert spec is not None and spec.loader is not None
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def fixture() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cats = ["错对齐与欺骗", "错对齐与欺骗", "控制"]
    ranks = [1, 3, 2]
    titles = ["one", "two", "three"]
    manifest = [dict(title=t, category=c, importance_rank=r) for t, c, r in zip(titles, cats, ranks)]
    checks = dict(cards=["1", "2", "3"], tldr=["1", "2", "3"], links=["1", "2", "3"],
                  titles=titles, hasMasthead=False, tlLens=[4, 4, 4], cellLens=[], titleLens=[4, 4, 4],
                  categories=cats[:], tldrCategories=cats[:], categoryHeads=[cats[0], cats[2]],
                  mapHeads=[cats[0], cats[2]], importanceRanks=ranks[:], tableColumns=[], declaredColumns=[],
                  tableAlignments=[], images=[], scrollWidth=480, nodes=[], tldrPanel=True)
    return checks, manifest


class FakePage:
    def __init__(self, data):
        self.data = data

    def evaluate(self, script):
        return self.data


class StructuralChecks(unittest.TestCase):
    def setUp(self):
        self.checks, self.manifest = fixture()

    def run_check(self):
        return render.run_checks(FakePage(self.checks), self.manifest, "synthetic")

    def test_valid_grouped_ranks(self):
        self.run_check()

    def test_duplicate_rank_fails_even_if_manifest_matches(self):
        self.checks["importanceRanks"][1] = 1
        self.manifest[1]["importance_rank"] = 1
        with self.assertRaisesRegex(AssertionError, "unique positive"):
            self.run_check()

    def test_interleaved_categories_fail_even_if_manifest_matches(self):
        cats = ["错对齐与欺骗", "控制", "错对齐与欺骗"]
        ranks = [1, 2, 3]
        self.checks["categories"] = cats[:]
        self.checks["tldrCategories"] = cats[:]
        self.checks["importanceRanks"] = ranks[:]
        for row, cat, rank in zip(self.manifest, cats, ranks):
            row["category"], row["importance_rank"] = cat, rank
        with self.assertRaisesRegex(AssertionError, "categories must be contiguous"):
            self.run_check()

    def test_missing_image_is_rejected(self):
        self.checks["images"] = [{"src": "img/missing.png", "loaded": False}]
        with self.assertRaisesRegex(AssertionError, "images failed to load"):
            self.run_check()

    def test_title_mismatch_is_rejected(self):
        self.manifest[0]["title"] = "different"
        with self.assertRaisesRegex(AssertionError, "titles"):
            self.run_check()


class BrowserAndRender(unittest.TestCase):
    def test_current_category_head_fallback(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=render.find_chrome(), headless=True)
            try:
                page = browser.new_page(viewport={"width": 480, "height": 900})
                page.goto((ROOT / "issues/demo/issue.html").as_uri())
                page.evaluate("document.querySelectorAll('.map-item').forEach(e => e.removeAttribute('data-category'))")
                self.assertEqual(render.run_checks(page, render.load_manifest(ROOT / "issues/demo"), "fallback")["tldrCategories"],
                                 ["错对齐与欺骗", "错对齐与欺骗", "控制"])
                for label in ["错对齐与欺骗", "控制", "评估与审计", "可解释性", "保证与标准"]:
                    page.locator('.map-head').first.evaluate('(e, label) => e.textContent = label', label)
                    self.assertEqual(page.evaluate(render.CHECK_JS)["tldrCategories"][0], label)
                page.locator('.map-head').first.evaluate('(e) => e.textContent = "unknown"')
                self.assertIsNone(page.evaluate(render.CHECK_JS)["tldrCategories"][0])
                page.locator('.map-head').first.evaluate('(e) => e.textContent = "Misalignment｜错对齐案例"')
                self.assertEqual(page.evaluate(render.CHECK_JS)["tldrCategories"][0], "错对齐")
            finally:
                browser.close()

    def test_cli_render_from_outside_repository(self):
        with tempfile.TemporaryDirectory(prefix="biweekly-test-") as temp:
            issue = Path(temp) / "demo"
            shutil.copytree(ROOT / "issues/demo", issue)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/render_issue.py"), str(issue)],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("3 cards PASS", result.stdout)
            with zipfile.ZipFile(issue / "demo.zip") as z:
                self.assertIsNone(z.testzip())
                self.assertIn("issue.html", z.namelist())
                self.assertIn("importance_order.json", z.namelist())
            report = json.loads((issue / "qa/demo_checks.json").read_text())
            self.assertEqual(report["categories"], ["错对齐与欺骗", "错对齐与欺骗", "控制"])
            self.assertEqual(len(list((issue / "wechat_upload").glob("part*.png"))), 5)


if __name__ == "__main__":
    unittest.main()
