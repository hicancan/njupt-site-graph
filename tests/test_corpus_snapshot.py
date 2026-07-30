from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import zstandard

from njupt_site_graph import export_corpus_snapshot, validate_corpus_snapshot
from sitegraph.model import SITE_PACKAGE_FILES, SITE_PACKAGE_FORMAT
from sites.registry import REGISTRY_FORMAT


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_zstd_jsonl(path: Path) -> list[dict]:
    with path.open("rb") as raw:
        with zstandard.ZstdDecompressor().stream_reader(raw) as compressed:
            text = compressed.read().decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line]


def _seal_site_package_fixture(package: Path) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = {}
    for name in SITE_PACKAGE_FILES:
        if name == "manifest.json":
            continue
        content = (package / name).read_bytes()
        artifacts[name] = {
            "path": name,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    identity = hashlib.sha256()
    identity.update(SITE_PACKAGE_FORMAT.encode())
    identity.update(b"\0")
    identity.update(manifest["site_id"].encode())
    for name, artifact in artifacts.items():
        identity.update(b"\0")
        identity.update(name.encode())
        identity.update(b"\0")
        identity.update(str(artifact["bytes"]).encode())
        identity.update(b"\0")
        identity.update(artifact["sha256"].encode())
    manifest["package_id"] = identity.hexdigest()
    manifest["artifacts"] = artifacts
    _write_json(manifest_path, manifest)


def test_export_corpus_snapshot(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    packages_root = tmp_path / "packages"
    package = packages_root / "demo/index"
    package.mkdir(parents=True)
    _write_json(
        repo / "sites/registry.json",
        {
            "version": REGISTRY_FORMAT,
            "sites": [
                {
                    "id": "demo",
                    "config": "sites/demo/site.yaml",
                }
            ],
        },
    )
    _write_json(
        package / "manifest.json",
        {
            "format": "static-site-package-v3",
            "site_id": "demo",
            "started_at": "2026-07-29T00:00:00Z",
            "finished_at": "2026-07-29T00:00:01Z",
                "totals": {
                    "sections": 1,
                    "nav_nodes": 0,
                    "homepage_modules": 0,
                    "list_pages": 0,
                    "detail_pages": 5,
                    "empty_content": 0,
                    "unrecognized_page_type": 0,
                    "attachments": 4,
                    "external_links": 2,
                    "edges": 1,
                },
            "errors": [],
        },
    )
    _write_json(
        package / "site.json",
        {
            "site_id": "demo",
            "name": "演示站点",
            "base_url": "https://example.test/",
            "domain": "example.test",
        },
    )
    _write_json(
        package / "sections.json",
        [
            {
                "section_id": "notice",
                "site_id": "demo",
                "name": "通知公告",
                "url": "https://example.test/notices/",
                "section_type": "list",
                "nav_path": ["通知公告"],
                "crawlable": True,
            }
        ],
    )
    _write_json(package / "nav_tree.json", {"site_id": "demo", "nodes": []})
    _write_json(package / "homepage_modules.json", {"site_id": "demo", "modules": []})
    _write_jsonl(package / "list_pages.jsonl", [])
    _write_jsonl(
        package / "detail_pages.jsonl",
        [
            {
                "page_id": "page-a",
                    "site_id": "demo",
                    "url": "https://example.test/a#fragment",
                    "page_type": "detail_article_page",
                    "status": "ok",
                "title": "测试通知",
                "content_text": "  正文\n内容  ",
                "section_id": "notice",
                "published_at": "2026-07-29",
                "headings": ["招生"],
            },
            {
                "page_id": "page-alias-html",
                "site_id": "demo",
                "url": "https://example.test/2026/0729/c1a123/page.htm",
                "page_type": "detail_article_page",
                "status": "ok",
                "title": "别名通知",
                "content_text": "相同正文",
                "section_id": "notice",
                "published_at": "2026-07-29",
                "headings": ["招生"],
            },
            {
                "page_id": "page-alias-psp",
                "site_id": "demo",
                "url": "https://example.test/2026/0729/c2a123/page.psp",
                "page_type": "detail_article_page",
                "status": "ok",
                "title": "别名通知",
                "content_text": "相同正文",
                "section_id": "notice",
                "published_at": "2026-07-29",
                "headings": ["招生"],
            },
            {
                "page_id": "section-content-a",
                "site_id": "demo",
                "url": "https://example.test/service/a.htm",
                "page_type": "section_content_page",
                "status": "ok",
                "title": "办事入口",
                "content_text": "相同栏目正文",
                "section_id": "notice",
                "published_at": None,
                "headings": ["服务"],
            },
            {
                "page_id": "section-content-b",
                "site_id": "demo",
                "url": "https://example.test/service/b.htm",
                "page_type": "section_content_page",
                "status": "ok",
                "title": "办事入口",
                "content_text": "相同栏目正文",
                "section_id": "notice",
                "published_at": None,
                "headings": ["服务"],
            },
        ],
    )
    _write_jsonl(
        package / "attachments.jsonl",
        [
            {
                "attachment_id": "attachment-a",
                "url": "https://example.test/a.pdf",
                "name": "附件",
                "extension": "pdf",
                "parent_url": "https://example.test/a",
            },
            {
                "attachment_id": "attachment-a-label",
                "url": "https://example.test/a.pdf",
                "name": "完整附件名称.pdf",
                "extension": "pdf",
                "parent_url": "https://example.test/a",
            },
            {
                "attachment_id": "attachment-alias-html",
                "url": "https://example.test/alias.pdf",
                "name": "别名附件.pdf",
                "extension": "pdf",
                "parent_url": "https://example.test/2026/0729/c1a123/page.htm",
            },
            {
                "attachment_id": "attachment-alias-psp",
                "url": "https://example.test/alias.pdf",
                "name": "别名附件.pdf",
                "extension": "pdf",
                "parent_url": "https://example.test/2026/0729/c2a123/page.psp",
            },
        ],
    )
    _write_jsonl(
        package / "external_links.jsonl",
        [
            {
                "external_id": "external-a",
                "url": "https://external.test/",
                "label": "外部系统",
                "source_url": "https://example.test/a",
                "source_section_id": "notice",
                "category": "system",
                "recorded_at": "2026-07-29T00:00:00Z",
            },
            {
                "external_id": "external-b",
                "url": "https://external.test/",
                "label": "外部系统入口",
                "source_url": "https://example.test/a",
                "source_section_id": "notice",
                "category": "system",
                "recorded_at": "2026-07-29T00:00:00Z",
            },
        ],
    )
    _write_jsonl(
        package / "edges.jsonl",
        [
            {
                "edge_id": "edge-a-b",
                "from_url": "https://example.test/a",
                "to_url": "https://example.test/b",
                "anchor_text": "下一页",
                "edge_type": "link",
            }
        ],
    )
    _seal_site_package_fixture(package)

    output = tmp_path / "snapshot"
    manifest = export_corpus_snapshot(repo, packages_root, output)

    documents = _read_zstd_jsonl(output / "documents.jsonl.zst")
    attachments = _read_zstd_jsonl(output / "attachments.jsonl.zst")
    links = _read_zstd_jsonl(output / "links.jsonl.zst")

    assert manifest["format"] == "njupt-corpus-snapshot"
    assert manifest["counts"] == {
        "sites": 1,
        "documents": 6,
        "attachments": 2,
        "links": 3,
    }
    notice_document = next(
        document for document in documents if document["title"] == "测试通知"
    )
    assert set(notice_document) == {
        "id",
        "source",
        "url",
        "title",
        "content",
        "published_at",
        "updated_at",
        "section",
        "kind",
        "tags",
        "attachment_ids",
    }
    assert notice_document["content"] == "正文 内容"
    notice_attachment = next(
        attachment
        for attachment in attachments
        if attachment["url"] == "https://example.test/a.pdf"
    )
    assert notice_attachment["parent_id"] == notice_document["id"]
    assert notice_attachment["name"] == "完整附件名称.pdf"
    assert notice_document["attachment_ids"] == [notice_attachment["id"]]
    alias_document = next(
        document for document in documents if document["title"] == "别名通知"
    )
    assert alias_document["url"] == (
        "https://example.test/2026/0729/c1a123/page.htm"
    )
    alias_attachment = next(
        attachment
        for attachment in attachments
        if attachment["url"] == "https://example.test/alias.pdf"
    )
    assert alias_attachment["parent_id"] == alias_document["id"]
    assert alias_attachment["parent_url"] == alias_document["url"]
    section_documents = [
        document for document in documents if document["title"] == "办事入口"
    ]
    assert {document["url"] for document in section_documents} == {
        "https://example.test/service/a.htm",
        "https://example.test/service/b.htm",
    }
    assert {link["kind"] for link in links} == {"external", "edge"}
    assert {document["title"] for document in documents if document["kind"] == "external"} == {
        "外部系统",
        "外部系统入口",
    }
    assert len({document["id"] for document in documents}) == len(documents)
    assert len({attachment["id"] for attachment in attachments}) == len(attachments)
    assert len({link["id"] for link in links}) == len(links)
    assert validate_corpus_snapshot(output) == manifest

    second_output = tmp_path / "snapshot-again"
    second_manifest = export_corpus_snapshot(repo, packages_root, second_output)
    assert second_manifest == manifest
    for name in ("documents.jsonl.zst", "attachments.jsonl.zst", "links.jsonl.zst"):
        assert (second_output / name).read_bytes() == (output / name).read_bytes()

    _write_json(package / "unexpected.json", {})
    with pytest.raises(ValueError, match="unexpected entries: unexpected.json"):
        export_corpus_snapshot(
            repo,
            packages_root,
            tmp_path / "rejected-snapshot",
        )
