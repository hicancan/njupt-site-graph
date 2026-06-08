from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs" / "site_registry.json"


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
    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--include", default=None)
    summary_parser.set_defaults(func=summary)
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
