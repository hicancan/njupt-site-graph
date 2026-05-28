# XSC structured sitegraph audit report

Generated: 2026-05-28 Asia/Shanghai

Reference site: `https://xsc.njupt.edu.cn/`

## Status

Complete for the current public XSC crawl scope. The manifest records an explicit outcome for every discovered URL and reports zero crawl errors.

## Commands run

```powershell
uv run python -m sitegraph.cli validate-config configs/sites/xsc/site.yaml
uv run python -m sitegraph.cli discover-homepage configs/sites/xsc/site.yaml --out data/sites/xsc/index/nav_tree.generated.json
uv run python -m sitegraph.cli crawl-site configs/sites/xsc/site.yaml --out data/sites/xsc/index
```

## Browser evidence

Browser audit verified homepage navigation, nested dropdowns, homepage modules, footer links, external systems, representative list pages, representative detail pages, direct attachments, legacy `list.psp` behavior, and static zero-item content pages.

Representative URLs:

- Homepage: `https://xsc.njupt.edu.cn/`
- List/pagination: `https://xsc.njupt.edu.cn/1176/list.htm`
- Download/resource list: `https://xsc.njupt.edu.cn/1169/list.htm`
- Legacy list: `https://xsc.njupt.edu.cn/_s24/_t3618/1160%20/list.psp`
- Static section content: `https://xsc.njupt.edu.cn/1149/list.htm`
- Detail: `https://xsc.njupt.edu.cn/2010/0420/c1147a13374/page.htm`

## Manifest totals

- sections: 34
- nav nodes: 30
- homepage modules: 10
- list pages: 233
- detail/content pages: 1589
- low-content pages: 112
- attachments: 17
- external links: 75
- edges: 1878
- URL outcomes: 6414

Outcome summary:

- crawled homepage: 1
- crawled list pages: 232
- crawled detail pages: 1586
- attachment metadata only: 14
- inline images recorded: 4517
- external links recorded: 53
- external policy links recorded: 3
- external system links recorded: 7

## Quality conclusion

- `all_discovered_urls_have_outcomes: true`
- `errors: 0`
- `attachment_policy: metadata_only`
- `external_link_policy: record_only`

No attachment binaries were saved. External systems, WeChat articles, and policy/external sites were recorded only.

## Remaining limitations

No blocking gaps remain. Some public `list.htm` pages are static content pages rather than lists; they are preserved as `section_content_page` records while their discovered URLs retain explicit list-page outcomes.
