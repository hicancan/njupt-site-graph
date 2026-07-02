# scie audit evidence

- Site: 通信与信息工程学院, https://scie.njupt.edu.cn/
- Model: college public portal. Configured sections are used where homepage auto-discovery is intentionally disabled to prevent over-crawling unrelated inline links.
- Pagination: next-link pagination. Terminal pages are proved by `data/sites/scie/index/coverage_report.json`.
- Scope exclusions: login-only systems, third-party bodies, and binary attachment bodies are not crawled; external destinations are recorded as outcomes.
- Reproduce: open the homepage and representative list/detail pages with Chrome DevTools MCP, inspect anchors/network/console, then run `python scripts/sitegraph_registry.py crawl --include scie` and validate the coverage report.
