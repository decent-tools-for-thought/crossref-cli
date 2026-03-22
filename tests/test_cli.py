from __future__ import annotations

import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossref_tool import cli


class CliTests(unittest.TestCase):
    def test_main_uses_default_output_format_from_config(self) -> None:
        config = {
            "api": {"base_url": "https://api.crossref.org"},
            "pool": {"default": "public", "email": "", "api_key": ""},
            "works": {"default_rows": 20, "max_rows": 1000},
            "output": {
                "default_format": "text",
                "default_select": "DOI,title",
            },
        }
        service = Mock()
        service.search_members.return_value = {
            "items": [{"resource": "member", "title": "ACM", "id": "98", "data": {}}],
            "meta": {},
        }

        stdout = StringIO()
        with (
            patch("crossref_tool.cli.load_config", return_value=config),
            patch("crossref_tool.cli.CrossrefService", return_value=service),
            patch("sys.stdout", stdout),
        ):
            exit_code = cli.main(["members", "search", "acm"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "ACM\t98")

    def test_main_reports_config_validation_errors(self) -> None:
        config = {
            "api": {"base_url": "https://api.crossref.org"},
            "pool": {"default": "public", "email": "", "api_key": ""},
            "works": {"default_rows": 20, "max_rows": 1000},
            "output": {
                "default_format": "jsonl",
                "default_select": "DOI,title",
            },
        }
        stderr = StringIO()
        with (
            patch("crossref_tool.cli.load_config", return_value=config),
            patch("sys.stderr", stderr),
        ):
            exit_code = cli.main(["config", "set", "pool", "invalid"])

        self.assertEqual(exit_code, 2)
        self.assertIn("pool must be one of", stderr.getvalue())
