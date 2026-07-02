# job91 audit evidence

- Site: 南京邮电大学就业信息网, https://njupt.91job.org.cn/
- Model: explicit `job91_api` adapter, not WebPlus extraction. The adapter discovers the station id, column tree, and list records through the public Job91 API.
- Pagination: API `getLbsj` is crawled page by page with `row` and `page`; terminal pages are proved by empty/short/duplicate-page evidence in `data/sites/job91/index/coverage_report.json`.
- Scope exclusions: login-only employer/student systems and third-party bodies are not crawled; public API records are normalized as detail pages.
- Reproduce: open the SPA with Chrome DevTools MCP, inspect XHR/fetch calls, then run `python scripts/sitegraph_registry.py crawl --include job91` and validate the coverage report.
