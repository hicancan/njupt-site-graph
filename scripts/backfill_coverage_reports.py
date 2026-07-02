from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from sitegraph.config import load_yaml
from sitegraph.coverage import (
    apply_coverage_to_manifest,
    build_coverage_report,
    record_pagination_evidence,
    write_coverage_report,
)
from sitegraph.crawl_output import read_jsonl
from sitegraph.util import write_json

from sitegraph_registry import ROOT, read_registry


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _section_max_pages(section: dict, cfg: dict) -> int:
    pagination = section.get("pagination") if isinstance(section.get("pagination"), dict) else {}
    policy = cfg.get("crawl_policy", {})
    return int(pagination.get("max_pages_safety", policy.get("max_pages_safety", 20)))


def _next_list_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"list(\d+)\.(htm|psp)$", url)
    if match:
        next_index = int(match.group(1)) + 1
        return re.sub(r"list\d+\.(htm|psp)$", f"list{next_index}.{match.group(2)}", url)
    match = re.search(r"/list\.(htm|psp)$", url)
    if match:
        return re.sub(r"/list\.(htm|psp)$", f"/list2.{match.group(1)}", url)
    return None


def _backfill_site(site: dict[str, str]) -> None:
    site_id = site["id"]
    cfg = load_yaml(ROOT / site["config"])
    package_root = ROOT / site["package"]
    manifest = _read_json(package_root / "manifest.json")
    sections = _read_json(package_root / "sections.json")
    list_pages = read_jsonl(package_root / "list_pages.jsonl")
    detail_pages = read_jsonl(package_root / "detail_pages.jsonl")
    attachments = read_jsonl(package_root / "attachments.jsonl")
    external_links = read_jsonl(package_root / "external_links.jsonl")
    by_section: dict[str, list[dict]] = {}
    for page in list_pages:
        by_section.setdefault(str(page.get("section_id") or ""), []).append(page)
    manifest["errors"] = []
    manifest["coverage"] = {"pagination": [], "unknown_urls": [], "exclusions": []}
    for section in sections:
        section_id = str(section.get("section_id") or "")
        pages = sorted(by_section.get(section_id, []), key=lambda item: int(item.get("page_index") or 0))
        if not pages:
            continue
        max_pages = _section_max_pages(section, cfg)
        pages_crawled = len(pages)
        terminal_verified = pages_crawled < max_pages
        termination_reason = "existing_package_under_safety_cap" if terminal_verified else "safety_cap"
        inferred_next_url = None if terminal_verified else _next_list_url(str(pages[-1].get("url") or ""))
        record_pagination_evidence(
            manifest,
            {
                "section_id": section_id,
                "section_name": section.get("name"),
                "section_url": section.get("url"),
                "last_url": pages[-1].get("url"),
                "next_url": inferred_next_url or (None if terminal_verified else "unknown_after_existing_package_cap"),
                "pages_crawled": pages_crawled,
                "max_pages_safety": max_pages,
                "termination_reason": termination_reason,
                "terminal_verified": terminal_verified,
            },
        )
        if not terminal_verified:
            manifest.setdefault("errors", []).append(
                {
                    "section_id": section_id,
                    "url": pages[-1].get("url"),
                    "next_url": inferred_next_url,
                    "phase": "pagination",
                    "error": f"existing package reaches max_pages_safety={max_pages}; run full crawl with a higher verified limit",
                }
            )
    report = build_coverage_report(
        cfg=cfg,
        site_id=site_id,
        out_root=package_root,
        manifest=manifest,
        sections=sections,
        list_pages=list_pages,
        detail_pages=detail_pages,
        attachments=attachments,
        external_links=external_links,
        incremental=False,
    )
    apply_coverage_to_manifest(manifest, report)
    write_coverage_report(package_root, report, incremental=False)
    write_json(package_root / "manifest.json", manifest)
    print(json.dumps({"site": site_id, "coverage_status": report["coverage_status"], "reasons": report["incomplete_reasons"]}, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill coverage_report.json from existing site packages.")
    parser.add_argument("--include", default=None)
    args = parser.parse_args(argv)
    for site in read_registry(args.include):
        _backfill_site(site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
