from pathlib import Path


def test_jwc_config_exists():
    assert Path('configs/sites/jwc/site.yaml').exists()
    assert Path('docs/research/jwc_deep_audit.md').exists()
