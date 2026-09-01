from __future__ import annotations

import base64
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

import requests
import yaml
from sitegraph import SiteDefinition, SitePackage
from sitegraph.util import now_iso, stable_id


API_ROOT = "https://api.github.com"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
CONFIG_KEYS = {
    "owner",
    "repository",
    "ref",
    "article_roots",
    "attachment_roots",
    "article_extensions",
    "excluded_paths",
    "excluded_attachment_paths",
    "section_labels",
    "max_article_bytes",
}
FRONTMATTER_BOUNDARY = re.compile(r"^---\s*$", re.MULTILINE)
MDX_COMMENT = re.compile(r"\{/\*.*?\*/\}", re.DOTALL)
MDX_IMPORT = re.compile(r"^(?:import|export)\s+.*?$", re.MULTILINE)
JSX_TAG = re.compile(r"</?[A-Za-z][^>]*>", re.DOTALL)
MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
MARKDOWN_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any, name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise RuntimeError(f"github_repository.{name} must be a list")
    result = tuple(_text(item).strip("/") for item in value)
    if any(not item for item in result) or len(result) != len(set(result)):
        raise RuntimeError(f"github_repository.{name} contains an invalid path")
    return result


@dataclass(frozen=True)
class Settings:
    owner: str
    repository: str
    ref: str
    article_roots: tuple[str, ...]
    attachment_roots: tuple[str, ...]
    article_extensions: frozenset[str]
    excluded_paths: frozenset[str]
    excluded_attachment_paths: frozenset[str]
    section_labels: dict[str, str]
    max_article_bytes: int

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Settings":
        raw = config.get("github_repository")
        if not isinstance(raw, dict) or set(raw) != CONFIG_KEYS:
            unknown = sorted(set(raw or {}) - CONFIG_KEYS) if isinstance(raw, dict) else []
            missing = sorted(CONFIG_KEYS - set(raw or {})) if isinstance(raw, dict) else sorted(CONFIG_KEYS)
            raise RuntimeError(
                "github_repository must contain the current exact fields; "
                f"missing={missing}, unknown={unknown}"
            )
        owner = _text(raw["owner"])
        repository = _text(raw["repository"])
        ref = _text(raw["ref"])
        if not owner or not repository or not ref:
            raise RuntimeError("github_repository owner, repository and ref are required")
        extensions = frozenset(
            item.lower().lstrip(".")
            for item in _string_list(raw["article_extensions"], "article_extensions")
        )
        labels = raw["section_labels"]
        if not isinstance(labels, dict) or any(
            not _text(key) or not _text(value) for key, value in labels.items()
        ):
            raise RuntimeError("github_repository.section_labels must be a string map")
        maximum = raw["max_article_bytes"]
        if not isinstance(maximum, int) or maximum < 1 or maximum > 4 * 1024 * 1024:
            raise RuntimeError("github_repository.max_article_bytes is out of range")
        return cls(
            owner=owner,
            repository=repository,
            ref=ref,
            article_roots=_string_list(raw["article_roots"], "article_roots"),
            attachment_roots=_string_list(
                raw["attachment_roots"], "attachment_roots", allow_empty=True
            ),
            article_extensions=extensions,
            excluded_paths=frozenset(
                _string_list(raw["excluded_paths"], "excluded_paths", allow_empty=True)
            ),
            excluded_attachment_paths=frozenset(
                _string_list(
                    raw["excluded_attachment_paths"],
                    "excluded_attachment_paths",
                    allow_empty=True,
                )
            ),
            section_labels={_text(key): _text(value) for key, value in labels.items()},
            max_article_bytes=maximum,
        )


class GitHubClient:
    def __init__(self, timeout: int = 30, attempts: int = 4) -> None:
        self.timeout = timeout
        self.attempts = attempts
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "njupt-site-graph",
            }
        )
        if token := _text(os.environ.get("GITHUB_TOKEN")):
            self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{API_ROOT}/{path.lstrip('/')}"
        for attempt in range(self.attempts):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as error:
                if attempt + 1 == self.attempts:
                    raise RuntimeError(f"GitHub request failed: {url}: {error}") from error
                time.sleep(2**attempt)
                continue
            retryable = response.status_code in RETRYABLE_STATUS or (
                response.status_code == 403
                and response.headers.get("X-RateLimit-Remaining") == "0"
            )
            if retryable and attempt + 1 < self.attempts:
                time.sleep(2**attempt)
                continue
            try:
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as error:
                detail = response.text[:500]
                raise RuntimeError(
                    f"GitHub request failed: {url}: HTTP {response.status_code}: {detail}"
                ) from error
            if not isinstance(payload, dict):
                raise RuntimeError(f"GitHub response must be an object: {url}")
            return payload
        raise AssertionError("unreachable")

    def tree(self, settings: Settings) -> dict[str, Any]:
        ref = quote(settings.ref, safe="")
        return self.get(
            f"repos/{settings.owner}/{settings.repository}/git/trees/{ref}",
            params={"recursive": "1"},
        )

    def blob(self, settings: Settings, sha: str) -> bytes:
        payload = self.get(
            f"repos/{settings.owner}/{settings.repository}/git/blobs/{sha}"
        )
        if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
            raise RuntimeError(f"GitHub blob {sha} is not base64 encoded")
        try:
            encoded = "".join(payload["content"].split())
            return base64.b64decode(encoded, validate=True)
        except ValueError as error:
            raise RuntimeError(f"GitHub blob {sha} contains invalid base64") from error


def _under(path: str, roots: tuple[str, ...]) -> str | None:
    for root in roots:
        if path == root:
            return ""
        prefix = f"{root}/"
        if path.startswith(prefix):
            return path[len(prefix) :]
    return None


def _extension(path: str) -> str:
    return PurePosixPath(path).suffix.lower().lstrip(".")


def _article_path(path: str, settings: Settings) -> bool:
    return (
        path not in settings.excluded_paths
        and _under(path, settings.article_roots) is not None
        and _extension(path) in settings.article_extensions
    )


def _attachment_path(path: str, settings: Settings) -> bool:
    return (
        path not in settings.excluded_attachment_paths
        and _under(path, settings.attachment_roots) is not None
        and not _article_path(path, settings)
    )


def _frontmatter(source: str) -> tuple[dict[str, Any], str]:
    if not source.startswith("---"):
        return {}, source
    boundaries = list(FRONTMATTER_BOUNDARY.finditer(source))
    if len(boundaries) < 2 or boundaries[0].start() != 0:
        raise RuntimeError("unterminated Markdown frontmatter")
    raw = source[boundaries[0].end() : boundaries[1].start()]
    value = yaml.safe_load(raw) or {}
    if not isinstance(value, dict):
        raise RuntimeError("Markdown frontmatter must be an object")
    return value, source[boundaries[1].end() :]


def _plain_markdown(source: str) -> tuple[str, list[str]]:
    source = MDX_COMMENT.sub(" ", source)
    source = MDX_IMPORT.sub(" ", source)
    source = MARKDOWN_IMAGE.sub(r"\1", source)
    source = MARKDOWN_LINK.sub(r"\1", source)
    source = JSX_TAG.sub(" ", source)
    headings = [re.sub(r"[`*_]", "", item).strip() for item in MARKDOWN_HEADING.findall(source)]
    lines = [line.rstrip() for line in source.splitlines()]
    compact: list[str] = []
    blank = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if compact and not blank:
                compact.append("")
            blank = True
            continue
        compact.append(stripped)
        blank = False
    return "\n".join(compact).strip(), headings


def _article(blob: bytes, path: str) -> tuple[str, str, list[str]]:
    try:
        source = blob.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"GitHub article is not UTF-8: {path}") from error
    metadata, body = _frontmatter(source)
    content, headings = _plain_markdown(body)
    title = _text(metadata.get("title"))
    if not title and headings:
        title = headings[0]
    if not title:
        title = PurePosixPath(path).stem
    description = _text(metadata.get("description"))
    if description and description not in content:
        content = f"{description}\n\n{content}".strip()
    return title, content, headings


def _github_url(settings: Settings, kind: str, path: str = "") -> str:
    base = f"https://github.com/{settings.owner}/{settings.repository}/{kind}/{quote(settings.ref, safe='')}"
    return f"{base}/{quote(path, safe='/')}" if path else base


def _section(
    definition: SiteDefinition,
    settings: Settings,
    path: str,
) -> tuple[str, str, str]:
    relative = _under(path, settings.article_roots)
    if relative is None:
        raise AssertionError(path)
    key = relative.split("/", 1)[0] if "/" in relative else "_root"
    label = settings.section_labels.get(key, key if key != "_root" else definition.name)
    directory = str(PurePosixPath(path).parent)
    section_id = f"{definition.id}_{stable_id(key, length=12)}"
    return section_id, label, _github_url(settings, "tree", directory)


def _attachment_name(path: str, settings: Settings) -> str:
    relative = _under(path, settings.attachment_roots)
    if relative is None:
        raise AssertionError(path)
    return " · ".join(part for part in PurePosixPath(relative).parts if part)


def crawl(
    *,
    definition: SiteDefinition,
    config: dict[str, Any],
    output_path: Path,
    dry_run: bool,
    incremental: bool,
) -> SitePackage | None:
    del output_path, incremental
    settings = Settings.from_config(config)
    if dry_run:
        print(
            json.dumps(
                {
                    "site_id": definition.id,
                    "plugin": "github_repository",
                    "repository": f"{settings.owner}/{settings.repository}",
                    "ref": settings.ref,
                },
                ensure_ascii=False,
            )
        )
        return None

    client = GitHubClient()
    payload = client.tree(settings)
    if payload.get("truncated") is not False or not isinstance(payload.get("tree"), list):
        raise RuntimeError("GitHub recursive tree is missing or truncated")
    tree_sha = _text(payload.get("sha"))
    if not tree_sha:
        raise RuntimeError("GitHub recursive tree has no identity")
    entries: list[dict[str, Any]] = []
    paths: set[str] = set()
    for item in payload["tree"]:
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        path = _text(item.get("path"))
        sha = _text(item.get("sha"))
        size = item.get("size")
        if not path or not sha or not isinstance(size, int) or size < 0:
            raise RuntimeError("GitHub tree contains an invalid blob")
        if path in paths:
            raise RuntimeError(f"GitHub tree contains duplicate path: {path}")
        paths.add(path)
        entries.append({"path": path, "sha": sha, "size": size})
    entries.sort(key=lambda item: (item["path"].casefold(), item["path"]))

    sections_by_id: dict[str, dict[str, Any]] = {}
    details_by_url: dict[str, dict[str, Any]] = {}
    attachments_by_id: dict[str, dict[str, Any]] = {}
    for position, item in enumerate(entries):
        path = item["path"]
        if _article_path(path, settings):
            if item["size"] > settings.max_article_bytes:
                raise RuntimeError(
                    f"GitHub article exceeds {settings.max_article_bytes} bytes: {path}"
                )
            blob = client.blob(settings, item["sha"])
            if len(blob) != item["size"]:
                raise RuntimeError(f"GitHub blob size mismatch: {path}")
            title, content, headings = _article(blob, path)
            section_id, section_name, section_url = _section(definition, settings, path)
            sections_by_id.setdefault(
                section_id,
                {
                    "section_id": section_id,
                    "site_id": definition.id,
                    "name": section_name,
                    "url": section_url,
                    "section_type": "repository_directory",
                    "nav_path": [section_name],
                    "crawlable": True,
                    "business_tags": ["community" if not settings.attachment_roots else "materials"],
                },
            )
            url = _github_url(settings, "blob", path)
            details_by_url[url] = {
                "page_id": stable_id(definition.id, "github", path),
                "site_id": definition.id,
                "section_id": section_id,
                "url": url,
                "page_type": "repository_article",
                "title": title,
                "publisher": definition.name,
                "published_at": None,
                "updated_at": None,
                "content_text": content,
                "content_hash": item["sha"],
                "status": "ok",
                "content_status": "normal_content" if content else "empty_content",
                "extraction_strategy": "github_git_blob",
                "headings": headings,
                "inline_links": [],
                "inline_images": [],
                "attachment_count": 0,
                "source_keys": [f"tree:{tree_sha}", f"blob:{item['sha']}"],
            }
        elif _attachment_path(path, settings):
            url = _github_url(settings, "blob", path)
            attachment_id = stable_id(definition.id, "github-attachment", path)
            attachments_by_id[attachment_id] = {
                "attachment_id": attachment_id,
                "parent_url": definition.base_url,
                "name": _attachment_name(path, settings),
                "url": url,
                "extension": _extension(path),
                "position": position,
                "bytes": item["size"],
                "content_sha": item["sha"],
            }

    if not details_by_url:
        raise RuntimeError("GitHub repository produced no articles")
    return SitePackage(
        definition=definition,
        started_at=now_iso(),
        sections=sorted(sections_by_id.values(), key=lambda item: item["section_id"]),
        detail_pages_by_url=details_by_url,
        attachments_by_id=attachments_by_id,
        errors=[],
    )
