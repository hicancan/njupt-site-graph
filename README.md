# njupt-site-graph

南京邮电大学站点实例与统一校园语料生产仓库。

## Boundary

```text
static-site-graph generic crawler
  -> SitePackage
njupt-site-graph corpus exporter
  -> NjuptCorpusSnapshot
njupt-search
  -> SearchBundle
```

This repository contains no search ranking, inverted index, WASM or search
sharding code.

```text
njupt-site-graph/
├─ sites/       # NJUPT SiteDefinition files and NJUPT-only plugins
├─ corpus/      # NjuptCorpusSnapshot schema and exporter
├─ tests/       # fixture and contract tests
├─ ops/         # local crawl/export/publish composition
└─ docs/        # contracts and local workflow
```

## Local use

Install this repository and an explicit checkout of `static-site-graph` in one
virtual environment:

```powershell
uv venv
uv pip install -e D:\code\github\hicancan\static-site-graph
uv pip install -e .[dev]
```

Fast, network-free tests:

```powershell
uv run pytest -q
```

Validate all site definitions and inspect current local packages:

```powershell
uv run python ops/njupt.py validate-configs
uv run python ops/njupt.py validate-packages --packages-root D:\Data\njupt-site-packages
uv run python ops/njupt.py summary --packages-root D:\Data\njupt-site-packages
```

Run one real crawl or every configured crawl:

```powershell
uv run python ops/njupt.py crawl --include job91 --packages-root D:\Data\njupt-site-packages
uv run python ops/njupt.py crawl --packages-root D:\Data\njupt-site-packages
uv run python ops/njupt.py crawl --packages-root D:\Data\njupt-site-packages --incremental
uv run python ops/njupt.py crawl --packages-root D:\Data\njupt-site-packages --incremental --jobs 4
```

Export the only downstream artifact:

```powershell
uv run python ops/njupt.py export-corpus `
  --packages-root D:\Data\njupt-site-packages `
  --out D:\Data\njupt-corpus
```

SitePackage output is never located through the source tree or registry. Every
crawl, validation, summary, and corpus export receives one explicit package
root; each registered site owns `<packages-root>/<site-id>/index`.
The exporter validates each package identity and every member's path, byte size
and SHA-256 before consuming its records.

The complete local three-repository loop is owned by the thin
`njupt-search/ops/local.ps1` orchestrator. It requires all three repository
paths and explicit corpus/bundle output paths; this repository does not locate
or update a search checkout implicitly.

The snapshot contains `manifest.json`, `documents.jsonl.zst`,
`attachments.jsonl.zst` and `links.jsonl.zst`. It is immutable and identified by
the format, source metadata, counts and artifact identities in its manifest. A
document contains exactly `id`, `source`, `url`, `title`, `content`,
`published_at`, `updated_at`, `section`, `kind`, `tags` and `attachment_ids`;
source display names are stored once in the manifest.
`attachments.jsonl.zst` is the only authority for attachment metadata and parent
relationships. Documents reference it by ID. `links.jsonl.zst` preserves site
relationships; only explicitly labelled external links become searchable
external documents. Search verifies the link artifact identity but does not
decompress or interpret it.

The scheduled `Publish NJUPT Corpus` workflow stores the complete SitePackages
beside every immutable corpus release. The next run restores and validates that
single prior package set before invoking the crawler with `--incremental`.
Independent sites run with bounded concurrency; each site's discovery and
incremental merge semantics remain sequential and unchanged.
Only the first run without any prior package asset performs an explicit
bootstrap crawl. A successful corpus release dispatches its URL, identity and
archive SHA-256 to `njupt-search`; no source branch or data lock is rewritten.
