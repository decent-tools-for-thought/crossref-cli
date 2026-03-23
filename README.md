<div align="center">

# crossref-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/crossref-cli?sort=semver&color=facc15)](https://github.com/decent-tools-for-thought/crossref-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-eab308)
![License](https://img.shields.io/badge/license-MIT-ca8a04)

DOI-first command-line client for searching, filtering, resolving, and exporting Crossref metadata from the shell.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
$$\color{#EAB308}Tool \space \color{#CA8A04}Map$$
- [Install](#install)
- [Functionality](#functionality)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install

```bash
uv tool install .
crossref --help
```

## Functionality
$$\color{#EAB308}Core \space \color{#CA8A04}Features$$

### Works
- `crossref works search`: search works with free-text queries, Crossref filters, facets, sorting, pagination, sampling, cursor-based traversal, field selection, and `json`/`jsonl`/`text` output.
- `crossref works search`: narrow work queries with dedicated fielded lookups such as `--query-author`, `--query-editor`, `--query-affiliation`, `--query-bibliographic`, and `--query-container-title`.
- `crossref works fetch`: fetch one DOI, optionally select fields, include registration-agency metadata, and render as `json` or `text`.

### Preprints
- `crossref preprints search`: search preprint records with the same filtering, paging, field-query, and formatting controls as `works search`.
- `crossref preprints search`: filter by relationship metadata with `--relationship`.
- `crossref preprints by-prefix`: browse preprints for one DOI prefix.
- `crossref preprints by-date-range`: browse preprints within an explicit publication-date range.

### Registry Resources
- `crossref members search`: search Crossref members with filters, facets, paging controls, and `json`/`jsonl`/`text` output.
- `crossref members fetch`: fetch one member record.
- `crossref members works`: list works for one member.
- `crossref journals search`: search journals by metadata.
- `crossref journals fetch`: fetch one journal by ISSN.
- `crossref journals works`: list works for one journal.
- `crossref funders search`: search funders by metadata.
- `crossref funders fetch`: fetch one funder record.
- `crossref funders works`: list works for one funder.
- `crossref prefixes list`: list prefixes with filter and paging controls.
- `crossref prefixes fetch`: fetch one prefix record.
- `crossref prefixes works`: list works for one prefix.
- `crossref types list`: list Crossref work types.
- `crossref types fetch`: fetch one work type definition.
- `crossref types works`: list works for one work type.
- `crossref licenses list`: list known Crossref licenses with filter and paging controls.

### DOI Resolution And Export
- `crossref doi`: resolve a DOI, optionally return only the resolved target, include redirect data, check registration, include agency data, select fields, and render as `json` or `text`.
- `crossref format export`: run a filtered work query and export results as `bib`, `ris`, or `csl-json`.

### Configuration
- `crossref config show`: print the saved config.
- `crossref config reset`: restore defaults.
- `crossref config set email`: save the polite-pool email address.
- `crossref config set pool`: switch between `public`, `polite`, and `plus`.
- `crossref config set api-key`: save a Plus API key.
- `crossref config set default-rows`, `max-rows`, `default-format`, `default-select`: tune default query and output behavior.

## Configuration
$$\color{#EAB308}User \space \color{#CA8A04}Config$$

Using the polite pool is recommended:

```bash
crossref config set email your-email@example.com
crossref config set pool polite
crossref config show
```

## Quick Start
$$\color{#EAB308}Quick \space \color{#CA8A04}Start$$

```bash
crossref works search "machine learning interpretability" \
  --filter "from-pub-date:2023-01-01,until-pub-date:2023-12-31" \
  --filter "type:journal-article" \
  --rows 20

crossref works fetch doi:10.1145/1234567.1234568 --format json

crossref members search "Springer Nature"
crossref members works 297 --rows 20

crossref format export \
  --filter "type:journal-article" \
  --format bib \
  --limit 20
```

## Credits
$$\color{#EAB308}Project \space \color{#CA8A04}Credits$$

This client is built for Crossref's REST API and is not affiliated with Crossref.

Credit goes to Crossref and its member community for the DOI registry data, metadata model, and API documentation this tool depends on.
