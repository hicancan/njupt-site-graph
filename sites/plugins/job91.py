from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

import requests
from sitegraph import SiteDefinition, SitePackage
from sitegraph.fetch import DEFAULT_HEADERS
from sitegraph.util import now_iso, stable_id


SCHOOL_CODE = "10293"
SITE_KIND = "0"


def _text(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class Client:
    base_url: str
    timeout: int

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = requests.get(
                url,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(
                f"91job request failed: {url}?{urlencode(params or {})}: {exc}"
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("success") is not True
            or payload.get("code") != 200
        ):
            raise RuntimeError(
                f"91job returned an invalid response: "
                f"{json.dumps(payload, ensure_ascii=False)[:500]}"
            )
        return payload


def _columns(
    values: list[dict[str, Any]], parent: list[str] | None = None
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for value in values:
        name = _text(value.get("lmmc"))
        path = [*(parent or []), *([name] if name else [])]
        identifier = _text(value.get("lmid"))
        if not identifier or not name:
            raise RuntimeError("91job category requires lmid and lmmc")
        result.append(
            {
                "id": identifier,
                "name": name,
                "nav_path": path,
            }
        )
        children = value.get("model")
        if isinstance(children, list):
            result.extend(_columns(children, path))
    return result


def _item_key(item: dict[str, Any]) -> str:
    for key in ("xwid", "zphid", "xjhid", "dwid", "zwid", "companyId", "id"):
        if value := _text(item.get(key)):
            return f"{key}:{value}"
    raise RuntimeError("91job item has no stable business identity")


def _pages(
    client: Client,
    *,
    category: str,
    page_size: int,
    maximum: int,
    known_keys: set[str],
) -> tuple[list[tuple[int, list[dict[str, Any]]]], dict[str, Any]]:
    pages: list[tuple[int, list[dict[str, Any]]]] = []
    seen: set[tuple[str, ...]] = set()
    for page_number in range(1, maximum + 1):
        params: dict[str, Any] = {"lmid": category, "row": page_size}
        if page_number > 1:
            params["page"] = page_number
        values = client.get("/web/wsjysc/wzsy/getLbsj", params).get("result")
        if not isinstance(values, list):
            raise RuntimeError(
                f"91job category {category} page {page_number} is not a list"
            )
        keys = tuple(_item_key(item) for item in values)
        if not values:
            return pages, {"reason": "empty_page", "last_page": page_number}
        if page_number > 1 and keys in seen:
            return pages, {"reason": "duplicate_page", "last_page": page_number - 1}
        pages.append((page_number, values))
        seen.add(keys)
        if known_keys and all(key in known_keys for key in keys):
            return pages, {"reason": "known_page", "last_page": page_number}
        if len(values) < page_size:
            return pages, {"reason": "short_page", "last_page": page_number}
    return pages, {"reason": "page_limit", "last_page": maximum}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _known_item_keys(output_path: Path) -> set[str]:
    keys: set[str] = set()
    for row in _read_rows(output_path / "detail_pages.jsonl"):
        source_keys = row.get("source_keys")
        if isinstance(source_keys, list):
            keys.update(
                key
                for key in (_text(value) for value in source_keys)
                if ":" in key
            )
        url = str(row.get("url") or "")
        parsed = urlparse(url)
        identifier = unquote(parsed.path.rstrip("/").rsplit("/", 1)[-1])
        if not identifier:
            continue
        if "/job-fair/" in parsed.path:
            keys.add(f"zphid:{identifier}")
        elif "/news/" in parsed.path:
            keys.add(f"xwid:{identifier}")
        query = parse_qs(parsed.query)
        for name in ("xjhid", "dwid"):
            if values := query.get(name):
                if value := _text(values[0]):
                    keys.add(f"{name}:{value}")
    return keys


def _record(
    *,
    site_id: str,
    section_id: str,
    record_id: str,
    url: str,
    title: str,
    content: str,
    published_at: str | None,
    publisher: str,
    raw: dict[str, Any],
    source_keys: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "page_id": stable_id(site_id, record_id),
        "site_id": site_id,
        "section_id": section_id,
        "url": url,
        "page_type": "detail_article_page",
        "title": title,
        "publisher": publisher,
        "published_at": published_at,
        "updated_at": None,
        "content_text": content,
        "content_hash": stable_id(json.dumps(raw, ensure_ascii=False, sort_keys=True)),
        "status": "ok",
        "content_status": "normal_content" if content else "empty_content",
        "extraction_strategy": "job91_api",
        "headings": [],
        "inline_links": [],
        "inline_images": [],
        "attachment_count": 0,
        "source_keys": list(source_keys),
    }


def _records(
    *, base_url: str, site_id: str, section_id: str, item: dict[str, Any], index: int
) -> list[dict[str, Any]]:
    if "zphid" in item or "zphmc" in item:
        record_id = _text(item.get("zphid"))
        title = _text(item.get("zphmc"))
        if not record_id or not title:
            raise RuntimeError(
                f"91job fair {section_id}/{index} requires zphid and zphmc"
            )
        content = " ".join(
            part
            for part in (_text(item.get("gljg")), _text(item.get("jbcd")))
            if part
        )
        return [
            _record(
                site_id=site_id,
                section_id=section_id,
                record_id=record_id,
                url=f"{base_url}/sub-station/job-fair/{quote(record_id, safe='')}",
                title=title,
                content=content,
                published_at=_text(item.get("jbkssj")) or None,
                publisher=_text(item.get("gljg")) or "南京邮电大学",
                raw=item,
                source_keys=(f"zphid:{record_id}",),
            )
        ]

    if "xjhid" in item or "xjhmc" in item:
        record_id = _text(item.get("xjhid"))
        title = _text(item.get("xjhmc"))
        if not record_id or not title:
            raise RuntimeError(
                f"91job lecture {section_id}/{index} requires xjhid and xjhmc"
            )
        content = " ".join(
            part
            for part in (
                _text(item.get("xjxx")),
                _text(item.get("jbrq")),
                _text(item.get("kssj")),
                _text(item.get("jbdd")),
            )
            if part
        )
        query = urlencode({"xjhid": record_id, "xxdm": SCHOOL_CODE})
        return [
            _record(
                site_id=site_id,
                section_id=section_id,
                record_id=f"xjhid:{record_id}",
                url=f"{base_url}/sub-station/lectureDetail?{query}",
                title=title,
                content=content,
                published_at=_text(item.get("jbrq")) or None,
                publisher=_text(item.get("xjxx")) or "南京邮电大学",
                raw=item,
                source_keys=(f"xjhid:{record_id}",),
            )
        ]

    if "dwid" in item or "zpzw" in item:
        company_id = _text(item.get("dwid"))
        company_name = _text(item.get("dwmc"))
        positions = item.get("zpzw")
        if not company_id or not company_name or not isinstance(positions, list):
            raise RuntimeError(
                f"91job company {section_id}/{index} requires dwid, dwmc and zpzw"
            )
        if not positions:
            query = urlencode({"dwid": company_id, "xxdm": SCHOOL_CODE})
            return [
                _record(
                    site_id=site_id,
                    section_id=section_id,
                    record_id=f"dwid:{company_id}",
                    url=f"{base_url}/sub-station/companyDetails?{query}",
                    title=company_name,
                    content=_text(item.get("zzshsj")),
                    published_at=_text(item.get("zzshsj")) or None,
                    publisher=company_name,
                    raw=item,
                    source_keys=(f"dwid:{company_id}",),
                )
            ]
        records: list[dict[str, Any]] = []
        company_facts = {key: value for key, value in item.items() if key != "zpzw"}
        for position_index, position in enumerate(positions):
            if not isinstance(position, dict):
                raise RuntimeError(
                    f"91job position {section_id}/{index}/{position_index} must be an object"
                )
            position_id = _text(position.get("zpgwid"))
            title = _text(position.get("zwmc"))
            if not position_id or not title:
                raise RuntimeError(
                    f"91job position {section_id}/{index}/{position_index} "
                    "requires zpgwid and zwmc"
                )
            content = " ".join(
                part
                for part in (
                    company_name,
                    _text(position.get("gzdd")),
                    _text(position.get("xlyq")),
                    _text(position.get("yjnx")),
                    _text(position.get("zprs")),
                )
                if part
            )
            query = urlencode(
                {
                    "zpgwid": position_id,
                    "dwid": company_id,
                    "xxdm": SCHOOL_CODE,
                }
            )
            records.append(
                _record(
                    site_id=site_id,
                    section_id=section_id,
                    record_id=f"zpgwid:{position_id}",
                    url=f"{base_url}/sub-station/jobDetails?{query}",
                    title=title,
                    content=content,
                    published_at=_text(item.get("zzshsj")) or None,
                    publisher=company_name,
                    raw={"company": company_facts, "position": position},
                    source_keys=(
                        f"dwid:{company_id}",
                        f"zpgwid:{position_id}",
                    ),
                )
            )
        return records

    record_id = _text(item.get("xwid"))
    title = _text(item.get("xwbt"))
    if not record_id or not title:
        raise RuntimeError(
            f"91job news {section_id}/{index} requires xwid and xwbt"
        )
    content = " ".join(
        part
        for part in (
            _text(item.get("xwfbt")),
            _text(item.get("xwnr")),
            _text(item.get("xwbq")),
            _text(item.get("flbq")),
            _text(item.get("hdsj")),
            _text(item.get("hddd")),
        )
        if part
    )
    return [
        _record(
            site_id=site_id,
            section_id=section_id,
            record_id=record_id,
            url=_text(item.get("tzljdz"))
            or f"{base_url}/sub-station/news/{quote(record_id, safe='')}",
            title=title,
            content=content,
            published_at=_text(item.get("fbsj")) or None,
            publisher="南京邮电大学就业信息网",
            raw=item,
            source_keys=(f"xwid:{record_id}",),
        )
    ]


def crawl(
    *,
    definition: SiteDefinition,
    config: dict[str, Any],
    output_path: Path,
    dry_run: bool,
    incremental: bool,
) -> SitePackage | None:
    site_id = definition.id
    base_url = definition.base_url.rstrip("/")
    policy = config.get("crawl_policy", {})
    timeout = int(policy.get("timeout_seconds", 20))
    page_size = int(policy.get("job91_items_per_section", 120))
    maximum = int(policy.get("job91_max_pages_per_section", 40))
    category_workers = int(policy.get("job91_category_workers", 3))
    if dry_run:
        print(
            json.dumps(
                {"site_id": site_id, "base_url": base_url, "plugin": "job91"},
                ensure_ascii=False,
            )
        )
        return

    started_at = now_iso()
    known_keys = _known_item_keys(output_path) if incremental else set()
    client = Client(base_url, timeout)
    website_id = _text(
        client.get(
            "/web/wsjysc/wzsy/getWzid",
            {"xxdm": SCHOOL_CODE, "wzlx": SITE_KIND},
        ).get("result")
    )
    if not website_id:
        raise RuntimeError("91job website id is empty")
    raw_columns = client.get(
        "/web/wsjysc/wzsy/getXwlm", {"wzid": website_id}
    ).get("result")
    if not isinstance(raw_columns, list) or not raw_columns:
        raise RuntimeError("91job returned no categories")

    columns = _columns(raw_columns)
    workers = min(max(1, category_workers), len(columns))

    def fetch_category(column: dict[str, Any]):
        return _pages(
            client,
            category=column["id"],
            page_size=page_size,
            maximum=maximum,
            known_keys=known_keys,
        )

    if workers == 1:
        category_pages = [fetch_category(column) for column in columns]
    else:
        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="job91-category",
        ) as executor:
            category_pages = list(executor.map(fetch_category, columns))

    sections: list[dict[str, Any]] = []
    list_pages_by_url = (
        {
            row["url"]: row
            for row in _read_rows(output_path / "list_pages.jsonl")
        }
        if incremental
        else {}
    )
    detail_by_url = (
        {
            row["url"]: row
            for row in _read_rows(output_path / "detail_pages.jsonl")
        }
        if incremental
        else {}
    )
    edges_by_id = (
        {
            row["edge_id"]: row
            for row in _read_rows(output_path / "edges.jsonl")
        }
        if incremental
        else {}
    )
    errors: list[dict[str, Any]] = []
    for column, (pages, stop) in zip(columns, category_pages, strict=True):
        section_id = f"{site_id}_{stable_id(column['id'], length=12)}"
        section_url = (
            f"{base_url}/sub-station/list/{quote(column['id'], safe='')}"
        )
        sections.append(
            {
                "section_id": section_id,
                "site_id": site_id,
                "name": column["name"],
                "url": section_url,
                "section_type": "api_list",
                "nav_path": column["nav_path"],
                "crawlable": True,
                "business_tags": ["employment"],
                "source": "api_category",
            }
        )
        print(
            json.dumps(
                {
                    "site_id": site_id,
                    "section_id": section_id,
                    "source_category_id": column["id"],
                    "pages": len(pages),
                    "termination": stop["reason"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if stop["reason"] == "page_limit":
            errors.append(
                {
                    "phase": "pagination",
                    "section_id": section_id,
                    "message": f"reached configured page limit {maximum}",
                }
            )
        for page_number, items in pages:
            list_url = (
                section_url
                if page_number == 1
                else f"{section_url}?page={page_number}"
            )
            list_pages_by_url[list_url] = {
                "page_id": stable_id(site_id, list_url),
                "site_id": site_id,
                "section_id": section_id,
                "url": list_url,
                "page_type": "section_list_page",
                "status": "ok",
                "page_index": page_number,
                "item_count": len(items),
                "fetched_at": now_iso(),
            }
            for index, item in enumerate(items):
                records = _records(
                    base_url=base_url,
                    site_id=site_id,
                    section_id=section_id,
                    item=item,
                    index=(page_number - 1) * page_size + index,
                )
                for record in records:
                    detail_by_url[record["url"]] = record
                    edge = {
                        "edge_id": stable_id(list_url, record["url"]),
                        "from_url": list_url,
                        "to_url": record["url"],
                        "anchor_text": record["title"],
                        "edge_type": "api_list_item",
                        "target_type": "detail_article_page",
                        "same_domain": True,
                    }
                    edges_by_id[edge["edge_id"]] = edge

    nav_nodes = [
        {
            "node_id": stable_id(site_id, column["id"]),
            "site_id": site_id,
            "label": column["name"],
            "url": f"{base_url}/sub-station/list/{quote(column['id'], safe='')}",
            "nav_path": column["nav_path"],
            "depth": max(1, len(column["nav_path"])),
            "target_type": "section_list_page",
            "same_domain": True,
            "parent_id": None,
            "position": position,
        }
        for position, column in enumerate(columns)
    ]
    modules = [
        {
            "module_id": stable_id(site_id, column["id"], "module"),
            "site_id": site_id,
            "name": column["name"],
            "url": base_url,
            "list_url": f"{base_url}/sub-station/list/{quote(column['id'], safe='')}",
            "position": position,
            "source": "api_category",
        }
        for position, column in enumerate(columns)
    ]
    return SitePackage(
        definition=definition,
        started_at=started_at,
        nav_nodes=nav_nodes,
        homepage_modules=modules,
        sections=sections,
        list_pages_by_url=list_pages_by_url,
        detail_pages_by_url=detail_by_url,
        attachments_by_id={},
        external_links_by_id={},
        edges_by_id=edges_by_id,
        errors=errors,
    )
