# Architecture

This repository owns the NJUPT instance of `static-site-graph`.

```text
sites/* SiteDefinition
  -> static-site-graph generic crawler or a site-owned plugin
  -> local SitePackage directories
  -> corpus exporter
  -> NjuptCorpusSnapshot
```

`sites` contains NJUPT configuration and exceptional integrations such as the
91job API. `corpus` owns the only downstream contract. `ops` composes crawl,
validation, export and publication commands without implementing extraction or
search.

Before reading records, the exporter validates the producer-owned SitePackage
format, package identity, member paths, sizes, hashes, schemas, site references,
record identities and counts. It never repairs or guesses invalid upstream
content.

`NjuptCorpusSnapshot` contains:

```text
manifest.json
documents.jsonl.zst
attachments.jsonl.zst
links.jsonl.zst
```

Each `NjuptDocument` contains exactly `id`, `source`, `url`, `title`, `content`,
`published_at`, `updated_at`, `section`, `kind`, `tags` and `attachments`.
Human-readable source names live once in `manifest.json.sources`; they are not
repeated in every document.

The attachment table is authoritative for attachment identity and parent
relationships. Nested document attachments are a deliberately repeated,
minimal projection used by search; the producer validates exact equality.
The link table preserves discovered relationships and provenance. It is not a
search input by itself; labelled external links are materialized as ordinary
`kind=external` documents, while missing labels remain `null` rather than being
invented from a URL.

The corpus exporter removes only aliases that it can prove are the same
upstream object: WebPlus article URLs with the same source article identifier
are merged only when title, body, dates, kind and tags are equal, and repeated
section-content pagination rows are merged only when their complete document
semantics are equal. Attachments are remapped to the selected canonical parent.
Conflicting aliases and merely similar bodies remain separate; there is no
content-based or guessed deduplication.

The snapshot identity hashes all three compressed row artifacts. Consequently a
links-only change changes the snapshot identity and triggers a deterministic
SearchBundle rebuild even though the search reader only maps document rows.
This keeps one explicit corpus identity instead of introducing a second search
input identity. The SearchBundle has its own identity over the corpus identity
and all emitted search artifacts.

The snapshot is immutable and addressed by its content identity. Crawl,
validation and export commands receive one explicit external SitePackage root;
the registry never selects a data directory. HTTP failures, parsing failures,
page counts, empty bodies and timestamps remain ordinary diagnostics in a
`SitePackage`; they do not change the exported data contract.
