from __future__ import annotations

import json
from pathlib import Path


EXPECTED_SITE_IDS = {
    "jwc",
    "xsc",
    "cxcy",
    "lib",
    "xxb",
    "www",
    "job91",
    "tyb",
    "bwc",
    "fwlc",
    "gzzd",
    "xxgk",
    "cs",
    "scie",
    "bhs",
}


def read_registry() -> list[dict[str, str]]:
    payload = json.loads(Path("configs/site_registry.json").read_text(encoding="utf-8"))
    assert payload["version"] == "njupt-site-registry-v1"
    return payload["sites"]


def test_site_registry_is_complete_and_unique():
    sites = read_registry()
    site_ids = [site["id"] for site in sites]
    assert set(site_ids) == EXPECTED_SITE_IDS
    assert len(site_ids) == len(set(site_ids))
    for site in sites:
        assert Path(site["config"]).exists(), site
        assert site["package"] == f"data/sites/{site['id']}/index"
