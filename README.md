# crossref-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/crossref-cli?sort=semver)](https://github.com/decent-tools-for-thought/crossref-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

DOI-centric command-line client for the Crossref REST API.

> [!IMPORTANT]
> This codebase is fully AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Why This Exists

- Search scholarly metadata with Crossref’s strong filter model.
- Resolve DOIs, inspect members and journals, and export citations.
- Keep common publisher and metadata workflows scriptable.

## Install

```bash
uv tool install .
crossref --help
```

For local development:

```bash
uv sync
uv run crossref --help
```

## Quick Start

Search works:

```bash
crossref works search "machine learning interpretability" \
  --filter "from-pub-date:2023-01-01,until-pub-date:2023-12-31" \
  --filter "type:journal-article" \
  --rows 20
```

Fetch a DOI:

```bash
crossref works fetch doi:10.1145/1234567.1234568 --format json
```

Look up publishers and their works:

```bash
crossref members search "Springer Nature"
crossref members works 297 --rows 20
```

Export citations:

```bash
crossref format export \
  --filter "type:journal-article" \
  --format bib \
  --limit 20
```

## Configuration

Using the polite pool is recommended:

```bash
crossref config set email your-email@example.com
crossref config set pool polite
crossref config show
```

## Development

```bash
uv run ruff check src tests
uv run mypy
```

## Credits

This client is built on Crossref’s REST API and metadata infrastructure. Credit goes to Crossref and its member community for the DOI registry data and API documentation this tool depends on.
