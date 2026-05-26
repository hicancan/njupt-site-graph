# JWC Structured Sitegraph Audit Report

Generated: 2026-05-26 Asia/Shanghai

Reference site: `https://jwc.njupt.edu.cn/`

## Status

Complete for the current public JWC crawl scope. The final manifest records an outcome for every discovered URL and reports zero crawl errors.

## Chrome-Verified Page Families

Chrome DOM inspection was performed for these representative pages before the crawler model was finalized:

- Homepage: `https://jwc.njupt.edu.cn/`
  - Verified global navigation, dropdown navigation, homepage news/notice modules, comprehensive service links, undergraduate teaching project links, footer links, direct homepage attachment item, external systems, cross-domain article links, and same-domain list/detail links.
- Policy/list page: `https://jwc.njupt.edu.cn/1746/list.htm`
  - Verified scoped list container `.news_list.list2`, mixed internal detail pages, direct attachments, external policy links, and pagination.
- Download/resource page: `https://jwc.njupt.edu.cn/1690/list.htm`
  - Verified direct attachment list items and repeated first-item markup; crawler dedupes by URL plus label.
- Full detail page: `https://jwc.njupt.edu.cn/2026/0327/c1594a298565/page.htm`
  - Extracted title, publisher, published date, view count, normal body content, inline links/images, and 4 attachments.
- Low-content detail page: `https://jwc.njupt.edu.cn/2026/0518/c1594a302043/page.htm`
  - Extracted title, publisher, published date, view count, and classified `content_status=low_content`.

## Final Package Coverage

Manifest totals from `data/sites/jwc/index/manifest.json`:

- sections: 139
- nav nodes: 119
- homepage modules: 10
- list pages: 661
- detail pages: 6884
- low-content detail pages: 750
- attachments: 7905
- external links: 426
- edges: 16311
- URL outcomes: 19089

Outcome summary:

- crawled homepage: 1
- crawled list pages: 661
- crawled detail pages: 6884
- attachment metadata only: 7140
- inline images recorded: 3926
- inline links recorded: 121
- external links recorded: 253
- external policy links recorded: 40
- external system links recorded: 5
- cross-domain article links recorded: 58

Quality flags:

- `all_discovered_urls_have_outcomes: true`
- `errors: 0`
- `attachment_policy: metadata_only`
- `external_link_policy: record_only`

## Required Output Files

Generated under `data/sites/jwc/index/`:

- `site.json`
- `nav_tree.json`
- `sections.json`
- `list_pages.jsonl`
- `detail_pages.jsonl`
- `attachments.jsonl`
- `external_links.jsonl`
- `edges.jsonl`
- `manifest.json`

Additional generated evidence:

- `homepage_modules.json`
- `nav_tree.generated.json` from `discover-homepage`

## Representative Extraction Evidence

Full detail article:

- URL: `https://jwc.njupt.edu.cn/2026/0327/c1594a298565/page.htm`
- title: `【教务管理办公室】2025-2026学年第二学期在线开放课程（慕课）线下考试报名通知`
- publisher: `综合办公室`
- published_at: `2026-03-27`
- view_count: `2645`
- content_status: `normal_content`
- attachment_count: `4`
- extraction_strategy: `.wp_articlecontent`

Low-content detail article:

- URL: `https://jwc.njupt.edu.cn/2026/0518/c1594a302043/page.htm`
- title: `【教务管理办公室】关于做好2025-2026学年第二学期期末考试工作安排的通知`
- publisher: `综合办公室`
- published_at: `2026-05-18`
- view_count: `10`
- content_status: `low_content`
- attachment_count: `0`
- extraction_strategy: `.wp_articlecontent`

Direct nav detail:

- URL: `https://jwc.njupt.edu.cn/2025/0904/c1528a288083/page.htm`
- title: `2025-2026学年校历`
- publisher: `系统管理员`
- published_at: `2025-09-04`
- content_status: `low_content`

Representative list pages:

- `jwc_rules_root` page 1: 14 items, including 6 internal detail pages and 8 external links.
- `jwc_rules_root` page 2: 14 items, including 4 direct attachments and 10 external links.
- `jwc_download_student_forms` page 1: 6 deduped direct attachment items.
- `jwc_homepage_notice_module` page 1: 14 items, including 13 internal detail pages and 1 direct attachment.

## Remaining Gaps Or Blockers

No crawl blockers remain in the generated manifest.

Intentional policy limits:

- Attachment binaries were not downloaded; only metadata was preserved.
- External systems, external policies, and cross-domain articles were recorded but not crawled as content.
