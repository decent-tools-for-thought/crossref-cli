from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .config import load_config, reset_config, save_config
from .core import CrossrefService, render_output


def _add_query_controls(
    parser: argparse.ArgumentParser, *, include_query: bool = True, include_select: bool = True
) -> None:
    if include_query:
        parser.add_argument("query", nargs="?")
    parser.add_argument("--filter", action="append", default=[])
    parser.add_argument("--facet", action="append", default=[])
    parser.add_argument("--rows", type=int)
    parser.add_argument("--offset", type=int)
    parser.add_argument("--sample", type=int)
    parser.add_argument("--cursor")
    parser.add_argument("--max-results", type=int)
    parser.add_argument("--sort")
    parser.add_argument("--order", choices=["asc", "desc"])
    if include_select:
        parser.add_argument("--select")
    parser.add_argument("--format", choices=["jsonl", "json", "text"])


def _add_work_field_queries(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query-author")
    parser.add_argument("--query-editor")
    parser.add_argument("--query-chair")
    parser.add_argument("--query-translator")
    parser.add_argument("--query-contributor")
    parser.add_argument("--query-affiliation")
    parser.add_argument("--query-bibliographic")
    parser.add_argument("--query-container-title")


def _work_field_query_args(args: argparse.Namespace) -> dict[str, str]:
    mapping = {
        "author": args.query_author,
        "editor": args.query_editor,
        "chair": args.query_chair,
        "translator": args.query_translator,
        "contributor": args.query_contributor,
        "affiliation": args.query_affiliation,
        "bibliographic": args.query_bibliographic,
        "container-title": args.query_container_title,
    }
    return {key: value for key, value in mapping.items() if value}


def _configure_work_list_parser(parser: argparse.ArgumentParser) -> None:
    _add_query_controls(parser)
    _add_work_field_queries(parser)


def _configure_resource_list_parser(
    parser: argparse.ArgumentParser, *, include_query: bool = True
) -> None:
    _add_query_controls(parser, include_query=include_query, include_select=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crossref")
    subparsers = parser.add_subparsers(dest="command")

    works = subparsers.add_parser("works")
    works_sub = works.add_subparsers(dest="works_command")
    works_search = works_sub.add_parser("search")
    _configure_work_list_parser(works_search)
    works_fetch = works_sub.add_parser("fetch")
    works_fetch.add_argument("doi")
    works_fetch.add_argument("--select")
    works_fetch.add_argument("--include-agency", action="store_true")
    works_fetch.add_argument("--format", choices=["json", "text"])

    preprints = subparsers.add_parser("preprints")
    preprints_sub = preprints.add_subparsers(dest="preprints_command")
    preprints_search = preprints_sub.add_parser("search")
    _configure_work_list_parser(preprints_search)
    preprints_search.add_argument("--relationship")
    preprints_prefix = preprints_sub.add_parser("by-prefix")
    preprints_prefix.add_argument("prefix")
    _configure_work_list_parser(preprints_prefix)
    preprints_prefix.add_argument("--relationship")
    preprints_range = preprints_sub.add_parser("by-date-range")
    preprints_range.add_argument("from_date")
    preprints_range.add_argument("until_date")
    _configure_work_list_parser(preprints_range)
    preprints_range.add_argument("--relationship")

    members = subparsers.add_parser("members")
    members_sub = members.add_subparsers(dest="members_command")
    members_search = members_sub.add_parser("search")
    _configure_resource_list_parser(members_search)
    members_fetch = members_sub.add_parser("fetch")
    members_fetch.add_argument("member_id")
    members_fetch.add_argument("--format", choices=["json", "text"])
    members_works = members_sub.add_parser("works")
    members_works.add_argument("member_id")
    _configure_work_list_parser(members_works)

    journals = subparsers.add_parser("journals")
    journals_sub = journals.add_subparsers(dest="journals_command")
    journals_search = journals_sub.add_parser("search")
    _configure_resource_list_parser(journals_search)
    journals_fetch = journals_sub.add_parser("fetch")
    journals_fetch.add_argument("issn")
    journals_fetch.add_argument("--format", choices=["json", "text"])
    journals_works = journals_sub.add_parser("works")
    journals_works.add_argument("issn")
    _configure_work_list_parser(journals_works)

    funders = subparsers.add_parser("funders")
    funders_sub = funders.add_subparsers(dest="funders_command")
    funders_search = funders_sub.add_parser("search")
    _configure_resource_list_parser(funders_search)
    funders_fetch = funders_sub.add_parser("fetch")
    funders_fetch.add_argument("funder_id")
    funders_fetch.add_argument("--format", choices=["json", "text"])
    funders_works = funders_sub.add_parser("works")
    funders_works.add_argument("funder_id")
    _configure_work_list_parser(funders_works)

    prefixes = subparsers.add_parser("prefixes")
    prefixes_sub = prefixes.add_subparsers(dest="prefixes_command")
    prefixes_list = prefixes_sub.add_parser("list")
    _configure_resource_list_parser(prefixes_list, include_query=False)
    prefixes_fetch = prefixes_sub.add_parser("fetch")
    prefixes_fetch.add_argument("prefix")
    prefixes_fetch.add_argument("--format", choices=["json", "text"])
    prefixes_works = prefixes_sub.add_parser("works")
    prefixes_works.add_argument("prefix")
    _configure_work_list_parser(prefixes_works)

    types = subparsers.add_parser("types")
    types_sub = types.add_subparsers(dest="types_command")
    types_list = types_sub.add_parser("list")
    _configure_resource_list_parser(types_list, include_query=False)
    types_fetch = types_sub.add_parser("fetch")
    types_fetch.add_argument("type_id")
    types_fetch.add_argument("--format", choices=["json", "text"])
    types_works = types_sub.add_parser("works")
    types_works.add_argument("type_id")
    _configure_work_list_parser(types_works)

    licenses = subparsers.add_parser("licenses")
    licenses_sub = licenses.add_subparsers(dest="licenses_command")
    licenses_list = licenses_sub.add_parser("list")
    _configure_resource_list_parser(licenses_list, include_query=False)

    doi = subparsers.add_parser("doi")
    doi.add_argument("doi")
    doi.add_argument("--resolve-only", action="store_true")
    doi.add_argument("--include-redirects", action="store_true")
    doi.add_argument("--check-registration", action="store_true")
    doi.add_argument("--include-agency", action="store_true")
    doi.add_argument("--select")
    doi.add_argument("--format", choices=["json", "text"])

    fmt = subparsers.add_parser("format")
    fmt_sub = fmt.add_subparsers(dest="format_command")
    export = fmt_sub.add_parser("export")
    export.add_argument("query", nargs="?")
    export.add_argument("--filter", action="append", default=[])
    export.add_argument("--select")
    export.add_argument("--sort")
    export.add_argument("--order", choices=["asc", "desc"])
    export.add_argument("--limit", type=int, default=20)
    export.add_argument(
        "--format", dest="export_format", choices=["bib", "ris", "csl-json"], required=True
    )

    config = subparsers.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command")
    config_sub.add_parser("show")
    config_sub.add_parser("reset")
    config_set = config_sub.add_parser("set")
    config_set.add_argument(
        "field",
        choices=[
            "email",
            "pool",
            "api-key",
            "default-rows",
            "max-rows",
            "default-format",
            "default-select",
        ],
    )
    config_set.add_argument("value")
    return parser


def _resolve_output_format(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(getattr(args, "format", None) or config["output"]["default_format"])


def _render_list_result(result: dict[str, Any], output_format: str) -> str:
    payload: Any = result if output_format == "json" else result["items"]
    return render_output(payload, output_format)


def _update_config(config: dict[str, Any], field: str, value: str) -> dict[str, Any]:
    if field == "api-key":
        config["pool"]["api_key"] = value
    elif field == "email":
        config["pool"]["email"] = value
    elif field == "pool":
        if value not in {"public", "polite", "plus"}:
            raise ValueError("pool must be one of: public, polite, plus")
        config["pool"]["default"] = value
    elif field == "default-rows":
        config["works"]["default_rows"] = int(value)
    elif field == "max-rows":
        config["works"]["max_rows"] = int(value)
    elif field == "default-format":
        if value not in {"json", "jsonl", "text"}:
            raise ValueError("default-format must be one of: json, jsonl, text")
        config["output"]["default_format"] = value
    elif field == "default-select":
        config["output"]["default_select"] = value
    else:
        raise ValueError(f"Unsupported config field: {field}")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    help_attr_by_command = {
        "works": "works_command",
        "preprints": "preprints_command",
        "members": "members_command",
        "journals": "journals_command",
        "funders": "funders_command",
        "prefixes": "prefixes_command",
        "types": "types_command",
        "licenses": "licenses_command",
        "format": "format_command",
        "config": "config_command",
    }
    help_attr = help_attr_by_command.get(args.command)
    if help_attr and getattr(args, help_attr) is None:
        next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ).choices[args.command].print_help()
        return 0
    config = load_config()

    try:
        if args.command == "config":
            if args.config_command == "show":
                print(json.dumps(config, indent=2, ensure_ascii=True))
                return 0
            if args.config_command == "reset":
                print(json.dumps(reset_config(), indent=2, ensure_ascii=True))
                return 0
            save_config(_update_config(config, args.field, args.value))
            print(json.dumps(config, indent=2, ensure_ascii=True))
            return 0

        service = CrossrefService(config=config)
        output_format = _resolve_output_format(args, config)

        if args.command == "works":
            if args.works_command == "search":
                result = service.search_works(
                    query=args.query,
                    filters=args.filter,
                    select=args.select,
                    rows=args.rows,
                    cursor=args.cursor,
                    max_results=args.max_results,
                    offset=args.offset,
                    sample=args.sample,
                    sort=args.sort,
                    order=args.order,
                    facets=args.facet,
                    field_queries=_work_field_query_args(args),
                )
                print(_render_list_result(result, output_format))
                return 0
            payload = service.fetch_work(
                args.doi, select=args.select, include_agency=args.include_agency
            )
            print(render_output(payload, output_format))
            return 0

        if args.command == "preprints":
            common = {
                "query": args.query,
                "filters": args.filter,
                "select": args.select,
                "rows": args.rows,
                "cursor": args.cursor,
                "max_results": args.max_results,
                "offset": args.offset,
                "sample": args.sample,
                "sort": args.sort,
                "order": args.order,
                "facets": args.facet,
                "relationship": args.relationship,
            }
            if args.preprints_command == "search":
                result = service.preprint_search(**common)
            elif args.preprints_command == "by-prefix":
                result = service.preprints_by_prefix(prefix=args.prefix, **common)
            else:
                result = service.preprints_by_date_range(
                    from_date=args.from_date, until_date=args.until_date, **common
                )
            print(_render_list_result(result, output_format))
            return 0

        if args.command == "members":
            if args.members_command == "search":
                result = service.search_members(
                    query=args.query,
                    filters=args.filter,
                    rows=args.rows,
                    offset=args.offset,
                    sample=args.sample,
                    sort=args.sort,
                    order=args.order,
                    facets=args.facet,
                    max_results=args.max_results,
                )
                print(_render_list_result(result, output_format))
                return 0
            if args.members_command == "fetch":
                print(render_output(service.fetch_member(args.member_id), output_format))
                return 0
            result = service.member_works(
                member_id=args.member_id,
                filters=args.filter,
                select=args.select,
                rows=args.rows,
                cursor=args.cursor,
                max_results=args.max_results,
                offset=args.offset,
                sample=args.sample,
                sort=args.sort,
                order=args.order,
                facets=args.facet,
                field_queries=_work_field_query_args(args),
            )
            print(_render_list_result(result, output_format))
            return 0

        if args.command == "journals":
            if args.journals_command == "search":
                result = service.search_journals(
                    query=args.query,
                    filters=args.filter,
                    rows=args.rows,
                    offset=args.offset,
                    sample=args.sample,
                    sort=args.sort,
                    order=args.order,
                    facets=args.facet,
                    max_results=args.max_results,
                )
                print(_render_list_result(result, output_format))
                return 0
            if args.journals_command == "fetch":
                print(render_output(service.fetch_journal(args.issn), output_format))
                return 0
            result = service.journal_works(
                issn=args.issn,
                filters=args.filter,
                select=args.select,
                rows=args.rows,
                cursor=args.cursor,
                max_results=args.max_results,
                offset=args.offset,
                sample=args.sample,
                sort=args.sort,
                order=args.order,
                facets=args.facet,
                field_queries=_work_field_query_args(args),
            )
            print(_render_list_result(result, output_format))
            return 0

        if args.command == "funders":
            if args.funders_command == "search":
                result = service.search_funders(
                    query=args.query,
                    filters=args.filter,
                    rows=args.rows,
                    offset=args.offset,
                    sample=args.sample,
                    sort=args.sort,
                    order=args.order,
                    facets=args.facet,
                    max_results=args.max_results,
                )
                print(_render_list_result(result, output_format))
                return 0
            if args.funders_command == "fetch":
                print(render_output(service.fetch_funder(args.funder_id), output_format))
                return 0
            result = service.funder_works(
                funder_id=args.funder_id,
                filters=args.filter,
                select=args.select,
                rows=args.rows,
                cursor=args.cursor,
                max_results=args.max_results,
                offset=args.offset,
                sample=args.sample,
                sort=args.sort,
                order=args.order,
                facets=args.facet,
                field_queries=_work_field_query_args(args),
            )
            print(_render_list_result(result, output_format))
            return 0

        if args.command == "prefixes":
            if args.prefixes_command == "list":
                result = service.list_prefixes(
                    rows=args.rows,
                    offset=args.offset,
                    sample=args.sample,
                    sort=args.sort,
                    order=args.order,
                    facets=args.facet,
                    max_results=args.max_results,
                )
                print(_render_list_result(result, output_format))
                return 0
            if args.prefixes_command == "fetch":
                print(render_output(service.fetch_prefix(args.prefix), output_format))
                return 0
            result = service.prefix_works(
                prefix=args.prefix,
                filters=args.filter,
                select=args.select,
                rows=args.rows,
                cursor=args.cursor,
                max_results=args.max_results,
                offset=args.offset,
                sample=args.sample,
                sort=args.sort,
                order=args.order,
                facets=args.facet,
                field_queries=_work_field_query_args(args),
            )
            print(_render_list_result(result, output_format))
            return 0

        if args.command == "types":
            if args.types_command == "list":
                result = service.list_types(
                    rows=args.rows,
                    offset=args.offset,
                    sample=args.sample,
                    sort=args.sort,
                    order=args.order,
                    facets=args.facet,
                    max_results=args.max_results,
                )
                print(_render_list_result(result, output_format))
                return 0
            if args.types_command == "fetch":
                print(render_output(service.fetch_type(args.type_id), output_format))
                return 0
            result = service.type_works(
                type_id=args.type_id,
                filters=args.filter,
                select=args.select,
                rows=args.rows,
                cursor=args.cursor,
                max_results=args.max_results,
                offset=args.offset,
                sample=args.sample,
                sort=args.sort,
                order=args.order,
                facets=args.facet,
                field_queries=_work_field_query_args(args),
            )
            print(_render_list_result(result, output_format))
            return 0

        if args.command == "licenses":
            result = service.list_licenses(
                rows=args.rows,
                offset=args.offset,
                sample=args.sample,
                sort=args.sort,
                order=args.order,
                facets=args.facet,
                max_results=args.max_results,
            )
            print(_render_list_result(result, output_format))
            return 0

        if args.command == "doi":
            payload = service.doi_record(
                args.doi,
                resolve_only=args.resolve_only,
                include_redirects=args.include_redirects,
                check_registration=args.check_registration,
                include_agency=args.include_agency,
                select=args.select,
            )
            print(render_output(payload, output_format))
            return 0

        if args.command == "format":
            print(
                service.export_works(
                    query=args.query,
                    filters=args.filter,
                    select=args.select,
                    limit=args.limit,
                    export_format=args.export_format,
                    sort=args.sort,
                    order=args.order,
                )
            )
            return 0

        parser.error(f"Unsupported command: {args.command}")
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 0
