from pathlib import Path

from site_package_assertions import read_json


def test_jwc_config_exists():
    assert Path('configs/sites/jwc/site.yaml').exists()
    assert Path('docs/research/jwc_deep_audit.md').exists()


def test_jwc_manifest_remains_complete():
    manifest = read_json(Path('data/sites/jwc/index/manifest.json'))
    assert manifest['site_id'] == 'jwc'
    assert manifest['quality']['all_discovered_urls_have_outcomes'] is True
    assert manifest['quality']['errors'] == 0
    assert manifest['quality']['attachment_policy'] == 'metadata_only'
    assert manifest['quality']['external_link_policy'] == 'record_only'
