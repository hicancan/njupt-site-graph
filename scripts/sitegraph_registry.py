from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs" / "site_registry.json"
PACKAGE_FILES = (
    "site.json",
    "nav_tree.json",
    "sections.json",
    "list_pages.jsonl",
    "detail_pages.jsonl",
    "attachments.jsonl",
    "external_links.jsonl",
    "edges.jsonl",
    "manifest.json",
    "homepage_modules.json",
    "coverage_report.json",
)
MAX_MANIFEST_BYTES = 25 * 1024 * 1024
CONSUMABLE_COVERAGE_STATUSES = {"complete", "complete_with_exclusions"}
ALLOWED_SECTION_SOURCES = {
    "declared_section",
    "homepage_nav",
    "homepage_module",
    "inline_section_link",
    "api_category",
    "archive_section",
}
FORBIDDEN_TERMINATION_REASONS = {"existing_package_under_safety_cap"}


def _resolve_package_ref(package_root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = package_root / path
    return path.resolve()


def _validate_audit_evidence_json(site_id: str, package_root: Path, ref: str) -> None:
    audit_path = _resolve_package_ref(package_root, ref)
    if not audit_path.exists():
        raise SystemExit(f"{site_id} audit JSON evidence is missing: {ref}")
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{site_id} audit JSON evidence is invalid JSON: {ref}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{site_id} audit JSON evidence must be an object: {ref}")
    if payload.get("site_id") != site_id:
        raise SystemExit(f"{site_id} audit JSON site_id mismatch: {payload.get('site_id')!r}")
    required_keys = {
        "homepage",
        "navigation_entries",
        "section_samples",
        "list_page_samples",
        "pagination_terminal_samples",
        "detail_page_samples",
        "attachment_samples",
        "external_boundaries",
        "console_errors",
        "network_errors",
        "exclusions",
    }
    missing = sorted(key for key in required_keys if key not in payload)
    if missing:
        raise SystemExit(f"{site_id} audit JSON evidence missing keys: {', '.join(missing)}")
    _reject_forbidden_termination_reasons(site_id, payload, f"audit JSON evidence {ref}")


def _reject_forbidden_termination_reasons(site_id: str, payload: object, label: str) -> None:
    if isinstance(payload, dict):
        reason = payload.get("termination_reason")
        if reason in FORBIDDEN_TERMINATION_REASONS:
            raise SystemExit(f"{site_id} {label} contains forbidden migration termination reason: {reason}")
        for value in payload.values():
            _reject_forbidden_termination_reasons(site_id, value, label)
    elif isinstance(payload, list):
        for value in payload:
            _reject_forbidden_termination_reasons(site_id, value, label)


def read_registry(include: str | None = None) -> list[dict[str, str]]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if payload.get("version") != "njupt-site-registry-v1":
        raise SystemExit(f"{REGISTRY_PATH} has unsupported version")
    sites = payload.get("sites")
    if not isinstance(sites, list) or not sites:
        raise SystemExit(f"{REGISTRY_PATH} sites must be a non-empty list")
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for site in sites:
        if not isinstance(site, dict):
            raise SystemExit("site registry entries must be objects")
        site_id = str(site.get("id") or "").strip()
        config = str(site.get("config") or "").strip()
        package = str(site.get("package") or "").strip()
        if not site_id or not config or not package:
            raise SystemExit(f"invalid site registry entry: {site!r}")
        if site_id in seen:
            raise SystemExit(f"duplicate site id in registry: {site_id}")
        seen.add(site_id)
        out.append({"id": site_id, "config": config, "package": package})
    if not include:
        return out
    requested = {item.strip() for item in include.split(",") if item.strip()}
    selected = [site for site in out if site["id"] in requested]
    missing = requested - {site["id"] for site in selected}
    if missing:
        raise SystemExit(f"unknown site ids in --include: {', '.join(sorted(missing))}")
    return selected


def run_command(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def validate_configs(_args: argparse.Namespace) -> None:
    for site in read_registry(getattr(_args, "include", None)):
        run_command([sys.executable, "-m", "sitegraph.cli", "validate-config", site["config"]])


def dry_run(args: argparse.Namespace) -> None:
    for site in read_registry(args.include):
        command = [
            sys.executable,
            "-m",
            "sitegraph.cli",
            "crawl-site",
            site["config"],
            "--out",
            site["package"],
            "--dry-run",
        ]
        if args.incremental:
            command.append("--incremental")
        run_command(command)


def crawl(args: argparse.Namespace) -> None:
    for site in read_registry(args.include):
        command = [
            sys.executable,
            "-m",
            "sitegraph.cli",
            "crawl-site",
            site["config"],
            "--out",
            site["package"],
        ]
        if args.incremental:
            command.extend(
                [
                    "--incremental",
                    "--incremental-known-page-stop",
                    str(args.incremental_known_page_stop),
                    "--incremental-refresh-frontier",
                    str(args.incremental_refresh_frontier),
                ]
            )
        run_command(command)


def validate_packages(args: argparse.Namespace) -> None:
    for site in read_registry(args.include):
        site_id = site["id"]
        package_root = ROOT / site["package"]
        missing = [filename for filename in PACKAGE_FILES if not (package_root / filename).exists()]
        if missing:
            raise SystemExit(f"{site_id} package is incomplete; missing: {', '.join(missing)}")
        manifest_path = package_root / "manifest.json"
        manifest_bytes = manifest_path.stat().st_size
        if manifest_bytes > MAX_MANIFEST_BYTES:
            raise SystemExit(f"{site_id} manifest is too large: {manifest_bytes} bytes > {MAX_MANIFEST_BYTES}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("site_id") != site_id:
            raise SystemExit(f"{manifest_path} site_id mismatch: expected {site_id}, got {manifest.get('site_id')!r}")
        quality = manifest.get("quality")
        if not isinstance(quality, dict):
            raise SystemExit(f"{manifest_path} missing quality object")
        if quality.get("all_discovered_urls_have_outcomes") is not True:
            raise SystemExit(f"{site_id} has discovered URLs without outcomes")
        errors = manifest.get("errors")
        if not isinstance(errors, list):
            raise SystemExit(f"{manifest_path} errors must be a list")
        if quality.get("errors") != 0 or errors:
            preview = json.dumps(errors[:10], ensure_ascii=False, indent=2)
            raise SystemExit(f"{site_id} package contains crawl errors:\n{preview}")
        coverage_path = package_root / "coverage_report.json"
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        _reject_forbidden_termination_reasons(site_id, coverage, "coverage report")
        if coverage.get("site_id") != site_id:
            raise SystemExit(f"{coverage_path} site_id mismatch: expected {site_id}, got {coverage.get('site_id')!r}")
        manifest_status = str(manifest.get("coverage_status") or "")
        quality_status = str(quality.get("coverage_status") or "")
        coverage_status = str(coverage.get("coverage_status") or "")
        if manifest_status not in CONSUMABLE_COVERAGE_STATUSES or quality_status not in CONSUMABLE_COVERAGE_STATUSES:
            raise SystemExit(f"{site_id} coverage_status must be complete or complete_with_exclusions")
        if coverage_status not in CONSUMABLE_COVERAGE_STATUSES:
            raise SystemExit(f"{site_id} coverage report is not consumable: {coverage.get('incomplete_reasons')!r}")
        if len({manifest_status, quality_status, coverage_status}) != 1:
            raise SystemExit(
                f"{site_id} coverage_status drift: manifest={manifest_status}, quality={quality_status}, report={coverage_status}"
            )
        evidence_source = str(coverage.get("evidence_source") or manifest.get("evidence_source") or quality.get("evidence_source") or "")
        if evidence_source != "full_crawl":
            raise SystemExit(f"{site_id} evidence_source must be full_crawl, got {evidence_source!r}")
        audit_ref = manifest.get("audit_evidence_ref") or quality.get("audit_evidence_ref") or coverage.get("audit_evidence_ref")
        if not isinstance(audit_ref, str) or not audit_ref.strip():
            raise SystemExit(f"{site_id} missing audit_evidence_ref")
        audit_path = _resolve_package_ref(package_root, audit_ref)
        if not audit_path.exists():
            raise SystemExit(f"{site_id} audit evidence is missing: {audit_ref}")
        audit_json_ref = (
            manifest.get("audit_evidence_json_ref")
            or quality.get("audit_evidence_json_ref")
            or coverage.get("audit_evidence_json_ref")
        )
        if not isinstance(audit_json_ref, str) or not audit_json_ref.strip():
            raise SystemExit(f"{site_id} missing audit_evidence_json_ref")
        _validate_audit_evidence_json(site_id, package_root, audit_json_ref)
        if manifest.get("pagination_terminal_verified") is not True:
            raise SystemExit(f"{site_id} pagination_terminal_verified must be true")
        if int(manifest.get("unknown_url_count") or 0) != 0:
            raise SystemExit(f"{site_id} unknown_url_count must be zero")
        exclusions = (coverage.get("urls") or {}).get("exclusions") or []
        if exclusions and coverage_status != "complete_with_exclusions":
            raise SystemExit(f"{site_id} packages with exclusions must use complete_with_exclusions")
        if not exclusions and coverage_status != "complete":
            raise SystemExit(f"{site_id} packages without exclusions must use complete")
        section_sources = ((coverage.get("sections") or {}).get("by_source") or {})
        invalid_sources = sorted(str(source) for source in section_sources if source not in ALLOWED_SECTION_SOURCES)
        if invalid_sources:
            raise SystemExit(f"{site_id} has invalid section sources: {', '.join(invalid_sources)}")
        today = date.today().isoformat()
        for exclusion in exclusions:
            if not isinstance(exclusion, dict):
                raise SystemExit(f"{site_id} coverage exclusion entries must be objects")
            missing = [
                key
                for key in ("scope", "reason", "evidence_url", "expiry", "owner_action")
                if not str(exclusion.get(key) or "").strip()
            ]
            if missing:
                raise SystemExit(f"{site_id} coverage exclusions missing required keys: {', '.join(missing)}")
            if str(exclusion["expiry"]) < today:
                raise SystemExit(f"{site_id} coverage exclusion expired: {exclusion!r}")


def summary(_args: argparse.Namespace) -> None:
    rows = []
    for site in read_registry(getattr(_args, "include", None)):
        manifest_path = ROOT / site["package"] / "manifest.json"
        if not manifest_path.exists():
            rows.append({"site": site["id"], "missing": str(manifest_path)})
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        totals = manifest.get("totals") or {}
        rows.append(
            {
                "site": site["id"],
                "detail_pages": totals.get("detail_pages"),
                "attachments": totals.get("attachments"),
                "external_links": totals.get("external_links"),
                "url_outcomes": totals.get("url_outcomes"),
                "errors": (manifest.get("quality") or {}).get("errors"),
                "coverage_status": manifest.get("coverage_status"),
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Operate every site in configs/site_registry.json.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate-configs")
    validate_parser.add_argument("--include", default=None)
    validate_parser.set_defaults(func=validate_configs)
    dry_parser = subparsers.add_parser("dry-run")
    dry_parser.add_argument("--incremental", action="store_true")
    dry_parser.add_argument("--include", default=None)
    dry_parser.set_defaults(func=dry_run)
    crawl_parser = subparsers.add_parser("crawl")
    crawl_parser.add_argument("--incremental", action="store_true")
    crawl_parser.add_argument("--include", default=None)
    crawl_parser.add_argument("--incremental-known-page-stop", type=int, default=2)
    crawl_parser.add_argument("--incremental-refresh-frontier", type=int, default=3)
    crawl_parser.set_defaults(func=crawl)
    validate_packages_parser = subparsers.add_parser("validate-packages")
    validate_packages_parser.add_argument("--include", default=None)
    validate_packages_parser.set_defaults(func=validate_packages)
    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--include", default=None)
    summary_parser.set_defaults(func=summary)
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
