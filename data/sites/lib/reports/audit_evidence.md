# lib audit evidence

- Site: 图书馆, https://lib.njupt.edu.cn/
- Model: public portal with WebPlus-like navigation/list/detail pages. Attachments are captured as metadata only.
- Pagination: next-link/list pagination. Terminal pages are proved by `data/sites/lib/index/coverage_report.json`.
- Scope exclusions: reader login, subscription databases, third-party resources, and binary attachment bodies are not crawled; external destinations are recorded as outcomes.
- Reproduce: open the homepage and representative list/detail pages with Chrome DevTools MCP, inspect anchors/network/console, then run `python scripts/sitegraph_registry.py crawl --include lib` and validate the coverage report.
