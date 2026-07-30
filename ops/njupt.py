from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "sites" / "registry.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from njupt_site_graph import export_corpus_snapshot, validate_corpus_snapshot
from sitegraph.config import load_site_definition
from sitegraph.package import validate_site_package, write_site_package
from sitegraph.plugin import load_crawl_plugin
from sites.registry import load_site_registry


def run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def package_path(packages_root: Path, site_id: str) -> Path:
    return packages_root.resolve() / site_id / "index"


def validate_configs(args: argparse.Namespace) -> None:
    for site in load_site_registry(REGISTRY_PATH, args.include):
        run([sys.executable, "-m", "sitegraph.cli", "validate-config", site.config])


def _crawl_site(site: Any, args: argparse.Namespace) -> None:
    output_path = package_path(args.packages_root, site.id)
    if site.plugin:
        definition = load_site_definition(ROOT / site.config)
        plugin = load_crawl_plugin(site.plugin)
        package = plugin(
            definition=definition,
            config=definition.config,
            output_path=output_path,
            dry_run=args.dry_run,
            incremental=args.incremental,
        )
        if package is not None:
            write_site_package(
                package,
                output_path,
                incremental=args.incremental,
            )
        return
    command = [
        sys.executable,
        "-m",
        "sitegraph.cli",
        "crawl-site",
        site.config,
        "--out",
        str(output_path),
    ]
    if args.dry_run:
        command.append("--dry-run")
    if args.incremental:
        command.append("--incremental")
    run(command)


def crawl(args: argparse.Namespace) -> None:
    sites = load_site_registry(REGISTRY_PATH, args.include)
    workers = min(args.jobs, len(sites))
    if workers == 1:
        for site in sites:
            _crawl_site(site, args)
        return
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="site-crawl") as executor:
        list(executor.map(lambda site: _crawl_site(site, args), sites))


def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SystemExit(f"{path}:{line_number} must be an object")
            rows.append(row)
    return rows


def validate_packages(args: argparse.Namespace) -> None:
    for site in load_site_registry(REGISTRY_PATH, args.include):
        root = package_path(args.packages_root, site.id)
        try:
            validate_site_package(root, expected_site_id=site.id)
        except (ValueError, TypeError) as error:
            raise SystemExit(f"{site.id}: {error}") from error
        details = _read_json_lines(root / "detail_pages.jsonl")
        attachments = _read_json_lines(root / "attachments.jsonl")
        for row in details:
            if not str(row.get("url") or "").strip() or not str(row.get("title") or "").strip():
                raise SystemExit(f"{site.id} has a detail row without url/title")
        for row in attachments:
            if not str(row.get("url") or "").strip():
                raise SystemExit(f"{site.id} has an attachment row without url")


def summary(args: argparse.Namespace) -> None:
    rows: list[dict[str, Any]] = []
    for site in load_site_registry(REGISTRY_PATH, args.include):
        root = package_path(args.packages_root, site.id)
        manifest_path = root / "manifest.json"
        if not manifest_path.exists():
            rows.append({"site": site.id, "missing": str(manifest_path)})
            continue
        validate_site_package(root, expected_site_id=site.id)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        details = _read_json_lines(root / "detail_pages.jsonl")
        errors = manifest["errors"]
        rows.append(
            {
                "site": site.id,
                "pages": len(details),
                "attachments": len(_read_json_lines(root / "attachments.jsonl")),
                "empty_content": sum(not str(item.get("content_text") or "").strip() for item in details),
                "unrecognized_page_type": sum(not item.get("page_type") for item in details),
                "http_errors": sum("http" in str(item.get("phase") or "").lower() for item in errors),
                "parse_errors": sum("parse" in str(item.get("phase") or "").lower() for item in errors),
                "errors": len(errors),
                "started_at": manifest.get("started_at"),
                "finished_at": manifest["finished_at"],
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def export_corpus(args: argparse.Namespace) -> None:
    manifest = export_corpus_snapshot(
        ROOT,
        args.packages_root.resolve(),
        args.out.resolve(),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def validate_corpus(args: argparse.Namespace) -> None:
    manifest = validate_corpus_snapshot(args.snapshot.resolve())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="NJUPT site crawl and corpus operations")
    commands = parser.add_subparsers(dest="command", required=True)

    validate_config_parser = commands.add_parser("validate-configs")
    validate_config_parser.add_argument("--include")
    validate_config_parser.set_defaults(func=validate_configs)

    for name, dry_run in (("crawl", False), ("dry-run", True)):
        crawl_parser = commands.add_parser(name)
        crawl_parser.add_argument("--include")
        crawl_parser.add_argument(
            "--packages-root",
            type=Path,
            required=True,
        )
        crawl_parser.add_argument("--incremental", action="store_true")
        crawl_parser.add_argument("--jobs", type=int, choices=range(1, 16), default=1)
        crawl_parser.set_defaults(func=crawl, dry_run=dry_run)

    validate_package_parser = commands.add_parser("validate-packages")
    validate_package_parser.add_argument("--include")
    validate_package_parser.add_argument(
        "--packages-root",
        type=Path,
        required=True,
    )
    validate_package_parser.set_defaults(func=validate_packages)

    summary_parser = commands.add_parser("summary")
    summary_parser.add_argument("--include")
    summary_parser.add_argument("--packages-root", type=Path, required=True)
    summary_parser.set_defaults(func=summary)

    export_parser = commands.add_parser("export-corpus")
    export_parser.add_argument("--packages-root", type=Path, required=True)
    export_parser.add_argument("--out", type=Path, required=True)
    export_parser.set_defaults(func=export_corpus)

    validate_corpus_parser = commands.add_parser("validate-corpus")
    validate_corpus_parser.add_argument("snapshot", type=Path)
    validate_corpus_parser.set_defaults(func=validate_corpus)

    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
