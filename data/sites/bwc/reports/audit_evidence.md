# bwc audit evidence

- Site: 保卫处, https://bwc.njupt.edu.cn/
- Model: WebPlus-style public portal. Homepage navigation and modules expose list pages; detail pages use `/20*/**/page.htm`; attachments are captured as metadata only.
- Pagination: next-link pagination. Terminal pages are proved by `data/sites/bwc/index/coverage_report.json`.
- Scope exclusions: login-only systems, third-party bodies, and binary attachment bodies are not crawled; external destinations are recorded as outcomes.
- Reproduce: open the homepage and representative list/detail pages with Chrome DevTools MCP, inspect anchors/network/console, then run `python scripts/sitegraph_registry.py crawl --include bwc` and validate the coverage report.
