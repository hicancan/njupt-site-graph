# bhs audit evidence

- Site: 贝尔英才学院, https://bhs.njupt.edu.cn/
- Model: college public portal. Homepage navigation and modules expose list pages; detail pages use WebPlus-style article URLs; attachments are captured as metadata only.
- Pagination: next-link pagination. Terminal pages are proved by `data/sites/bhs/index/coverage_report.json`.
- Scope exclusions: login-only systems, third-party bodies, and binary attachment bodies are not crawled; external destinations are recorded as outcomes.
- Reproduce: open the homepage and representative list/detail pages with Chrome DevTools MCP, inspect anchors/network/console, then run `python scripts/sitegraph_registry.py crawl --include bhs` and validate the coverage report.
