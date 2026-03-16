from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote

from .config import load_config
from .http import HttpClient

JsonDict = dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_doi(doi: str) -> str:
    normalized = doi.strip()
    normalized = normalized.removeprefix("doi:")
    normalized = normalized.removeprefix("https://doi.org/")
    normalized = normalized.removeprefix("http://doi.org/")
    normalized = normalized.removeprefix("https://dx.doi.org/")
    normalized = normalized.removeprefix("http://dx.doi.org/")
    return normalized.strip()


def _best_published_date(message: JsonDict) -> str | None:
    for field in ["published-online", "published-print", "issued", "published"]:
        date_parts = (message.get(field) or {}).get("date-parts") or []
        if date_parts and date_parts[0]:
            parts = [str(part) for part in date_parts[0]]
            if len(parts) == 1:
                return parts[0]
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1].zfill(2)}"
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
    return None


def _best_year(message: JsonDict) -> str | None:
    published = _best_published_date(message)
    if not published:
        return None
    return published.split("-", 1)[0]


def _select_fields(fields: str | None, default: str) -> str:
    raw = fields or default
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return ",".join(dict.fromkeys(items))


def _list_provenance(*, pool_used: str, fields_requested: str | None = None) -> JsonDict:
    provenance: JsonDict = {
        "retrievedAt": _now(),
        "poolUsed": pool_used,
    }
    if fields_requested is not None:
        provenance["fieldsRequested"] = [field for field in fields_requested.split(",") if field]
    return provenance


def _extract_resource_id(resource: str, message: JsonDict) -> str | None:
    if resource == "member":
        value = message.get("id")
        return str(value) if value is not None else None
    if resource == "funder":
        value = message.get("id") or message.get("uri")
        return str(value) if value is not None else None
    if resource == "journal":
        issn = message.get("ISSN")
        if isinstance(issn, list):
            return issn[0] if issn else None
        return issn
    if resource == "prefix":
        value = message.get("owner-prefix") or message.get("prefix")
        return str(value) if value is not None else None
    if resource == "type":
        value = message.get("id")
        return str(value) if value is not None else None
    if resource == "license":
        value = message.get("URL") or message.get("url") or message.get("id")
        return str(value) if value is not None else None
    value = message.get("id") or message.get("DOI")
    return str(value) if value is not None else None


def _extract_resource_title(resource: str, message: JsonDict) -> str | None:
    del resource
    for key in ["title", "primary-name", "name", "label"]:
        value = message.get(key)
        if isinstance(value, list):
            if value:
                return str(value[0])
        elif value:
            return str(value)
    return None


def normalize_resource(message: JsonDict, *, resource: str, pool_used: str) -> JsonDict:
    return {
        "backend": "crossref",
        "resource": resource,
        "id": _extract_resource_id(resource, message),
        "title": _extract_resource_title(resource, message),
        "data": message,
        "provenance": _list_provenance(pool_used=pool_used),
    }


def normalize_work(
    message: JsonDict,
    *,
    pool_used: str,
    fields_requested: str,
    agency: str | None = None,
) -> JsonDict:
    doi = message.get("DOI")
    licenses = [license_item.get("URL") for license_item in message.get("license") or [] if license_item.get("URL")]
    member_value = message.get("member")
    return {
        "backend": "crossref",
        "id": {
            "doi": doi,
            "shortDoi": None,
            "prefix": doi.split("/", 1)[0] if doi and "/" in doi else None,
            "agency": agency,
        },
        "title": (message.get("title") or [None])[0],
        "authors": [
            {
                "given": author.get("given"),
                "family": author.get("family"),
                "sequence": author.get("sequence"),
                "affiliation": [aff.get("name") for aff in author.get("affiliation") or [] if aff.get("name")],
                "orcid": author.get("ORCID"),
            }
            for author in message.get("author") or []
        ],
        "publishedDate": _best_published_date(message),
        "publishedPrint": message.get("published-print"),
        "publishedOnline": message.get("published-online"),
        "issued": message.get("issued"),
        "abstract": message.get("abstract"),
        "url": message.get("URL"),
        "containerTitle": message.get("container-title") or [],
        "type": message.get("type"),
        "subtype": message.get("subtype"),
        "publisher": message.get("publisher"),
        "language": message.get("language"),
        "isPostedContent": message.get("type") == "posted-content",
        "relation": message.get("relation"),
        "subject": message.get("subject") or [],
        "rights": {
            "license": licenses,
            "copyright": message.get("copyright"),
            "copyrightYear": message.get("published", {}).get("date-parts", [[None]])[0][0] if message.get("published") else None,
        },
        "referenceCount": message.get("reference-count"),
        "isReferencedByCount": message.get("is-referenced-by-count"),
        "references": message.get("reference"),
        "member": {
            "id": str(member_value) if member_value is not None else None,
            "name": None,
        },
        "deposited": {
            "date": (message.get("deposited") or {}).get("date-time"),
            "timestamp": (message.get("deposited") or {}).get("timestamp"),
        },
        "indexed": {
            "date": (message.get("indexed") or {}).get("date-time"),
            "timestamp": (message.get("indexed") or {}).get("timestamp"),
        },
        "provenance": _list_provenance(pool_used=pool_used, fields_requested=fields_requested),
    }


def _normalize_list_meta(message: JsonDict) -> JsonDict:
    return {
        "totalResults": message.get("total-results"),
        "itemsPerPage": message.get("items-per-page"),
        "nextCursor": message.get("next-cursor"),
        "query": message.get("query"),
        "facets": message.get("facets"),
    }


def _quote_path_value(value: str) -> str:
    return quote(value, safe="")


def _merge_filters(filters: list[str] | None) -> str | None:
    flattened = [item.strip() for item in (filters or []) if item and item.strip()]
    return ",".join(flattened) if flattened else None


def _merge_facets(facets: list[str] | None) -> str | None:
    flattened = [item.strip() for item in (facets or []) if item and item.strip()]
    return ",".join(flattened) if flattened else None


def _field_queries_to_params(field_queries: dict[str, str] | None) -> JsonDict:
    params: JsonDict = {}
    for key, value in (field_queries or {}).items():
        if value:
            params[f"query.{key}"] = value
    return params


def _work_entry_type(work: JsonDict) -> str:
    work_type = work.get("type")
    mapping = {
        "journal-article": "article",
        "book": "book",
        "book-chapter": "incollection",
        "proceedings-article": "inproceedings",
        "posted-content": "misc",
        "dissertation": "phdthesis",
        "report": "techreport",
    }
    if isinstance(work_type, str):
        return mapping.get(work_type, "misc")
    return "misc"


def _authors_text(work: JsonDict, *, separator: str = " and ") -> str:
    authors = []
    for author in work.get("authors") or []:
        given = (author.get("given") or "").strip()
        family = (author.get("family") or "").strip()
        full = " ".join(part for part in [given, family] if part)
        if full:
            authors.append(full)
    return separator.join(authors)


def _escape_bibtex(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _work_to_bibtex(work: JsonDict) -> str:
    key = (work.get("id") or {}).get("doi") or (work.get("title") or "untitled")
    key = key.replace("/", "_").replace(" ", "_")
    published_date = work.get("publishedDate")
    year = None
    if isinstance(published_date, str):
        year_text = published_date.split("-", 1)[0]
        if year_text.isdigit():
            year = year_text
    fields = [
        ("title", work.get("title")),
        ("author", _authors_text(work) or None),
        ("journal", (work.get("containerTitle") or [None])[0]),
        ("year", year),
        ("doi", (work.get("id") or {}).get("doi")),
        ("url", work.get("url")),
    ]
    lines = [f"@{_work_entry_type(work)}{{{key},"]
    for field, value in fields:
        if value:
            lines.append(f"  {field} = {{{_escape_bibtex(str(value))}}},")
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("}")
    return "\n".join(lines)


def _work_to_ris(work: JsonDict) -> str:
    work_type = work.get("type")
    type_map = {
        "journal-article": "JOUR",
        "book": "BOOK",
        "book-chapter": "CHAP",
        "proceedings-article": "CPAPER",
        "posted-content": "UNPB",
    }
    ty = type_map.get(work_type, "GEN") if isinstance(work_type, str) else "GEN"
    lines = [f"TY  - {ty}"]
    if work.get("title"):
        lines.append(f"TI  - {work['title']}")
    for author in work.get("authors") or []:
        name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
        if name:
            lines.append(f"AU  - {name}")
    container = (work.get("containerTitle") or [None])[0]
    if container:
        lines.append(f"JO  - {container}")
    if work.get("publishedDate"):
        lines.append(f"PY  - {work['publishedDate']}")
    if (work.get("id") or {}).get("doi"):
        lines.append(f"DO  - {work['id']['doi']}")
    if work.get("url"):
        lines.append(f"UR  - {work['url']}")
    lines.append("ER  -")
    return "\n".join(lines)


def _work_to_csl_json(work: JsonDict) -> JsonDict:
    issued = None
    if work.get("publishedDate"):
        parts = [int(part) for part in work["publishedDate"].split("-") if part.isdigit()]
        if parts:
            issued = {"date-parts": [parts]}
    item = {
        "id": (work.get("id") or {}).get("doi"),
        "DOI": (work.get("id") or {}).get("doi"),
        "type": work.get("type") or "article",
        "title": work.get("title"),
        "URL": work.get("url"),
        "container-title": (work.get("containerTitle") or [None])[0],
        "author": [
            {
                "given": author.get("given"),
                "family": author.get("family"),
            }
            for author in work.get("authors") or []
        ],
        "issued": issued,
    }
    return {key: value for key, value in item.items() if value is not None}


def export_records(records: list[JsonDict], export_format: str) -> str:
    if export_format == "bib":
        return "\n\n".join(_work_to_bibtex(record) for record in records)
    if export_format == "ris":
        return "\n\n".join(_work_to_ris(record) for record in records)
    if export_format == "csl-json":
        import json

        return json.dumps([_work_to_csl_json(record) for record in records], indent=2, ensure_ascii=True)
    raise ValueError(f"Unsupported export format: {export_format}")


class CrossrefService:
    def __init__(self, config: dict | None = None, client: HttpClient | None = None) -> None:
        self.config = config or load_config()
        pool = self.config["pool"]
        selected_pool = pool.get("default", "public")
        if selected_pool == "public" and pool.get("email"):
            selected_pool = "polite"
        headers = {"User-Agent": "crossref-tool/0.1.0"}
        if selected_pool == "polite" and pool.get("email"):
            headers["User-Agent"] = f"crossref-tool/0.1.0 (mailto:{pool['email']})"
        if selected_pool == "plus" and pool.get("api_key"):
            token = f"Bearer {pool['api_key']}"
            headers["Authorization"] = token
            headers["Crossref-Plus-API-Token"] = token
        self.pool_used = selected_pool
        self.client = client or HttpClient(headers=headers)
        self.base_url = self.config["api"]["base_url"].rstrip("/")
        self.mailto = pool.get("email") or None

    def _default_rows(self, rows: int | None) -> int:
        value = rows if rows is not None else self.config["works"]["default_rows"]
        if value < 0:
            raise ValueError("rows must be >= 0")
        if value > self.config["works"]["max_rows"]:
            raise ValueError(f"rows must be <= {self.config['works']['max_rows']}")
        return value

    def _prepare_params(
        self,
        *,
        query: str | None = None,
        filters: list[str] | None = None,
        select: str | None = None,
        rows: int | None = None,
        offset: int | None = None,
        sample: int | None = None,
        sort: str | None = None,
        order: str | None = None,
        facets: list[str] | None = None,
        cursor: str | None = None,
        field_queries: dict[str, str] | None = None,
    ) -> JsonDict:
        params: JsonDict = {
            "query": query or None,
            "filter": _merge_filters(filters),
            "select": select,
            "rows": self._default_rows(rows),
            "offset": offset,
            "sample": sample,
            "sort": sort,
            "order": order,
            "facet": _merge_facets(facets),
            "cursor": cursor,
        }
        params.update(_field_queries_to_params(field_queries))
        if self.mailto:
            params.setdefault("mailto", self.mailto)
        if cursor and offset is not None:
            raise ValueError("offset cannot be combined with cursor")
        if cursor and sample is not None:
            raise ValueError("sample cannot be combined with cursor")
        if sample is not None and sample < 1:
            raise ValueError("sample must be >= 1")
        if offset is not None and offset < 0:
            raise ValueError("offset must be >= 0")
        return params

    def _fetch_singleton(
        self,
        path: str,
        *,
        normalize: Callable[[JsonDict], JsonDict],
        params: JsonDict | None = None,
    ) -> JsonDict:
        payload = self.client.get_json(f"{self.base_url}{path}", params)
        return normalize(payload["message"])

    def _fetch_list(
        self,
        path: str,
        *,
        normalize_item: Callable[[JsonDict], JsonDict],
        query: str | None = None,
        filters: list[str] | None = None,
        select: str | None = None,
        rows: int | None = None,
        offset: int | None = None,
        sample: int | None = None,
        sort: str | None = None,
        order: str | None = None,
        facets: list[str] | None = None,
        cursor: str | None = None,
        max_results: int | None = None,
        field_queries: dict[str, str] | None = None,
        allow_cursor: bool = False,
    ) -> JsonDict:
        params = self._prepare_params(
            query=query,
            filters=filters,
            select=select,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            cursor=cursor,
            field_queries=field_queries,
        )
        if max_results is not None and max_results < 1:
            raise ValueError("max-results must be >= 1")
        if allow_cursor and params["cursor"] is None and max_results is not None and max_results > params["rows"]:
            params["cursor"] = "*"

        items: list[JsonDict] = []
        next_cursor = params.get("cursor")
        current_offset = params.get("offset") or 0
        meta: JsonDict = {}

        while True:
            payload = self.client.get_json(f"{self.base_url}{path}", params)["message"]
            meta = _normalize_list_meta(payload)
            batch = payload.get("items") or []
            for item in batch:
                items.append(normalize_item(item))
                if max_results is not None and len(items) >= max_results:
                    return {"items": items[:max_results], "meta": meta}

            if not batch:
                break
            if params.get("sample") is not None:
                break
            if params.get("cursor"):
                next_cursor = payload.get("next-cursor")
                if not next_cursor or next_cursor == params.get("cursor"):
                    break
                params["cursor"] = next_cursor
                continue
            if max_results is None:
                break
            if len(batch) < params["rows"]:
                break
            current_offset += params["rows"]
            params["offset"] = current_offset

        return {"items": items, "meta": meta}

    def fetch_work(self, doi: str, *, select: str | None, include_agency: bool = False) -> JsonDict:
        fields = _select_fields(select, self.config["output"]["default_select"])
        params = {"select": fields} if select else ({"mailto": self.mailto} if self.mailto else None)
        if params is not None and self.mailto and "mailto" not in params:
            params["mailto"] = self.mailto
        payload = self.client.get_json(f"{self.base_url}/works/{_quote_path_value(normalize_doi(doi))}", params)
        agency = None
        if include_agency:
            agency = self.fetch_work_agency(doi).get("agency")
        return normalize_work(payload["message"], pool_used=self.pool_used, fields_requested=fields, agency=agency)

    def fetch_work_agency(self, doi: str) -> JsonDict:
        params = {"mailto": self.mailto} if self.mailto else None
        payload = self.client.get_json(f"{self.base_url}/works/{_quote_path_value(normalize_doi(doi))}/agency", params)
        message = payload["message"]
        agency = (message.get("agency") or {}).get("id")
        return {
            "backend": "crossref",
            "resource": "agency",
            "doi": message.get("DOI"),
            "agency": agency,
            "label": (message.get("agency") or {}).get("label"),
            "registered": agency == "crossref",
            "provenance": _list_provenance(pool_used=self.pool_used),
        }

    def search_works(
        self,
        *,
        query: str | None,
        filters: list[str],
        select: str | None,
        rows: int | None,
        cursor: str | None,
        max_results: int | None,
        offset: int | None = None,
        sample: int | None = None,
        sort: str | None = None,
        order: str | None = None,
        facets: list[str] | None = None,
        field_queries: dict[str, str] | None = None,
    ) -> JsonDict:
        fields = _select_fields(select, self.config["output"]["default_select"])
        return self._fetch_list(
            "/works",
            normalize_item=lambda item: normalize_work(item, pool_used=self.pool_used, fields_requested=fields),
            query=query,
            filters=filters,
            select=fields,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            cursor=cursor,
            max_results=max_results,
            field_queries=field_queries,
            allow_cursor=True,
        )

    def member_works(self, *, member_id: str, filters: list[str], select: str | None, rows: int | None, cursor: str | None, max_results: int | None, offset: int | None = None, sample: int | None = None, sort: str | None = None, order: str | None = None, facets: list[str] | None = None, field_queries: dict[str, str] | None = None) -> JsonDict:
        fields = _select_fields(select, self.config["output"]["default_select"])
        return self._fetch_list(
            f"/members/{_quote_path_value(member_id)}/works",
            normalize_item=lambda item: normalize_work(item, pool_used=self.pool_used, fields_requested=fields),
            filters=filters,
            select=fields,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            cursor=cursor,
            max_results=max_results,
            field_queries=field_queries,
            allow_cursor=True,
        )

    def journal_works(self, *, issn: str, filters: list[str], select: str | None, rows: int | None, cursor: str | None, max_results: int | None, offset: int | None = None, sample: int | None = None, sort: str | None = None, order: str | None = None, facets: list[str] | None = None, field_queries: dict[str, str] | None = None) -> JsonDict:
        fields = _select_fields(select, self.config["output"]["default_select"])
        return self._fetch_list(
            f"/journals/{_quote_path_value(issn)}/works",
            normalize_item=lambda item: normalize_work(item, pool_used=self.pool_used, fields_requested=fields),
            filters=filters,
            select=fields,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            cursor=cursor,
            max_results=max_results,
            field_queries=field_queries,
            allow_cursor=True,
        )

    def funder_works(self, *, funder_id: str, filters: list[str], select: str | None, rows: int | None, cursor: str | None, max_results: int | None, offset: int | None = None, sample: int | None = None, sort: str | None = None, order: str | None = None, facets: list[str] | None = None, field_queries: dict[str, str] | None = None) -> JsonDict:
        fields = _select_fields(select, self.config["output"]["default_select"])
        return self._fetch_list(
            f"/funders/{_quote_path_value(funder_id)}/works",
            normalize_item=lambda item: normalize_work(item, pool_used=self.pool_used, fields_requested=fields),
            filters=filters,
            select=fields,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            cursor=cursor,
            max_results=max_results,
            field_queries=field_queries,
            allow_cursor=True,
        )

    def prefix_works(self, *, prefix: str, filters: list[str], select: str | None, rows: int | None, cursor: str | None, max_results: int | None, offset: int | None = None, sample: int | None = None, sort: str | None = None, order: str | None = None, facets: list[str] | None = None, field_queries: dict[str, str] | None = None) -> JsonDict:
        fields = _select_fields(select, self.config["output"]["default_select"])
        return self._fetch_list(
            f"/prefixes/{_quote_path_value(prefix)}/works",
            normalize_item=lambda item: normalize_work(item, pool_used=self.pool_used, fields_requested=fields),
            filters=filters,
            select=fields,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            cursor=cursor,
            max_results=max_results,
            field_queries=field_queries,
            allow_cursor=True,
        )

    def type_works(self, *, type_id: str, filters: list[str], select: str | None, rows: int | None, cursor: str | None, max_results: int | None, offset: int | None = None, sample: int | None = None, sort: str | None = None, order: str | None = None, facets: list[str] | None = None, field_queries: dict[str, str] | None = None) -> JsonDict:
        fields = _select_fields(select, self.config["output"]["default_select"])
        return self._fetch_list(
            f"/types/{_quote_path_value(type_id)}/works",
            normalize_item=lambda item: normalize_work(item, pool_used=self.pool_used, fields_requested=fields),
            filters=filters,
            select=fields,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            cursor=cursor,
            max_results=max_results,
            field_queries=field_queries,
            allow_cursor=True,
        )

    def search_members(self, *, query: str | None, filters: list[str], rows: int | None, offset: int | None, sample: int | None, sort: str | None, order: str | None, facets: list[str] | None, max_results: int | None) -> JsonDict:
        return self._fetch_list(
            "/members",
            normalize_item=lambda item: normalize_resource(item, resource="member", pool_used=self.pool_used),
            query=query,
            filters=filters,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            max_results=max_results,
        )

    def fetch_member(self, member_id: str) -> JsonDict:
        return self._fetch_singleton(
            f"/members/{_quote_path_value(member_id)}",
            normalize=lambda message: normalize_resource(message, resource="member", pool_used=self.pool_used),
            params={"mailto": self.mailto} if self.mailto else None,
        )

    def search_journals(self, *, query: str | None, filters: list[str], rows: int | None, offset: int | None, sample: int | None, sort: str | None, order: str | None, facets: list[str] | None, max_results: int | None) -> JsonDict:
        return self._fetch_list(
            "/journals",
            normalize_item=lambda item: normalize_resource(item, resource="journal", pool_used=self.pool_used),
            query=query,
            filters=filters,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            max_results=max_results,
        )

    def fetch_journal(self, issn: str) -> JsonDict:
        return self._fetch_singleton(
            f"/journals/{_quote_path_value(issn)}",
            normalize=lambda message: normalize_resource(message, resource="journal", pool_used=self.pool_used),
            params={"mailto": self.mailto} if self.mailto else None,
        )

    def search_funders(self, *, query: str | None, filters: list[str], rows: int | None, offset: int | None, sample: int | None, sort: str | None, order: str | None, facets: list[str] | None, max_results: int | None) -> JsonDict:
        return self._fetch_list(
            "/funders",
            normalize_item=lambda item: normalize_resource(item, resource="funder", pool_used=self.pool_used),
            query=query,
            filters=filters,
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            max_results=max_results,
        )

    def fetch_funder(self, funder_id: str) -> JsonDict:
        return self._fetch_singleton(
            f"/funders/{_quote_path_value(funder_id)}",
            normalize=lambda message: normalize_resource(message, resource="funder", pool_used=self.pool_used),
            params={"mailto": self.mailto} if self.mailto else None,
        )

    def list_prefixes(self, *, rows: int | None, offset: int | None, sample: int | None, sort: str | None, order: str | None, facets: list[str] | None, max_results: int | None) -> JsonDict:
        return self._fetch_list(
            "/prefixes",
            normalize_item=lambda item: normalize_resource(item, resource="prefix", pool_used=self.pool_used),
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            max_results=max_results,
        )

    def fetch_prefix(self, prefix: str) -> JsonDict:
        return self._fetch_singleton(
            f"/prefixes/{_quote_path_value(prefix)}",
            normalize=lambda message: normalize_resource(message, resource="prefix", pool_used=self.pool_used),
            params={"mailto": self.mailto} if self.mailto else None,
        )

    def list_types(self, *, rows: int | None, offset: int | None, sample: int | None, sort: str | None, order: str | None, facets: list[str] | None, max_results: int | None) -> JsonDict:
        return self._fetch_list(
            "/types",
            normalize_item=lambda item: normalize_resource(item, resource="type", pool_used=self.pool_used),
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            max_results=max_results,
        )

    def fetch_type(self, type_id: str) -> JsonDict:
        return self._fetch_singleton(
            f"/types/{_quote_path_value(type_id)}",
            normalize=lambda message: normalize_resource(message, resource="type", pool_used=self.pool_used),
            params={"mailto": self.mailto} if self.mailto else None,
        )

    def list_licenses(self, *, rows: int | None, offset: int | None, sample: int | None, sort: str | None, order: str | None, facets: list[str] | None, max_results: int | None) -> JsonDict:
        return self._fetch_list(
            "/licenses",
            normalize_item=lambda item: normalize_resource(item, resource="license", pool_used=self.pool_used),
            rows=rows,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            max_results=max_results,
        )

    def preprint_search(self, *, query: str | None, filters: list[str], select: str | None, rows: int | None, cursor: str | None, max_results: int | None, offset: int | None = None, sample: int | None = None, sort: str | None = None, order: str | None = None, facets: list[str] | None = None, relationship: str | None = None) -> JsonDict:
        merged_filters = [*filters]
        merged_filters.append("type:posted-content")
        if relationship:
            merged_filters.append(f"relation.type:{relationship}")
        return self.search_works(
            query=query,
            filters=merged_filters,
            select=select,
            rows=rows,
            cursor=cursor,
            max_results=max_results,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
        )

    def preprints_by_prefix(self, *, prefix: str, query: str | None, filters: list[str], select: str | None, rows: int | None, cursor: str | None, max_results: int | None, offset: int | None = None, sample: int | None = None, sort: str | None = None, order: str | None = None, facets: list[str] | None = None, relationship: str | None = None) -> JsonDict:
        merged_filters = [*filters, f"prefix:{prefix}"]
        return self.preprint_search(
            query=query,
            filters=merged_filters,
            select=select,
            rows=rows,
            cursor=cursor,
            max_results=max_results,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            relationship=relationship,
        )

    def preprints_by_date_range(self, *, from_date: str, until_date: str, query: str | None, filters: list[str], select: str | None, rows: int | None, cursor: str | None, max_results: int | None, offset: int | None = None, sample: int | None = None, sort: str | None = None, order: str | None = None, facets: list[str] | None = None, relationship: str | None = None) -> JsonDict:
        merged_filters = [*filters, f"from-posted-date:{from_date}", f"until-posted-date:{until_date}"]
        return self.preprint_search(
            query=query,
            filters=merged_filters,
            select=select,
            rows=rows,
            cursor=cursor,
            max_results=max_results,
            offset=offset,
            sample=sample,
            sort=sort,
            order=order,
            facets=facets,
            relationship=relationship,
        )

    def resolve_doi(self, doi: str, *, include_redirects: bool = False) -> JsonDict:
        url = f"https://doi.org/{normalize_doi(doi)}"
        resolved_url = self.client.resolve_url(url, follow_redirects=include_redirects)
        return {
            "backend": "crossref",
            "resource": "doi-resolution",
            "doi": normalize_doi(doi),
            "requestedUrl": url,
            "resolvedUrl": resolved_url,
            "followedRedirects": include_redirects,
            "provenance": _list_provenance(pool_used=self.pool_used),
        }

    def doi_record(self, doi: str, *, resolve_only: bool = False, include_redirects: bool = False, check_registration: bool = False, include_agency: bool = False, select: str | None = None) -> JsonDict:
        response: JsonDict = {
            "backend": "crossref",
            "resource": "doi",
            "doi": normalize_doi(doi),
            "provenance": _list_provenance(pool_used=self.pool_used),
        }
        if check_registration or include_agency:
            response["registration"] = self.fetch_work_agency(doi)
        if resolve_only:
            response["resolution"] = self.resolve_doi(doi, include_redirects=include_redirects)
            return response
        response["work"] = self.fetch_work(doi, select=select, include_agency=include_agency)
        if include_redirects:
            response["resolution"] = self.resolve_doi(doi, include_redirects=True)
        return response

    def export_works(self, *, query: str | None, filters: list[str], select: str | None, limit: int, export_format: str, sort: str | None = None, order: str | None = None) -> str:
        fields = _select_fields(select, self.config["output"]["default_select"])
        result = self.search_works(
            query=query,
            filters=filters,
            select=fields,
            rows=min(limit, self.config["works"]["max_rows"]),
            cursor=None,
            max_results=limit,
            sort=sort,
            order=order,
        )
        return export_records(result["items"], export_format)


def render_output(data: JsonDict | list[JsonDict], fmt: str) -> str:
    import json

    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=True)
    if fmt == "jsonl":
        if not isinstance(data, list):
            raise ValueError("jsonl output requires a list")
        return "\n".join(json.dumps(item, ensure_ascii=True) for item in data)
    if fmt == "text":
        if isinstance(data, list):
            return "\n".join(_render_text_item(item) for item in data)
        return _render_text_item(data)
    raise ValueError(f"Unsupported format: {fmt}")


def _render_text_item(item: JsonDict) -> str:
    if "resource" in item and "data" in item:
        title = item.get("title") or item.get("id") or item["resource"]
        return f"{title}\t{item.get('id') or ''}"
    if "work" in item and item.get("resource") == "doi":
        work = item.get("work")
        if work:
            return _render_text_item(work)
        resolution = item.get("resolution") or {}
        return f"{item.get('doi')}\t{resolution.get('resolvedUrl') or ''}"
    if item.get("resource") == "doi-resolution":
        return f"{item.get('doi')}\t{item.get('resolvedUrl') or ''}"
    if "id" in item and isinstance(item["id"], dict):
        title = item.get("title") or ""
        doi = item["id"].get("doi") or ""
        return f"{title}\t{doi}"
    if item.get("title"):
        return str(item["title"])
    if item.get("id"):
        return str(item["id"])
    return str(item)
