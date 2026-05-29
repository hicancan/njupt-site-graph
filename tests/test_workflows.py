from pathlib import Path


def test_update_sitegraph_workflow_runs_incremental_every_six_hours():
    workflow = Path('.github/workflows/update-sitegraph-data.yml')
    assert workflow.exists()
    text = workflow.read_text(encoding='utf-8')
    assert "cron: '0 */6 * * *'" in text
    assert '--incremental' in text
    assert '--incremental-known-page-stop 2' in text
    assert 'git add data/sites/*/index/' in text


def test_update_sitegraph_workflow_dispatches_search_after_success():
    workflow = Path('.github/workflows/update-sitegraph-data.yml')
    assert workflow.exists()
    text = workflow.read_text(encoding='utf-8')
    assert 'repos/hicancan/njupt-search/dispatches' in text
    assert 'sitegraph-data-updated' in text
    assert 'NJUPT_SEARCH_DISPATCH_TOKEN' in text
    assert 'git rev-parse HEAD' in text


def test_ci_workflow_validates_three_site_configs():
    workflow = Path('.github/workflows/ci.yml')
    assert workflow.exists()
    text = workflow.read_text(encoding='utf-8')
    for site_id in ('jwc', 'xsc', 'cxcy'):
        assert f'configs/sites/{site_id}/site.yaml' in text
