# njupt-site-graph development rules

- This repository owns NJUPT site configuration, NJUPT-only crawler plugins and
  the `NjuptCorpusSnapshot` contract.
- Generic crawling belongs to `static-site-graph`; search indexing and ranking
  belong to `njupt-search`.
- `sites` contains instances, `corpus` transforms `SitePackage` values, and `ops`
  only composes commands.
- Local crawl output belongs in an explicit external `D:\Data` or task staging
  path and is never committed as source.
- Preserve a recoverable corpus snapshot before removing the only collected copy.
- HTTP errors, parse errors, page counts, empty content and timestamps are
  diagnostics, not release states.
- Support only the current snapshot format. Missing or incompatible input fails.
- Delete replaced code and tests immediately; do not add alternate-format readers,
  path aliases, governance state machines or source-to-search coupling.
