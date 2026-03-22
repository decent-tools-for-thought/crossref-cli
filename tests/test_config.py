from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossref_tool import config as config_module


class ConfigTests(unittest.TestCase):
    def test_load_config_merges_saved_values_with_defaults(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_path = config_dir / "config.toml"
            config_path.write_text(
                '[pool]\nemail = "user@example.com"\n\n[works]\ndefault_rows = 50\n',
                encoding="utf-8",
            )

            with (
                patch.object(config_module, "CONFIG_DIR", config_dir),
                patch.object(config_module, "CONFIG_PATH", config_path),
            ):
                loaded = config_module.load_config()

        self.assertEqual(loaded["pool"]["default"], "public")
        self.assertEqual(loaded["pool"]["email"], "user@example.com")
        self.assertEqual(loaded["works"]["default_rows"], 50)
        self.assertEqual(loaded["output"]["default_format"], "jsonl")

    def test_save_config_writes_toml_scalars(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_path = config_dir / "config.toml"
            config = {
                "api": {"base_url": "https://api.crossref.org"},
                "pool": {"default": "polite", "email": "user@example.com", "api_key": ""},
                "works": {"default_rows": 25, "max_rows": 250},
                "cache": {"enabled": True, "ttl_seconds": 300},
                "output": {"default_format": "json", "default_select": 'DOI,title,"quoted"'},
            }

            with (
                patch.object(config_module, "CONFIG_DIR", config_dir),
                patch.object(config_module, "CONFIG_PATH", config_path),
            ):
                config_module.save_config(config)

            content = config_path.read_text(encoding="utf-8")

        self.assertIn("[cache]", content)
        self.assertIn("enabled = true", content)
        self.assertIn('default_select = "DOI,title,\\"quoted\\""', content)

    def test_reset_config_restores_defaults_and_writes_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_path = config_dir / "config.toml"

            with (
                patch.object(config_module, "CONFIG_DIR", config_dir),
                patch.object(config_module, "CONFIG_PATH", config_path),
            ):
                config = config_module.reset_config()

            saved = config_path.read_text(encoding="utf-8")

        self.assertEqual(config, config_module.DEFAULT_CONFIG)
        self.assertIn('[pool]\ndefault = "public"', saved)
