# Codex instructions for njupt-site-graph

You are working in the NJUPT instance project of `static-site-graph`.

## Mission

Build a complete, auditable structured site graph for NJUPT public websites. First reference site: `https://jwc.njupt.edu.cn/`.

## Upstream template

The upstream template lives at:

```text
D:\code\github\hicancan\static-site-graph
```

If a pattern is reusable across static/semi-static sites, update the upstream template too. Do not keep reusable logic only in this instance repository.

## Required Codex workflow

1. Use Chrome for real JWC DOM exploration and verification.
2. Use Python crawler for repeatable bulk crawl.
3. Keep site-specific facts under `configs/sites/jwc/` and `docs/research/`.
4. Keep generated outputs under `data/sites/jwc/`.
5. Do not save attachment binaries unless explicitly asked; preserve metadata only.
6. Never call the model complete until manifest proves every URL outcome.
7. If modeling is incomplete, mark gaps in `data/sites/jwc/reports/audit_report.md` rather than hiding them.

## Page families that must be handled for JWC

- homepage
- nav tree
- homepage modules
- section/list pages
- pagination pages
- detail article pages
- low-content detail pages
- direct attachment list items
- external systems
- external policy links
- cross-domain article links
- footer links
- inline images and embedded links

## Validation commands

```powershell
python -m sitegraph.cli validate-config configs/sites/jwc/site.yaml
python -m sitegraph.cli discover-homepage configs/sites/jwc/site.yaml --out data/sites/jwc/index/nav_tree.generated.json
python -m sitegraph.cli crawl-site configs/sites/jwc/site.yaml --out data/sites/jwc/index
pytest
```
