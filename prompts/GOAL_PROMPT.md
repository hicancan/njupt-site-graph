# One-shot Claude Code `/goal` prompt

Run Claude Code from `D:\code\github\hicancan\njupt-site-graph` with Chrome enabled:

```powershell
claude --chrome
```

Then paste this single command:

```text
/goal Complete njupt-site-graph to the agreed top-level state for the JWC reference site: use Chrome to audit every distinct JWC page family; complete configs/sites/jwc site modeling for homepage nav, homepage modules, physical sections, list pages, pagination, detail pages, low-content pages, direct attachment items, external systems, external policy/cross-domain links, footer links, inline images, attachments metadata, and edges; run the Python sitegraph crawler to generate data/sites/jwc/index/{site.json,nav_tree.json,sections.json,list_pages.jsonl,detail_pages.jsonl,attachments.jsonl,external_links.jsonl,edges.jsonl,manifest.json}; update data/sites/jwc/reports/audit_report.md with exact coverage and remaining blockers; run validation commands and tests; if reusable framework/schema/crawler patterns are found, update D:/code/github/hicancan/static-site-graph and run its tests too; prove completion by surfacing command outputs for validate-config, discover-homepage, crawl-site, pytest, and a manifest summary, or stop after 25 turns with a blocker list and no silent failures.
```

Notes:

- `/goal` is built into Claude Code v2.1.139+.
- The evaluator only judges what Claude surfaces in the conversation, so Claude must print command results and manifest summaries.
- If Chrome connection fails, Claude must report the exact `/chrome` status and continue only with HTTP-discovery marked as non-final.
