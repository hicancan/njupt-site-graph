# www audit evidence

- Site: 南京邮电大学主站, https://www.njupt.edu.cn/
- Chrome DevTools MCP evidence: homepage loaded with HTTP 200; accessibility snapshot exposed full top navigation, footer links, public modules, list links, detail links, external systems, and media links. Console contained Swiper warnings and one static-resource 404, which must be tracked rather than silently ignored.
- Model: WebPlus-style main portal. Configured sections include 通知通告, 南邮要闻, 学术活动; additional public links are classified as same-domain lists/details, attachments, or external outcomes.
- Pagination: next-link pagination. Terminal pages are proved by `data/sites/www/index/coverage_report.json`.
- Scope exclusions: login-only systems, WeChat/social bodies, third-party bodies, and binary attachment bodies are not crawled; external destinations are recorded as outcomes.
- Reproduce: open the homepage with Chrome DevTools MCP, inspect anchors/network/console, then run `python scripts/sitegraph_registry.py crawl --include www` and validate the coverage report.
