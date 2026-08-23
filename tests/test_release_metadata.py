"""Release metadata must follow the runtime version automatically."""

import re
import unittest
from pathlib import Path

from mineai import __version__
from mineai.cache import _CACHE_VALIDATION_VERSION


ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def setUp(self):
        match = re.search(r"BETAv(\d+)", __version__)
        self.assertIsNotNone(match, f"Unexpected runtime version: {__version__!r}")
        self.beta = match.group(1)
        self.exe_name = f"MineAI_Translator_Beta{self.beta}.exe"

    def test_build_docs_and_ci_use_current_executable(self):
        for relative in ("build.bat", ".github/workflows/tests.yml", "README.md"):
            content = (ROOT / relative).read_text(encoding="utf-8-sig")
            self.assertIn(self.exe_name, content, relative)
        spec = (ROOT / f"MineAI_Translator_Beta{self.beta}.spec").read_text(encoding="utf-8-sig")
        self.assertIn(self.exe_name.removesuffix(".exe"), spec)

    def test_user_dictionaries_are_not_bundled(self):
        spec = (ROOT / f"MineAI_Translator_Beta{self.beta}.spec").read_text(encoding="utf-8-sig")
        self.assertNotIn("dictionary.json", spec)
        self.assertNotIn("glossary.json", spec)

    def test_cache_marker_contains_release_and_validator_fingerprint(self):
        self.assertIn(__version__, _CACHE_VALIDATION_VERSION)
        self.assertRegex(_CACHE_VALIDATION_VERSION, r"\|[0-9a-f]{12}$")


if __name__ == "__main__":
    unittest.main()
