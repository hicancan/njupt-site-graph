# CXCY structured sitegraph audit report

Generated: 2026-05-28 Asia/Shanghai

Reference site: `https://cxcy.njupt.edu.cn/`

## Status

Complete for the current public CXCY crawl scope. The manifest records an explicit outcome for every discovered URL and reports zero crawl errors.

## Commands run

```powershell
uv run python -m sitegraph.cli validate-config configs/sites/cxcy/site.yaml
uv run python -m sitegraph.cli discover-homepage configs/sites/cxcy/site.yaml --out data/sites/cxcy/index/nav_tree.generated.json
uv run python -m sitegraph.cli crawl-site configs/sites/cxcy/site.yaml --out data/sites/cxcy/index
```

## Browser evidence

Browser audit verified homepage navigation, nested dropdowns, homepage modules, quick-link band, footer `_redirect` links, representative list pages, download center attachments, representative detail pages, and static zero-item content pages.

Representative URLs:

- Homepage: `https://cxcy.njupt.edu.cn/`
- News list: `https://cxcy.njupt.edu.cn/xwzx/list.htm`
- Notice list: `https://cxcy.njupt.edu.cn/tzgg/list.htm`
- Download center: `https://cxcy.njupt.edu.cn/15468/list.htm`
- Static section content: `https://cxcy.njupt.edu.cn/15485/list.htm`
- Detail with attachments: `https://cxcy.njupt.edu.cn/2026/0521/c11336a302380/page.htm`
- Redirect link example: `https://cxcy.njupt.edu.cn/_redirect?siteId=331&columnId=15478&articleId=141199`

## Manifest totals

- sections: 39
- nav nodes: 29
- homepage modules: 5
- list pages: 83
- detail/content pages: 612
- low-content pages: 82
- attachments: 205
- external links: 60
- edges: 1101
- URL outcomes: 1311

Outcome summary:

- crawled homepage: 1
- crawled list pages: 83
- crawled detail pages: 590
- attachment metadata only: 202
- inline images recorded: 370
- external links recorded: 55
- external policy links recorded: 4
- external system links recorded: 3
- cross-domain article links recorded: 2

## Quality conclusion

- `all_discovered_urls_have_outcomes: true`
- `errors: 0`
- `attachment_policy: metadata_only`
- `external_link_policy: record_only`

No attachment binaries were saved. Same-domain `_redirect` URLs were resolved only to record their HTTP 302 destinations and were not recursively crawled.

## Remaining limitations

No blocking gaps remain. Empty or mailbox-style sections are preserved as low-content `section_content_page` records where applicable, with explicit manifest outcomes.
