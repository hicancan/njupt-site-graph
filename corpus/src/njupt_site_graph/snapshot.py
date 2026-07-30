from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, BinaryIO, Iterable, Iterator
from urllib.parse import urlsplit, urlunsplit

import zstandard
from sitegraph.package import validate_site_package
from sites.registry import SiteRegistration, load_site_registry


FORMAT = "njupt-corpus-snapshot"
REGISTRY_RELATIVE_PATH = Path("sites/registry.json")
ARTIFACT_NAMES = ("documents.jsonl.zst", "attachments.jsonl.zst", "links.jsonl.zst")
WEBPLUS_ARTICLE_PATH = re.compile(
    r"/c\d+a(?P<article_id>\d+)/page\.(?:htm|psp)$",
    re.IGNORECASE,
)
WEBPLUS_LIST_PATH = re.compile(
    r"/list(?P<page>\d*)\.(?:htm|psp)$",
    re.IGNORECASE,
)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _canonical_url(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parts = urlsplit(text)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host = f"{host}:{port}"
    path = parts.path or "/"
    return urlunsplit((scheme, host, path, parts.query, ""))


def _stable_id(kind: str, source_id: str, identity: str) -> str:
    digest = hashlib.sha256(
        f"{kind}\0{source_id}\0{identity}".encode("utf-8")
    ).hexdigest()[:24]
    return f"{source_id}-{kind}-{digest}"


def _preferred_page_url(url: str) -> tuple[int, int, int, int, str]:
    path = urlsplit(url).path.lower()
    list_match = WEBPLUS_LIST_PATH.search(path)
    list_page = (
        int(list_match.group("page"))
        if list_match and list_match.group("page")
        else 1
    )
    return (
        int(path.endswith(".psp")),
        int(path.startswith("/_s")),
        list_page,
        len(path),
        url,
    )


def _optional_date(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as error:
        raise ValueError(f"invalid ISO date: {text}") from error


def _best_label(values: Iterable[Any]) -> str:
    labels = {_clean_text(value) for value in values}
    labels.discard("")
    if not labels:
        raise ValueError("cannot select a label from empty source values")

    def score(label: str) -> tuple[int, int, str]:
        meaningful = sum(character.isalnum() for character in label)
        return (
            meaningful,
            min(len(label), 160),
            label,
        )

    return max(labels, key=score)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def _json_line(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


@contextmanager
def _zstd_lines(path: Path) -> Iterator[BinaryIO]:
    compressor = zstandard.ZstdCompressor(level=10)
    with path.open("wb") as raw:
        with compressor.stream_writer(raw, closefd=False) as compressed:
            yield compressed


def _artifact(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def _site_package(
    packages_root: Path,
    registration: SiteRegistration,
) -> dict[str, Any]:
    root = (packages_root / registration.id / "index").resolve()
    validate_site_package(root, expected_site_id=registration.id)
    site = _read_json(root / "site.json")
    sections = _read_json(root / "sections.json")
    return {
        "root": root,
        "site": site,
        "sections": sections,
        "details": list(_read_jsonl(root / "detail_pages.jsonl")),
        "attachments": list(_read_jsonl(root / "attachments.jsonl")),
        "external_links": list(_read_jsonl(root / "external_links.jsonl")),
        "edges": list(_read_jsonl(root / "edges.jsonl")),
    }


def _section_maps(package: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    by_id: dict[str, dict[str, Any]] = {}
    names: dict[str, str] = {}
    for section in package["sections"]:
        if not isinstance(section, dict):
            raise ValueError("SitePackage section must be an object")
        section_id = _clean_text(section.get("section_id"))
        section_name = _clean_text(section.get("name"))
        if not section_id or not section_name:
            raise ValueError("SitePackage section requires section_id and name")
        if section_id in by_id:
            raise ValueError(f"duplicate SitePackage section: {section_id}")
        by_id[section_id] = section
        names[section_id] = section_name
    return by_id, names


def _site_identity(registry_id: str, site: dict[str, Any]) -> tuple[str, str]:
    source_id = _clean_text(site.get("site_id"))
    source_name = _clean_text(site.get("name"))
    if source_id != registry_id or not source_name:
        raise ValueError(f"invalid SitePackage identity for {registry_id}")
    return source_id, source_name


def _attachment_record(
    source_id: str,
    item: dict[str, Any],
    *,
    parent_id: str | None,
    parent_url: str | None,
    section: str | None,
) -> dict[str, Any]:
    url = _canonical_url(item.get("url"))
    name = _clean_text(item.get("name"))
    if not url:
        raise ValueError(f"{source_id} contains an attachment without a URL")
    if not name:
        raise ValueError(f"{source_id} contains an attachment without a name: {url}")
    identity = f"{parent_id or ''}\0{url}"
    return {
        "id": _stable_id("attachment", source_id, identity),
        "source": source_id,
        "url": url,
        "name": name,
        "extension": _clean_text(item.get("extension")).lower() or None,
        "parent_id": parent_id,
        "parent_url": parent_url if parent_id else None,
        "section": section,
    }


def _link_record(source_id: str, item: dict[str, Any], kind: str) -> dict[str, Any]:
    url = _canonical_url(item.get("url") or item.get("to_url"))
    label = _clean_text(item.get("label") or item.get("anchor_text")) or None
    from_url = _canonical_url(item.get("source_url") or item.get("from_url")) or None
    category = _clean_text(item.get("category") or item.get("target_type")) or None
    identity = "\0".join((from_url or "", url, label or "", category or ""))
    return {
        "id": _stable_id(kind, source_id, identity),
        "source": source_id,
        "url": url,
        "label": label,
        "kind": kind,
        "from_url": from_url,
        "category": category,
    }


def _read_zstd_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("rb") as raw:
        with zstandard.ZstdDecompressor().stream_reader(raw) as compressed:
            for line_number, line in enumerate(
                compressed.read().decode("utf-8").splitlines(),
                start=1,
            ):
                if not line:
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number} must be a JSON object")
                rows.append(value)
    return rows


def _unique_rows(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = _clean_text(row.get("id"))
        if not identity:
            raise ValueError(f"{label} contains an empty id")
        if identity in by_id:
            raise ValueError(f"{label} contains duplicate id: {identity}")
        by_id[identity] = row
    return by_id


def _snapshot_id(
    counts: dict[str, int],
    sources: list[dict[str, Any]],
    artifacts: dict[str, dict[str, Any]],
) -> str:
    identity = {
        "format": FORMAT,
        "counts": counts,
        "sources": sources,
        "artifacts": artifacts,
    }
    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_corpus_snapshot(root: Path) -> dict[str, Any]:
    expected_files = {*ARTIFACT_NAMES, "manifest.json"}
    present_files = {path.name for path in root.iterdir() if path.is_file()}
    if present_files != expected_files:
        raise ValueError(
            "NjuptCorpusSnapshot files do not match the current format; "
            f"missing={sorted(expected_files - present_files)}, "
            f"extra={sorted(present_files - expected_files)}"
        )

    manifest = _read_json(root / "manifest.json")
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"format", "snapshot_id", "counts", "sources", "artifacts"}
        or manifest.get("format") != FORMAT
        or not isinstance(manifest.get("counts"), dict)
        or set(manifest["counts"]) != {"sites", "documents", "attachments", "links"}
        or not isinstance(manifest.get("sources"), list)
        or not isinstance(manifest.get("artifacts"), dict)
        or set(manifest["artifacts"]) != set(ARTIFACT_NAMES)
    ):
        raise ValueError("incompatible NjuptCorpusSnapshot manifest")

    for name in ARTIFACT_NAMES:
        artifact = manifest["artifacts"][name]
        if (
            not isinstance(artifact, dict)
            or set(artifact) != {"path", "bytes", "sha256"}
            or artifact.get("path") != name
        ):
            raise ValueError(f"invalid corpus artifact metadata: {name}")
        actual = _artifact(root / name)
        if artifact != actual:
            raise ValueError(f"corpus artifact identity mismatch: {name}")
    if manifest.get("snapshot_id") != _snapshot_id(
        manifest["counts"],
        manifest["sources"],
        manifest["artifacts"],
    ):
        raise ValueError("corpus snapshot identity mismatch")

    source_rows = manifest["sources"]
    source_names: dict[str, str] = {}
    declared_counts: dict[str, dict[str, int]] = {}
    for source in source_rows:
        if (
            not isinstance(source, dict)
            or set(source) != {"id", "name", "counts"}
            or not isinstance(source.get("counts"), dict)
            or set(source["counts"]) != {"documents", "attachments", "links"}
        ):
            raise ValueError("invalid corpus source metadata")
        source_id = _clean_text(source.get("id"))
        source_name = _clean_text(source.get("name"))
        if not source_id or not source_name:
            raise ValueError("corpus source id and name must not be empty")
        if source_id in source_names:
            raise ValueError(f"duplicate corpus source: {source_id}")
        source_names[source_id] = source_name
        declared_counts[source_id] = source["counts"]
    if manifest["counts"]["sites"] != len(source_names):
        raise ValueError("corpus site count does not match sources")

    documents = _read_zstd_jsonl(root / "documents.jsonl.zst")
    attachments = _read_zstd_jsonl(root / "attachments.jsonl.zst")
    links = _read_zstd_jsonl(root / "links.jsonl.zst")
    documents_by_id = _unique_rows(documents, "documents")
    attachments_by_id = _unique_rows(attachments, "attachments")
    _unique_rows(links, "links")

    document_fields = {
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
    attachment_fields = {
        "id",
        "source",
        "url",
        "name",
        "extension",
        "parent_id",
        "parent_url",
        "section",
    }
    link_fields = {
        "id",
        "source",
        "url",
        "label",
        "kind",
        "from_url",
        "category",
    }
    document_keys: set[tuple[str, str, str]] = set()
    document_attachment_ids: dict[str, str] = {}
    actual_counts = {
        source_id: {"documents": 0, "attachments": 0, "links": 0}
        for source_id in source_names
    }

    for document in documents:
        if set(document) != document_fields:
            raise ValueError(f"invalid NjuptDocument fields: {document.get('id')}")
        source_id = _clean_text(document.get("source"))
        url = _canonical_url(document.get("url"))
        kind = _clean_text(document.get("kind"))
        if source_id not in source_names:
            raise ValueError(f"document has unknown source: {source_id}")
        if (
            not url
            or url != document["url"]
            or not _clean_text(document.get("title"))
            or kind not in {"page", "attachment", "external"}
            or not isinstance(document.get("content"), str)
            or not isinstance(document.get("tags"), list)
            or not isinstance(document.get("attachment_ids"), list)
            or any(
                value is not None and not isinstance(value, str)
                for value in (
                    document.get("published_at"),
                    document.get("updated_at"),
                    document.get("section"),
                )
            )
            or any(
                not isinstance(tag, str) or not tag
                for tag in document["tags"]
            )
            or document["tags"] != sorted(set(document["tags"]))
            or _optional_date(document.get("published_at"))
            != document.get("published_at")
            or _optional_date(document.get("updated_at"))
            != document.get("updated_at")
        ):
            raise ValueError(f"invalid NjuptDocument: {document.get('id')}")
        expected_document_id = (
            _stable_id("document", source_id, url)
            if kind == "page"
            else _stable_id("external", source_id, f"{url}\0{document['title']}")
            if kind == "external"
            else document["id"]
        )
        if document["id"] != expected_document_id:
            raise ValueError(f"invalid document identity: {document['id']}")
        document_key = (
            source_id,
            kind,
            url if kind != "external" else f"{url}\0{document['title']}",
        )
        if document_key in document_keys:
            raise ValueError(f"duplicate document source/kind/url: {document_key}")
        document_keys.add(document_key)
        actual_counts[source_id]["documents"] += 1
        for attachment_id in document["attachment_ids"]:
            if (
                not isinstance(attachment_id, str)
                or not attachment_id
                or attachment_id in document_attachment_ids
            ):
                raise ValueError(f"invalid document attachment id: {document['id']}")
            document_attachment_ids[attachment_id] = document["id"]

    for attachment in attachments:
        if set(attachment) != attachment_fields:
            raise ValueError(f"invalid attachment fields: {attachment.get('id')}")
        source_id = _clean_text(attachment.get("source"))
        if source_id not in source_names:
            raise ValueError(f"attachment has unknown source: {source_id}")
        if (
            not _canonical_url(attachment.get("url"))
            or _canonical_url(attachment["url"]) != attachment["url"]
            or not _clean_text(attachment.get("name"))
            or (
                attachment.get("extension") is not None
                and (
                    not isinstance(attachment["extension"], str)
                    or attachment["extension"] != attachment["extension"].lower()
                )
            )
            or (
                attachment.get("section") is not None
                and not isinstance(attachment["section"], str)
            )
        ):
            raise ValueError(f"invalid attachment: {attachment.get('id')}")
        expected_attachment_id = _stable_id(
            "attachment",
            source_id,
            f"{attachment.get('parent_id') or ''}\0{attachment['url']}",
        )
        if attachment["id"] != expected_attachment_id:
            raise ValueError(f"invalid attachment identity: {attachment['id']}")
        owner_id = document_attachment_ids.get(attachment["id"])
        if owner_id is None:
            raise ValueError(f"attachment is not referenced by a document: {attachment['id']}")
        parent_id = attachment.get("parent_id")
        if parent_id is None:
            owner = documents_by_id.get(attachment["id"])
            if (
                owner is None
                or owner["kind"] != "attachment"
                or owner["url"] != attachment["url"]
                or owner_id != owner["id"]
                or attachment.get("parent_url") is not None
            ):
                raise ValueError(f"orphan attachment document mismatch: {attachment['id']}")
        else:
            parent = documents_by_id.get(parent_id)
            if (
                parent is None
                or parent["kind"] != "page"
                or owner_id != parent_id
                or attachment.get("parent_url") != parent["url"]
            ):
                raise ValueError(f"attachment parent mismatch: {attachment['id']}")
        actual_counts[source_id]["attachments"] += 1

    if set(document_attachment_ids) != set(attachments_by_id):
        raise ValueError("document attachment ids do not match attachment rows")

    for link in links:
        if set(link) != link_fields:
            raise ValueError(f"invalid link fields: {link.get('id')}")
        source_id = _clean_text(link.get("source"))
        if (
            source_id not in source_names
            or link.get("kind") not in {"external", "edge"}
            or not _canonical_url(link.get("url"))
            or _canonical_url(link["url"]) != link["url"]
            or (
                link.get("label") is not None
                and not _clean_text(link.get("label"))
            )
            or (
                link.get("from_url") is not None
                and (
                    not isinstance(link["from_url"], str)
                    or _canonical_url(link["from_url"]) != link["from_url"]
                )
            )
            or (
                link.get("category") is not None
                and not _clean_text(link.get("category"))
            )
        ):
            raise ValueError(f"invalid link: {link.get('id')}")
        expected_link_id = _stable_id(
            link["kind"],
            source_id,
            "\0".join(
                (
                    link.get("from_url") or "",
                    link["url"],
                    link.get("label") or "",
                    link.get("category") or "",
                )
            ),
        )
        if link["id"] != expected_link_id:
            raise ValueError(f"invalid link identity: {link['id']}")
        actual_counts[source_id]["links"] += 1

    actual_totals = {
        "sites": len(source_names),
        "documents": len(documents),
        "attachments": len(attachments),
        "links": len(links),
    }
    if manifest["counts"] != actual_totals:
        raise ValueError("corpus manifest totals do not match artifact rows")
    if declared_counts != actual_counts:
        raise ValueError("corpus source counts do not match artifact rows")
    return manifest


def export_corpus_snapshot(
    repo: Path,
    packages_root: Path,
    output: Path,
) -> dict[str, Any]:
    registry = sorted(
        load_site_registry(repo / REGISTRY_RELATIVE_PATH),
        key=lambda registration: registration.id,
    )
    packages_root = packages_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    allowed_output_files = {*ARTIFACT_NAMES, "manifest.json"}
    extra_files = {
        path.name
        for path in output.iterdir()
        if path.is_file() and path.name not in allowed_output_files
    }
    extra_directories = {path.name for path in output.iterdir() if path.is_dir()}
    if extra_files or extra_directories:
        raise ValueError(
            "corpus output contains unrelated files; "
            f"files={sorted(extra_files)}, directories={sorted(extra_directories)}"
        )
    for name in allowed_output_files:
        target = output / name
        if target.exists():
            target.unlink()

    counts = {"sites": 0, "documents": 0, "attachments": 0, "links": 0}
    source_rows: list[dict[str, Any]] = []

    with (
        _zstd_lines(output / "documents.jsonl.zst") as documents_out,
        _zstd_lines(output / "attachments.jsonl.zst") as attachments_out,
        _zstd_lines(output / "links.jsonl.zst") as links_out,
    ):
        for registration in registry:
            package = _site_package(packages_root, registration)
            source_id, source_name = _site_identity(registration.id, package["site"])
            _sections_by_id, section_names = _section_maps(package)
            details_by_url: dict[str, tuple[str, str | None, str]] = {}
            page_documents: dict[str, dict[str, Any]] = {}

            for page in package["details"]:
                url = _canonical_url(page.get("url"))
                title = _clean_text(page.get("title"))
                if not url:
                    raise ValueError(f"{source_id} contains a detail page without a URL")
                if not title:
                    raise ValueError(f"{source_id} contains a detail page without a title: {url}")
                document_id = _stable_id("document", source_id, url)
                if document_id in page_documents:
                    raise ValueError(f"{source_id} contains duplicate detail URL: {url}")
                section_id = _clean_text(page.get("section_id"))
                section = section_names.get(section_id)
                details_by_url[url] = (document_id, section, url)
                tags = sorted(
                    {
                        text
                        for value in page.get("headings") or []
                        if (text := _clean_text(value))
                    }
                )
                page_documents[document_id] = {
                    "id": document_id,
                    "source": source_id,
                    "url": url,
                    "title": title,
                    "content": _clean_text(page.get("content_text")),
                    "published_at": _optional_date(page.get("published_at")),
                    "updated_at": _optional_date(page.get("updated_at")),
                    "section": section,
                    "kind": "page",
                    "tags": tags,
                    "attachment_ids": [],
                }
            webplus_aliases: dict[str, list[dict[str, Any]]] = {}
            for document_id, document in page_documents.items():
                article_match = WEBPLUS_ARTICLE_PATH.search(
                    urlsplit(document["url"]).path
                )
                if article_match:
                    webplus_aliases.setdefault(
                        article_match.group("article_id"),
                        [],
                    ).append(document)

            alias_groups: list[list[dict[str, Any]]] = []
            for candidates in webplus_aliases.values():
                semantics = {
                    (
                        document["title"],
                        document["content"],
                        document["published_at"],
                        document["updated_at"],
                        document["kind"],
                        tuple(document["tags"]),
                    )
                    for document in candidates
                }
                if len(candidates) > 1 and len(semantics) == 1:
                    alias_groups.append(candidates)

            for candidates in alias_groups:
                canonical = min(
                    candidates,
                    key=lambda document: _preferred_page_url(document["url"]),
                )
                for document in candidates:
                    details_by_url[document["url"]] = (
                        canonical["id"],
                        canonical["section"],
                        canonical["url"],
                    )
                    if document["id"] != canonical["id"]:
                        page_documents.pop(document["id"])

            attachment_rows: dict[str, dict[str, Any]] = {}
            for item in package["attachments"]:
                parent_url = _canonical_url(item.get("parent_url"))
                parent = details_by_url.get(parent_url)
                record = _attachment_record(
                    source_id,
                    item,
                    parent_id=parent[0] if parent else None,
                    parent_url=parent[2] if parent else None,
                    section=parent[1] if parent else None,
                )
                existing = attachment_rows.get(record["id"])
                if existing is None:
                    attachment_rows[record["id"]] = record
                    continue
                extensions = {
                    value for value in (existing["extension"], record["extension"]) if value
                }
                if len(extensions) > 1:
                    raise ValueError(
                        f"conflicting attachment extensions for {record['url']}: "
                        f"{sorted(extensions)}"
                    )
                existing["name"] = _best_label(
                    (existing["name"], record["name"]),
                )
                existing["extension"] = next(iter(extensions), None)

            for attachment in attachment_rows.values():
                parent_id = attachment["parent_id"]
                if parent_id is not None:
                    page_documents[parent_id]["attachment_ids"].append(attachment["id"])
            for document in page_documents.values():
                document["attachment_ids"].sort()

            orphan_documents: dict[str, dict[str, Any]] = {}
            for attachment in attachment_rows.values():
                if attachment["parent_id"] is not None:
                    continue
                orphan_documents[attachment["id"]] = {
                    "id": attachment["id"],
                    "source": source_id,
                    "url": attachment["url"],
                    "title": attachment["name"],
                    "content": "",
                    "published_at": None,
                    "updated_at": None,
                    "section": attachment["section"],
                    "kind": "attachment",
                    "tags": [attachment["extension"]] if attachment["extension"] else [],
                    "attachment_ids": [attachment["id"]],
                }

            link_rows: dict[str, dict[str, Any]] = {}
            external_documents: dict[tuple[str, str], set[str]] = {}
            for item in package["external_links"]:
                link = _link_record(source_id, item, "external")
                if not link["url"]:
                    raise ValueError(f"{source_id} contains an external link without a URL")
                existing_link = link_rows.get(link["id"])
                if existing_link is not None and existing_link != link:
                    raise ValueError(f"link identity collision: {link['id']}")
                link_rows[link["id"]] = link
                if link["label"] is None:
                    continue
                categories = external_documents.setdefault(
                    (link["url"], link["label"]),
                    set(),
                )
                if link["category"]:
                    categories.add(link["category"])

            for item in package["edges"]:
                link = _link_record(source_id, item, "edge")
                if not link["url"]:
                    raise ValueError(f"{source_id} contains an edge without a target URL")
                existing_link = link_rows.get(link["id"])
                if existing_link is not None and existing_link != link:
                    raise ValueError(f"link identity collision: {link['id']}")
                link_rows[link["id"]] = link

            external_document_rows: dict[str, dict[str, Any]] = {}
            for (url, title), categories in external_documents.items():
                document_id = _stable_id(
                    "external",
                    source_id,
                    f"{url}\0{title}",
                )
                external_document_rows[document_id] = {
                    "id": document_id,
                    "source": source_id,
                    "url": url,
                    "title": title,
                    "content": "",
                    "published_at": None,
                    "updated_at": None,
                    "section": None,
                    "kind": "external",
                    "tags": sorted(categories),
                    "attachment_ids": [],
                }

            documents = sorted(
                [
                    *page_documents.values(),
                    *orphan_documents.values(),
                    *external_document_rows.values(),
                ],
                key=lambda item: item["id"],
            )
            attachments = sorted(attachment_rows.values(), key=lambda item: item["id"])
            links = sorted(link_rows.values(), key=lambda item: item["id"])
            for document in documents:
                documents_out.write(_json_line(document))
            for attachment in attachments:
                attachments_out.write(_json_line(attachment))
            for link in links:
                links_out.write(_json_line(link))

            source_counts = {
                "documents": len(documents),
                "attachments": len(attachments),
                "links": len(links),
            }
            for key in ("documents", "attachments", "links"):
                counts[key] += source_counts[key]
            counts["sites"] += 1
            source_rows.append(
                {"id": source_id, "name": source_name, "counts": source_counts}
            )

    artifacts = {name: _artifact(output / name) for name in ARTIFACT_NAMES}
    manifest = {
        "format": FORMAT,
        "snapshot_id": _snapshot_id(counts, source_rows, artifacts),
        "counts": counts,
        "sources": source_rows,
        "artifacts": artifacts,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return validate_corpus_snapshot(output)
