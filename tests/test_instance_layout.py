from pathlib import Path

from site_package_assertions import (
    assert_attachment_policy,
    assert_counts_match_files,
    assert_external_policy,
    assert_manifest_complete,
    assert_required_site_package,
)


def test_jwc_config_exists():
    assert Path('configs/sites/jwc/site.yaml').exists()
    assert Path('data/sites/jwc/index/manifest.json').exists()


def test_jwc_manifest_remains_complete():
    assert_required_site_package('jwc')
    manifest = assert_manifest_complete('jwc')
    assert_counts_match_files('jwc', manifest)
    assert_attachment_policy('jwc', manifest)
    assert_external_policy('jwc', manifest)
