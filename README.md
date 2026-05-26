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

## First command for Claude Code

Open this repository in Claude Code with Chrome enabled:

```powershell
cd D:\code\github\hicancan\njupt-site-graph
claude --chrome
```

Then paste the command from `prompts/GOAL_PROMPT.md`.

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
5. Export contract for `njupt-search` is documented and tested.
6. Reusable patterns are backfed into `D:\code\github\hicancan\static-site-graph`.
