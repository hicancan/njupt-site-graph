from __future__ import annotations

import argparse
from pathlib import Path

from .snapshot import export_corpus_snapshot, validate_corpus_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="njupt-sitegraph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export-corpus",
        help="Export one NjuptCorpusSnapshot from local SitePackage directories.",
    )
    export_parser.add_argument("--repo", type=Path, default=Path.cwd())
    export_parser.add_argument("--packages-root", type=Path, required=True)
    export_parser.add_argument("--out", type=Path, required=True)
    validate_parser = subparsers.add_parser(
        "validate-corpus",
        help="Validate one current NjuptCorpusSnapshot.",
    )
    validate_parser.add_argument("snapshot", type=Path)

    args = parser.parse_args(argv)
    if args.command == "export-corpus":
        manifest = export_corpus_snapshot(
            args.repo.resolve(),
            args.packages_root.resolve(),
            args.out.resolve(),
        )
        print(
            f"exported {manifest['counts']['documents']} documents "
            f"from {manifest['counts']['sites']} sites to {args.out.resolve()}"
        )
        return 0
    if args.command == "validate-corpus":
        manifest = validate_corpus_snapshot(args.snapshot.resolve())
        print(
            f"valid {manifest['format']} {manifest['snapshot_id']} "
            f"with {manifest['counts']['documents']} documents"
        )
        return 0
    raise AssertionError(f"unhandled command: {args.command}")
