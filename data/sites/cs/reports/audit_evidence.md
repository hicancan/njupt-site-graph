# cs audit evidence

- Site: 计算机学院, https://cs.njupt.edu.cn/
- Model: college public portal. Configured sections are used where homepage auto-discovery is intentionally disabled to prevent over-crawling unrelated inline links.
- Pagination: next-link pagination. Terminal pages are proved by `data/sites/cs/index/coverage_report.json`.
- Scope exclusions: login-only systems, third-party bodies, and binary attachment bodies are not crawled; external destinations are recorded as outcomes.
- Reproduce: open the homepage and representative list/detail pages with Chrome DevTools MCP, inspect anchors/network/console, then run `python scripts/sitegraph_registry.py crawl --include cs` and validate the coverage report.
