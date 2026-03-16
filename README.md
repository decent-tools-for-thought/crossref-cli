# Crossref Tool - DOI Registry and Metadata CLI

A specialized command-line tool for the Crossref REST API, designed for DOI-centric workflows, metadata normalization, and filter-heavy retrieval across the global scholarly corpus.

## Quick Start

### Installation
```bash
pip install crossref-tool
# or
makepkg -si
```

For a local pacman package build on Arch Linux:

```bash
makepkg -si
pacman -Ql crossref-tool
```

### Basic Usage

#### Search works by filters
```bash
# Search by date range and title keyword
crossref works search "machine learning interpretability" \
  --filter "from-pub-date:2023-01-01,until-pub-date:2023-12-31" \
  --filter "type:journal-article" \
  --select DOI,title,author,published-online,abstract \
  --rows 100 \
  --format jsonl

# Search by publisher (prefix)
crossref works search "transformer models" \
  --prefix "10.1109"  # IEEE prefix \
  --filter "has-abstract:true" \
  --rows 50
```

#### Fetch work by DOI
```bash
crossref works fetch doi:10.1145/1234567.1234568 \
  --select DOI,title,author,published-online,abstract,URL \
  --format json
```

#### Preprint search (posted content)
```bash
crossref preprints search "large language models" \
  --type posted-content \
  --from-pub-date 2024-01-01 \
  --rows 50
```

#### Search by publisher/member
```bash
crossref members search "Springer Nature"

crossref members works 297  \
  --filter "from-pub-date:2024-01-01" \
  --rows 100
```

#### DOI resolution
```bash
crossref doi doi:10.1145/1234567.1234568

crossref doi doi:10.1145/1234567.1234568 --resolve-only
```

#### Export metadata
```bash
crossref format export \
  --filter "from-pub-date:2023-01-01,until-pub-date:2023-12-31" \
  --filter "type:journal-article" \
  --filter "has-abstract:true" \
  --format bib \
  --limit 50
```

## What Makes This Tool Special

1. **DOI Authority:** Authentic metadata from the DOI registration authority

2. **Filter-Heavy Query Model:** Structured metadata filters for precise discovery

3. **Three-Tier Rate System:** Public (5/1), Polite (10/3), Plus (150/unlimited)

4. **Global Coverage:** Comprehensive publisher/journal coverage across disciplines

5. **Posted Content Model:** Explicit preprint typing and relationship handling

## Key Commands

### Work Discovery
- `crossref works search <query>` - Search works with filters and field selection
- `crossref works fetch <doi>` - Retrieve work by DOI
- `crossref works similar <doi>` - Related works (future)

### Preprints
- `crossref preprints search <query>` - Search posted content with preprint filters
- `crossref preprints by-prefix <prefix>` - Search by DOI prefix publisher

### Publisher/Journal Metadata
- `crossref members search <name>` - Search members/publishers
- `crossref members works <id>` - Get works by member
- `crossref journals fetch <issn>` - Retrieve journal details

### DOI Operations
- `crossref doi <doi>` - Resolve DOI or fetch metadata
- `crossref doi <doi> --check-registration` - Verify DOI registration

### Export and Format
- `crossref format export <query>` - Export to BibTeX, RIS, CSL-JSON

### Configuration
- `crossref config set email <address>` - Set email for polite pool
- `crossref config show` - Display current configuration

## Output Format

### Search Results (JSONL)
```jsonl
{"backend":"crossref","id":{"doi":"10.1145/1234567.1234568","shortDoi":"10/1234567","prefix":"10.1145","agency":"Crossref"},"title":"A novel approach to machine learning","authors":[{"given":"John","family":"Smith","sequence":"first","affiliation":["Department of CS","University"],...}],"publishedDate":"2023-05-15","abstract":"This paper presents...","url":"https://api.crossref.org/works/10.1145/1234567.1234568","type":"journal-article","isPostedContent":false,"rights":{"license":["http://creativecommons.org/licenses/by/4.0"],"copyright":"© 2023 John Smith","copyrightYear":2023},"referenceCount":45,"member":{"id":"320","name":"Association for Computing Machinery (ACM)"},"deposited":{"date":"2023-05-16T02:34:56Z","timestamp":1684220096000},"indexed":{"date":"2023-05-16T06:12:34Z","timestamp":1684231954000},"provenance":{"retrievedAt":"2026-03-16T18:30:00Z","poolUsed":"polite","fieldsRequested":["DOI","title","author","published-online","abstract","URL"]}}
```

### Full Record (JSON)
```json
{
  "backend": "crossref",
  "id": {"doi": "10.1145/1234567.1234568", "prefix": "10.1145"},
  "title": "A novel approach to machine learning",
  "authors": [{"given": "John", "family": "Smith", ...}],
  "publishedDate": "2023-05-15",
  "abstract": "Full abstract text here...",
  "type": "journal-article",
  "isPostedContent": false,
  "rights": {"license": ["http://creativecommons.org/licenses/by/4.0"]},
  "referenceCount": 45,
  "member": {"id": "320", "name": "Association for Computing Machinery (ACM)"},
  "provenance": {"retrievedAt": "...", "poolUsed": "polite"}
}
```

## Configuration

### Global Config (`~/.config/crossref-tool/config.toml`)
```toml
[api]
base_url = "https://api.crossref.org"

[pool]
default = "polite"  # Recommended default
email = "user@example.com"
api_key = ""

[cache]
enabled = true
ttl_seconds = 3600

[works]
default_rows = 20
max_rows = 100
```

### Set Contact Email (Recommended for Polite Pool)
```bash
crossref config set email your-email@example.com
```

### Configure API Pool
```bash
crossref config set pool polite  # Recommended
# or
crossref config set pool public  # Lower rate, no email needed
# or
crossref config set pool plus    # Premium, requires paid key
```

## Rate Limiting - Three-Tier System

### 1. Public Pool (No Identification)
- **Rate:** 5 requests/second
- **Concurrency:** 1 connection
- **Headers:** None required
- **Use:** Testing, occasional queries, when email not configured
- **Behavior:** First to be throttled under heavy load

### 2. Polite Pool (**Recommended Default**)
- **Rate:** 10 requests/second
- **Concurrency:** 3 connections
- **Headers:** `User-Agent: crossref-tool/1.0 (mailto:user@example.com)`
- **Use:** Production workflows, regular usage
- **Behavior:** Significantly less prone to throttling
- **Enable:** Configure email in config

### 3. Metadata Plus (Paid)
- **Rate:** 150 requests/second
- **Concurrency:** No stated limit
- **Headers:** `Authorization: Bearer <key>`
- **Use:** High-volume enterprise users
- **Behavior:** Premium tier for large-scale operations

### Rate Limit Detection
- HTTP 429 when rate exceeded
- HTTP 403 for abuse/violation
- Response times increase as quotas approach (early warning)
- Automatic backoff before hitting hard limits

 IMPORTANT: Polite Pool is Not Just Etiquette

Crossref's documentation is explicit: using the polite pool **materially increases throughput** and **reduces block risk**. The 10 req/sec vs 5 req/sec difference is meaningful, and the concurrency limit (3 vs 1) is even more impactful. The CLI defaults to polite pool and warns public pool use in production contexts.

## Query Model: Filters vs Search

### Queries (Free Text)
```bash
crossref works search "transformer models in NLP"
```
- Simple keyword search
- Matches title, author fields
- Limited specificity

### Filters (Structured Metadata)
```bash
crossref works search "transformer models" \
  --filter "from-pub-date:2023-01-01,until-pub-date:2023-12-31" \
  --filter "type:journal-article" \
  --filter "has-abstract:true" \
  --filter "reference-count:10,100"
```
- Precise metadata filtering
- Multiple filters combined (AND logic)
- Recommended for production workflows

### Field Selection (Critical for Performance)
```bash
crossref works search "machine learning" \
  --select DOI,title,author,published-online,abstract,URL
```
- Minimizes payload size
- Required for efficient large queries
- Default selection covers most use cases

## Posted Content (Preprint) Model

### Preprint Typing
```bash
crossref preprints search "large language models" \
  --type posted-content \
  --from-pub-date 2024-01-01
```
- Crossref has a posted content type for preprints
- Requires correct preprint typing and relationship handling
- Relationship types: `is-preprint-of`, `has-preprint`

### Publisher-Specific Preprints
```bash
crossref preprints by-prefix "10.1101"
```Thinm
- Search by DOI prefix (bioRxiv uses 10.1101)
- Target specific preprint servers

## Limitations to Know

1. **Not Deep Abstract Search:** Abstracts missing in many records; Crossref is a metadata registry, not a full-text search engine
2. **Abstract Copyright Warnings:** Some abstracts are subject to copyright by publishers/authors
3. **Deposit Quality Varies:** Incomplete metadata is common across the corpus
4. **Not Semantic/Europe PMC-Like:** No deep keyword search with field operators like `TITLE:` or `ABSTRACT:`
5. **Response Time Growth:** Response times increase as rate limits approach (politeness indication)

## When to Use This Tool

Use Crossref Tool when:
- You need **DOI resolution** and authoritative DOI metadata
- Your queries are **filter-heavy** (dates, types, publishers, funders)
- You're building workflows for **DOI-centric operations** (registration, agency lookup)
- You need **publisher/journal metadata** and member relationships
- You're implementing **preprint workflows** via posted content model

## When to Use Other Tools

- **PMC Tool:** For PubMed-like fielded search, preprint-specific discovery with `SRC:PPR`
- **Semantic Scholar Tool:** For citation graph traversal, bulk search, author disambiguation

## Project Structure

```
crossref-tool/
├── PROJECT_OUTLINE.md       # Comprehensive design document
├── README.md                # This file
├── src/                     # Implementation (future)
├── tests/                   # Test suite
└── config/                  # Configuration templates
```

## Documentation

- [PROJECT_OUTLINE.md](PROJECT_OUTLINE.md) - Detailed design document with command reference
- [OVERVIEW.md](../OVERVIEW.md) - Multi-tool architecture overview
- [Crossref REST API Documentation](https://api.crossref.org/)

## Best Practices

### 1. Always Use Field Selection
```bash
crossref works search "machine learning" \
  --select DOI,title,author,published-online,abstract,URL
```
Payloads can be very large; field selection is expected, not just nice to have.

### 2. Prefer Polite Pool
```bash
crossref config set email your-email@example.com
crossref config set pool polite
```
Default to polite pool for production workflows.

### 3. Monitor Response Times
Response times grow as rate limits approach. Implement early warning before hitting hard limits.

### 4. Don't Treat Crossref as PubMed
Crossref does not support deep keyword search over abstracts like PubMed. Use Europe PMC or Semantic Scholar for that.

## Contributing

This tool implements Crossref's API with specificity to its filter-heavy query model, three-tier pool system, and DOI registry behavior. Idiosyncrasies like abstract copyright warnings and pool etiquette are features, not bugs.

## License

TBD (implementation phase)

---

**Status:** Design complete. Implementation pending.
**Version:** 0.1.0 (planned)
**API Documentation:** [Crossref REST API](https://api.crossref.org)
**Rate Limits:** Three-tier system: Public (5/1), Polite (10/3), Plus (150/unlimited)
