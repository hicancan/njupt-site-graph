# njupt-search integration contract

`njupt-site-graph` exports structured truth packages. `njupt-search` consumes selected data and performs semantic enrichment, typed terms, query aliases, ranking, and frontend delivery.

## Do not push raw full site data into njupt-search first screen

The full sitegraph is a truth source. `njupt-search` should ingest:

- recent or high-value details;
- evergreen workflows and policies;
- external system entries;
- resource metadata;
- all source/section provenance.

## Export candidates

A downstream exporter should produce:

- `source_id`
- `section_id`
- `nav_path`
- `page_type`
- `title`
- `url`
- `published_at`
- `content_text`
- `attachments[]` metadata only
- `external_links[]`
- `content_status`
- `sitegraph_provenance`

LLM enrichment belongs in `njupt-search`, not this upstream project, unless the task explicitly introduces semantic preprocessing.
