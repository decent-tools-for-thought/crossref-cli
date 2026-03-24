from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossref_tool.http import HttpClient


class HttpClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = HttpClient(headers={"User-Agent": "test-agent"})

    def test_get_json_includes_transport_reason_on_url_error(self) -> None:
        with (
            patch("crossref_tool.http.urlopen", side_effect=URLError("timed out")),
            patch("crossref_tool.http.time.sleep"),
        ):
            with self.assertRaises(RuntimeError) as context:
                self.client.get_json("https://api.crossref.org/works")

        self.assertIn(
            "Request failed: https://api.crossref.org/works (timed out)",
            str(context.exception),
        )

    def test_resolve_url_includes_transport_reason_with_redirect_follow(self) -> None:
        with patch("crossref_tool.http.urlopen", side_effect=URLError("connection reset")):
            with self.assertRaises(RuntimeError) as context:
                self.client.resolve_url("https://doi.org/10.1000/xyz", follow_redirects=True)

        self.assertIn(
            "Request failed: https://doi.org/10.1000/xyz (connection reset)",
            str(context.exception),
        )

    def test_resolve_url_includes_transport_reason_without_redirect_follow(self) -> None:
        opener = Mock()
        opener.open.side_effect = URLError("dns failure")
        with patch("crossref_tool.http.build_opener", return_value=opener):
            with self.assertRaises(RuntimeError) as context:
                self.client.resolve_url("https://doi.org/10.1000/xyz", follow_redirects=False)

        self.assertIn(
            "Request failed: https://doi.org/10.1000/xyz (dns failure)",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
