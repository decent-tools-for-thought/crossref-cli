from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossref_tool.core import (
    CrossrefService,
    export_records,
    normalize_doi,
    normalize_work,
    render_output,
)


class FakeHttpClient:
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append((url, params))
        response = self.responses.get(url)
        if callable(response):
            return response(params)
        if response is None:
            raise AssertionError(f"Unexpected URL: {url}")
        return response

    def resolve_url(self, url: str, *, follow_redirects: bool) -> str:
        self.calls.append((url, {"follow_redirects": follow_redirects}))
        return (
            "https://resolved.example/item" if follow_redirects else "https://doi.org/10.1000/xyz"
        )


class CrossrefCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "api": {"base_url": "https://api.crossref.org"},
            "pool": {"default": "polite", "email": "user@example.com", "api_key": ""},
            "works": {"default_rows": 20, "max_rows": 1000},
            "output": {
                "default_format": "jsonl",
                "default_select": "DOI,title,author,published-online,URL,type",
            },
        }

    def test_normalize_doi_strips_prefix_and_url(self) -> None:
        self.assertEqual(normalize_doi("doi:10.1000/xyz"), "10.1000/xyz")
        self.assertEqual(normalize_doi("https://doi.org/10.1000/xyz"), "10.1000/xyz")

    def test_normalize_work_maps_minimal_payload(self) -> None:
        work = {
            "DOI": "10.1000/xyz",
            "title": ["Example"],
            "author": [
                {"given": "Ada", "family": "Lovelace", "sequence": "first", "affiliation": []}
            ],
            "URL": "https://doi.org/10.1000/xyz",
            "type": "journal-article",
            "published-online": {"date-parts": [[2024, 1, 2]]},
        }
        normalized = normalize_work(
            work, pool_used="polite", fields_requested="DOI,title", agency="crossref"
        )
        self.assertEqual(normalized["id"]["prefix"], "10.1000")
        self.assertEqual(normalized["publishedDate"], "2024-01-02")
        self.assertFalse(normalized["isPostedContent"])
        self.assertEqual(normalized["id"]["agency"], "crossref")

    def test_search_works_supports_cursor_pagination(self) -> None:
        responses = {
            "https://api.crossref.org/works": self._paged_work_response,
        }
        service = CrossrefService(config=self.config, client=FakeHttpClient(responses))
        result = service.search_works(
            query="test",
            filters=[],
            select="DOI,title",
            rows=1,
            cursor=None,
            max_results=2,
        )
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["meta"]["nextCursor"], "cursor-2")

    def test_search_works_maps_filters_facets_and_field_queries(self) -> None:
        responses = {
            "https://api.crossref.org/works": {
                "message": {
                    "items": [
                        {"DOI": "10.1000/xyz", "title": ["Example"], "type": "journal-article"}
                    ],
                    "total-results": 1,
                    "items-per-page": 20,
                }
            }
        }
        client = FakeHttpClient(responses)
        service = CrossrefService(config=self.config, client=client)

        service.search_works(
            query="graph learning",
            filters=["from-pub-date:2024-01-01", "type:journal-article"],
            select=None,
            rows=None,
            cursor=None,
            max_results=None,
            facets=["type-name:*", "published:*"],
            field_queries={"author": "Ada", "container-title": "Journal of Testing"},
        )

        _, params = client.calls[0]
        assert params is not None
        self.assertEqual(params["query"], "graph learning")
        self.assertEqual(params["filter"], "from-pub-date:2024-01-01,type:journal-article")
        self.assertEqual(params["facet"], "type-name:*,published:*")
        self.assertEqual(
            params["select"],
            "DOI,title,author,published-online,URL,type",
        )
        self.assertEqual(params["query.author"], "Ada")
        self.assertEqual(params["query.container-title"], "Journal of Testing")
        self.assertEqual(params["mailto"], "user@example.com")

    def test_fetch_work_uses_default_select_and_includes_agency(self) -> None:
        responses = {
            "https://api.crossref.org/works/10.1000%2Fxyz": {
                "message": {
                    "DOI": "10.1000/xyz",
                    "title": ["Example"],
                    "type": "journal-article",
                }
            },
            "https://api.crossref.org/works/10.1000%2Fxyz/agency": {
                "message": {"DOI": "10.1000/xyz", "agency": {"id": "crossref", "label": "Crossref"}}
            },
        }
        client = FakeHttpClient(responses)
        service = CrossrefService(config=self.config, client=client)

        payload = service.fetch_work("doi:10.1000/xyz", select=None, include_agency=True)

        self.assertEqual(payload["id"]["agency"], "crossref")
        self.assertEqual(client.calls[0][1], {"mailto": "user@example.com"})
        self.assertEqual(client.calls[1][1], {"mailto": "user@example.com"})
        self.assertEqual(
            payload["provenance"]["fieldsRequested"],
            ["DOI", "title", "author", "published-online", "URL", "type"],
        )

    def test_doi_record_supports_registration_and_resolution(self) -> None:
        responses = {
            "https://api.crossref.org/works/10.1000%2Fxyz/agency": {
                "message": {"DOI": "10.1000/xyz", "agency": {"id": "crossref", "label": "Crossref"}}
            }
        }
        client = FakeHttpClient(responses)
        service = CrossrefService(config=self.config, client=client)
        payload = service.doi_record(
            "10.1000/xyz", resolve_only=True, check_registration=True, include_redirects=True
        )
        self.assertTrue(payload["registration"]["registered"])
        self.assertEqual(payload["resolution"]["resolvedUrl"], "https://resolved.example/item")

    def test_doi_record_fetches_work_and_optional_resolution(self) -> None:
        responses = {
            "https://api.crossref.org/works/10.1000%2Fxyz": {
                "message": {
                    "DOI": "10.1000/xyz",
                    "title": ["Example"],
                    "type": "journal-article",
                }
            }
        }
        client = FakeHttpClient(responses)
        service = CrossrefService(config=self.config, client=client)

        payload = service.doi_record("10.1000/xyz", include_redirects=True, select="DOI,title")

        self.assertEqual(payload["work"]["title"], "Example")
        self.assertEqual(payload["resolution"]["requestedUrl"], "https://doi.org/10.1000/xyz")

    def test_resource_search_normalizes_members(self) -> None:
        responses = {
            "https://api.crossref.org/members": {
                "message": {
                    "items": [{"id": 98, "primary-name": "ACM"}],
                    "total-results": 1,
                    "items-per-page": 20,
                }
            }
        }
        service = CrossrefService(config=self.config, client=FakeHttpClient(responses))
        result = service.search_members(
            query="acm",
            filters=[],
            rows=20,
            offset=None,
            sample=None,
            sort=None,
            order=None,
            facets=[],
            max_results=None,
        )
        self.assertEqual(result["items"][0]["resource"], "member")
        self.assertEqual(result["items"][0]["id"], "98")

    def test_export_records_supports_bib_ris_and_csl_json(self) -> None:
        record = {
            "id": {"doi": "10.1000/xyz"},
            "title": "Example",
            "authors": [{"given": "Ada", "family": "Lovelace"}],
            "containerTitle": ["Journal"],
            "publishedDate": "2024-01-02",
            "type": "journal-article",
            "url": "https://doi.org/10.1000/xyz",
        }
        bib = export_records([record], "bib")
        ris = export_records([record], "ris")
        csl_json = export_records([record], "csl-json")
        self.assertIn("@article{10.1000_xyz", bib)
        self.assertIn("TY  - JOUR", ris)
        self.assertIn('"DOI": "10.1000/xyz"', csl_json)

    def test_export_works_respects_limit_and_max_rows(self) -> None:
        responses = {
            "https://api.crossref.org/works": {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1000/xyz",
                            "title": ["Example"],
                            "author": [{"given": "Ada", "family": "Lovelace"}],
                            "type": "journal-article",
                        }
                    ],
                    "total-results": 1,
                    "items-per-page": 1,
                }
            }
        }
        client = FakeHttpClient(responses)
        config = {
            **self.config,
            "works": {"default_rows": 20, "max_rows": 5},
        }
        service = CrossrefService(config=config, client=client)

        output = service.export_works(
            query="testing",
            filters=["type:journal-article"],
            select=None,
            limit=10,
            export_format="bib",
        )

        _, params = client.calls[0]
        assert params is not None
        self.assertEqual(params["rows"], 5)
        self.assertIn("@article{10.1000_xyz", output)

    def test_render_output_text_handles_resource_envelopes(self) -> None:
        payload = {"resource": "member", "title": "ACM", "id": "98", "data": {}}
        self.assertEqual(render_output(payload, "text"), "ACM\t98")

    @staticmethod
    def _paged_work_response(params: dict[str, Any] | None) -> dict[str, Any]:
        assert params is not None
        cursor = params.get("cursor")
        if cursor == "*":
            return {
                "message": {
                    "items": [{"DOI": "10.1000/1", "title": ["One"], "type": "journal-article"}],
                    "next-cursor": "cursor-2",
                    "total-results": 2,
                    "items-per-page": 1,
                }
            }
        if cursor == "cursor-2":
            return {
                "message": {
                    "items": [{"DOI": "10.1000/2", "title": ["Two"], "type": "journal-article"}],
                    "next-cursor": "cursor-2",
                    "total-results": 2,
                    "items-per-page": 1,
                }
            }
        raise AssertionError(f"Unexpected cursor: {cursor}")


if __name__ == "__main__":
    unittest.main()
