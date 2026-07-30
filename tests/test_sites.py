from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sites.plugins import job91
from sites.registry import load_site_registry
from sitegraph.config import load_site_definition
from sitegraph.package import write_site_package


def test_registry_points_to_owned_site_configs() -> None:
    registry = load_site_registry(ROOT / "sites/registry.json")
    ids: set[str] = set()
    for site in registry:
        assert site.id not in ids
        ids.add(site.id)
        assert site.config == f"sites/{site.id}/site.yaml"
        assert (ROOT / site.config).is_file()


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
