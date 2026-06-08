from __future__ import annotations

import json
from pathlib import Path

import pytest

from site_package_assertions import (
    assert_attachment_policy,
    assert_counts_match_files,
    assert_external_policy,
    assert_manifest_complete,
    assert_output_urls_have_outcomes,
    assert_required_site_package,
)


def registered_site_ids() -> list[str]:
    registry = json.loads(Path("configs/site_registry.json").read_text(encoding="utf-8"))
    return [site["id"] for site in registry["sites"]]


@pytest.mark.parametrize("site_id", registered_site_ids())
def test_registered_site_package_complete(site_id: str):
    assert_required_site_package(site_id)
    manifest = assert_manifest_complete(site_id)
    assert_counts_match_files(site_id, manifest)
    assert_output_urls_have_outcomes(site_id, manifest)
    if int(manifest["totals"].get("attachments") or 0) > 0:
        assert_attachment_policy(site_id, manifest)
    if int(manifest["totals"].get("external_links") or 0) > 0:
        assert_external_policy(site_id, manifest)
    searchable_records = int(manifest["totals"].get("detail_pages") or 0) + int(manifest["totals"].get("external_links") or 0)
    assert searchable_records > 0
