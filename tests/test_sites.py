from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sites.plugins import job91
from sites.registry import load_site_registry
from sitegraph.config import load_site_definition
from sitegraph.package import write_site_package
from ops import njupt


def test_registry_points_to_owned_site_configs() -> None:
    registry = load_site_registry(ROOT / "sites/registry.json")
    ids: set[str] = set()
    for site in registry:
        assert site.id not in ids
        ids.add(site.id)
        assert site.config == f"sites/{site.id}/site.yaml"
        assert (ROOT / site.config).is_file()


def test_crawl_runs_each_site_with_bounded_parallelism(
    tmp_path: Path, monkeypatch
) -> None:
    sites = [
        SimpleNamespace(id=f"site-{index}", config="", plugin=None)
        for index in range(5)
    ]
    lock = threading.Lock()
    active = 0
    maximum_active = 0
    completed: list[str] = []

    def fake_crawl_site(site, _args) -> None:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.01)
        with lock:
            active -= 1
            completed.append(site.id)

    monkeypatch.setattr(njupt, "load_site_registry", lambda *_args: sites)
    monkeypatch.setattr(njupt, "_crawl_site", fake_crawl_site)
    njupt.crawl(
        SimpleNamespace(
            include=None,
            packages_root=tmp_path,
            dry_run=False,
            incremental=True,
            jobs=2,
        )
    )

    assert set(completed) == {site.id for site in sites}
    assert maximum_active == 2


def test_job91_plugin_produces_a_site_package(
    tmp_path: Path, monkeypatch
) -> None:
    class FakeClient:
        def __init__(self, base_url: str, timeout: int) -> None:
            assert base_url == "https://njupt.91job.org.cn"
            assert timeout == 20

        def get(self, path: str, params=None):
            if path.endswith("getWzid"):
                return {"result": "website-id"}
            if path.endswith("getXwlm"):
                return {
                    "result": [
                        {
                            "lmid": "notice",
                            "lmmc": "就业通知",
                            "model": [],
                        }
                    ]
                }
            if path.endswith("getLbsj"):
                return {
                    "result": [
                        {
                            "xwid": "news-1",
                            "xwbt": "校园招聘通知",
                            "xwnr": "招聘正文",
                            "fbsj": "2026-07-29",
                        }
                    ]
                }
            raise AssertionError(path)

    monkeypatch.setattr(job91, "Client", FakeClient)
    output = tmp_path / "package"
    definition = load_site_definition(ROOT / "sites/job91/site.yaml")
    package = job91.crawl(
        definition=definition,
        config=definition.config,
        output_path=output,
        dry_run=False,
        incremental=False,
    )
    assert package is not None
    write_site_package(package, output, incremental=False)

    detail = json.loads((output / "detail_pages.jsonl").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert detail["title"] == "校园招聘通知"
    assert detail["content_text"] == "招聘正文"
    assert manifest["totals"]["detail_pages"] == 1
    assert manifest["errors"] == []


def test_job91_incremental_stops_at_known_page_and_keeps_prior_facts(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[int] = []

    class InitialClient:
        def __init__(self, base_url: str, timeout: int) -> None:
            pass

        def get(self, path: str, params=None):
            if path.endswith("getWzid"):
                return {"result": "website-id"}
            if path.endswith("getXwlm"):
                return {
                    "result": [
                        {"lmid": "notice", "lmmc": "就业通知", "model": []}
                    ]
                }
            if path.endswith("getLbsj"):
                return {
                    "result": [
                        {
                            "xwid": "news-1",
                            "xwbt": "已有通知",
                            "xwnr": "已有正文",
                            "fbsj": "2026-07-29",
                        }
                    ]
                }
            raise AssertionError(path)

    output = tmp_path / "package"
    definition = load_site_definition(ROOT / "sites/job91/site.yaml")
    config = {
        **definition.config,
        "crawl_policy": {
            **definition.config["crawl_policy"],
            "job91_items_per_section": 1,
        },
    }
    monkeypatch.setattr(job91, "Client", InitialClient)
    initial = job91.crawl(
        definition=definition,
        config=config,
        output_path=output,
        dry_run=False,
        incremental=False,
    )
    assert initial is not None
    write_site_package(initial, output, incremental=False)

    class IncrementalClient(InitialClient):
        def get(self, path: str, params=None):
            if not path.endswith("getLbsj"):
                return super().get(path, params)
            page = int((params or {}).get("page", 1))
            calls.append(page)
            identifier = "news-2" if page == 1 else "news-1"
            return {
                "result": [
                    {
                        "xwid": identifier,
                        "xwbt": "新增通知" if page == 1 else "已有通知",
                        "xwnr": "新增正文" if page == 1 else "已有正文",
                        "fbsj": "2026-07-30" if page == 1 else "2026-07-29",
                    }
                ]
            }

    monkeypatch.setattr(job91, "Client", IncrementalClient)
    update = job91.crawl(
        definition=definition,
        config=config,
        output_path=output,
        dry_run=False,
        incremental=True,
    )
    assert update is not None
    write_site_package(update, output, incremental=True)

    rows = [
        json.loads(line)
        for line in (output / "detail_pages.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert calls == [1, 2]
    assert {row["title"] for row in rows} == {"已有通知", "新增通知"}
