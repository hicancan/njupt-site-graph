---
description: Advance njupt-site-graph toward complete JWC structured sitegraph modeling, crawl, validation, and upstream template backfeed.
argument-hint: "[site-id or goal]"
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write WebFetch
---

Work through the NJUPT sitegraph completion loop:

1. Read `AGENTS.md`, `.Codex/rules/`, `prompts/GOAL_PROMPT.md`, and `docs/research/jwc_deep_audit.md`.
2. Inspect `configs/sites/jwc/` and generated `data/sites/jwc/` outputs.
3. Use Chrome for JWC homepage, representative list pages, detail pages, low-content pages, direct attachment items, and external systems.
4. Update JWC site config and selectors.
5. Run crawler and validators.
6. Emit or update site package files under `data/sites/jwc/index/`.
7. Update `data/sites/jwc/reports/audit_report.md` with exact remaining gaps.
8. If reusable framework changes are needed, apply them in `D:/code/github/hicancan/static-site-graph` and run its tests.
9. Surface final command outputs proving completion.
