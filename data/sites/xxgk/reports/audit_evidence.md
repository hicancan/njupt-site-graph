# xxgk audit evidence

- Site: 信息公开, https://xxgk.njupt.edu.cn/
- Model: WebPlus-style public portal for information disclosure pages. Homepage navigation and modules expose list/detail pages; attachments are captured as metadata only.
- Pagination: next-link pagination. Terminal pages are proved by `data/sites/xxgk/index/coverage_report.json`.
- Scope exclusions: login-only systems, third-party bodies, and binary attachment bodies are not crawled; external destinations are recorded as outcomes.
- Reproduce: open the homepage and representative list/detail pages with Chrome DevTools MCP, inspect anchors/network/console, then run `python scripts/sitegraph_registry.py crawl --include xxgk` and validate the coverage report.
