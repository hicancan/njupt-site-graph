from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

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
    for key in ("xwid", "zphid", "zwid", "companyId", "id"):
        if value := _text(item.get(key)):
            return f"{key}:{value}"
    raise RuntimeError("91job item has no stable business identity")


def _pages(
    client: Client, *, category: str, page_size: int, maximum: int
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
        if len(values) < page_size:
            return pages, {"reason": "short_page", "last_page": page_number}
    return pages, {"reason": "page_limit", "last_page": maximum}


def _record(
    *, base_url: str, site_id: str, section_id: str, item: dict[str, Any], index: int
) -> dict[str, Any]:
    fair = "zphid" in item or "zphmc" in item
    raw_id = _text(item.get("zphid" if fair else "xwid"))
    title = _text(item.get("zphmc" if fair else "xwbt"))
    if not raw_id or not title:
        raise RuntimeError(
            f"91job item {section_id}/{index} requires a stable id and title"
        )
    record_id = raw_id
    if fair:
        content = " ".join(
            part
            for part in (_text(item.get("gljg")), _text(item.get("jbcd")))
            if part
        )
        url = f"{base_url}/sub-station/job-fair/{quote(record_id, safe='')}"
        published_at = _text(item.get("jbkssj")) or None
        publisher = _text(item.get("gljg")) or "南京邮电大学"
    else:
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
        url = _text(item.get("tzljdz")) or (
            f"{base_url}/sub-station/news/{quote(record_id, safe='')}"
        )
        published_at = _text(item.get("fbsj")) or None
        publisher = "南京邮电大学就业信息网"
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
        "content_hash": stable_id(json.dumps(item, ensure_ascii=False, sort_keys=True)),
        "status": "ok",
        "content_status": "normal_content" if content else "empty_content",
        "extraction_strategy": "job91_api",
        "headings": [],
        "inline_links": [],
        "inline_images": [],
        "attachment_count": 0,
    }


def crawl(
    *,
    definition: SiteDefinition,
    config: dict[str, Any],
    output_path: Path,
    dry_run: bool,
    incremental: bool,
) -> SitePackage | None:
    del output_path
    if incremental:
        raise RuntimeError("91job plugin does not support incremental crawling")
    site_id = definition.id
    base_url = definition.base_url.rstrip("/")
    policy = config.get("crawl_policy", {})
    timeout = int(policy.get("timeout_seconds", 20))
    page_size = int(policy.get("job91_items_per_section", 120))
    maximum = int(policy.get("job91_max_pages_per_section", 40))
    if dry_run:
        print(
            json.dumps(
                {"site_id": site_id, "base_url": base_url, "plugin": "job91"},
                ensure_ascii=False,
            )
        )
        return

    started_at = now_iso()
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
    sections: list[dict[str, Any]] = []
    list_pages: list[dict[str, Any]] = []
    detail_by_url: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for column in columns:
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
        pages, stop = _pages(
            client,
            category=column["id"],
            page_size=page_size,
            maximum=maximum,
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
            list_pages.append(
                {
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
            )
            for index, item in enumerate(items):
                record = _record(
                    base_url=base_url,
                    site_id=site_id,
                    section_id=section_id,
                    item=item,
                    index=(page_number - 1) * page_size + index,
                )
                detail_by_url.setdefault(record["url"], record)
                edges.append(
                    {
                        "edge_id": stable_id(list_url, record["url"]),
                        "from_url": list_url,
                        "to_url": record["url"],
                        "anchor_text": record["title"],
                        "edge_type": "api_list_item",
                        "target_type": "detail_article_page",
                        "same_domain": True,
                    }
                )

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
    details = list(detail_by_url.values())
    return SitePackage(
        definition=definition,
        started_at=started_at,
        nav_nodes=nav_nodes,
        homepage_modules=modules,
        sections=sections,
        list_pages_by_url={item["url"]: item for item in list_pages},
        detail_pages_by_url={item["url"]: item for item in details},
        attachments_by_id={},
        external_links_by_id={},
        edges_by_id={item["edge_id"]: item for item in edges},
        errors=errors,
    )
