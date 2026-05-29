# njupt-site-graph

`njupt-site-graph` is the NJUPT instance of the `static-site-graph` template.

Its first reference site is `https://jwc.njupt.edu.cn/`, but the project is not limited to JWC. It will model NJUPT public/static-like sites into structured site packages and export data for `njupt-search`.

## Relationship

```text
static-site-graph  -> framework/template/rules
njupt-site-graph   -> NJUPT site modeling + crawl data production
njupt-search       -> downstream semantic search product
```

## Local path assumption

The intended local layout is:

```text
D:\code\github\hicancan\static-site-graph
D:\code\github\hicancan\njupt-site-graph
D:\code\github\hicancan\njupt-search
```

## Repository boundary

Only product-facing configuration, tests, workflows, and generated site packages are tracked here.
Local research notes, audit reports, prompts, and agent/Claude/Codex configuration are intentionally ignored.

## Downstream automation contract

`Update Sitegraph Data` dispatches `sitegraph-data-updated` to `hicancan/njupt-search` after sitegraph data changes. Manual `workflow_dispatch` can set `dispatch_only=true` to verify the downstream trigger without running a live crawl.

The `NJUPT_SEARCH_DISPATCH_TOKEN` secret must be a valid GitHub token with write access to repository contents on `hicancan/njupt-search`, which is the permission GitHub requires for creating a repository dispatch event. A `Bad credentials (HTTP 401)` failure in the trigger step means the secret value is invalid or expired; rotate the secret rather than changing payload code.

## Human setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e D:\code\github\hicancan\static-site-graph[dev]
python -m pip install -e .[dev]
python -m sitegraph.cli validate-config configs/sites/jwc/site.yaml
python -m sitegraph.cli discover-homepage configs/sites/jwc/site.yaml --out data/sites/jwc/index/nav_tree.generated.json
```

## Completion target

Complete state means:

1. JWC site model has homepage/nav/section/list/pagination/detail/attachment/external/edge modeling.
2. Every discovered URL is classified into a manifest outcome.
3. Chrome has verified each distinct page family.
4. `data/sites/jwc/index/` contains the required structured package.
5. Export contract for `njupt-search` is enforced by tests and generated package manifests.
6. Reusable patterns are backfed into `D:\code\github\hicancan\static-site-graph`.
