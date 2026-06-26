from pathlib import Path


def test_update_sitegraph_workflow_runs_incremental_every_six_hours():
    workflow = Path('.github/workflows/update-sitegraph-data.yml')
    assert workflow.exists()
    text = workflow.read_text(encoding='utf-8')
    assert "cron: '0 */6 * * *'" in text
    assert '--incremental' in text
    assert '--incremental-known-page-stop 2' in text
    assert 'validate-packages --include "${{ matrix.site }}"' in text
    assert 'for attempt in 1 2 3' in text
    assert 'still failed after $attempt attempts' in text
    assert 'python scripts/commit_generated_changes.py' in text
    assert '--add data/sites/*/index/' in text
    assert '--ref-output sitegraph_ref' in text
    assert 'read-site-matrix:' in text
    assert 'crawl-site:' in text
    assert 'commit-and-dispatch:' in text
    assert 'max-parallel: 6' in text
    assert 'matrix:' in text
    assert 'site: ${{ fromJson(needs.read-site-matrix.outputs.sites) }}' in text
    assert 'sitegraph-package-${{ matrix.site }}' in text
    assert 'actions/download-artifact@v7' in text
    assert 'cancel-in-progress: false' in text
    assert 'git push' not in text


def test_sitegraph_package_validator_rejects_oversized_manifests():
    script = Path("scripts/sitegraph_registry.py").read_text(encoding="utf-8")
    assert "MAX_MANIFEST_BYTES = 25 * 1024 * 1024" in script
    assert "manifest is too large" in script


def test_update_sitegraph_workflow_dispatches_search_after_success():
    workflow = Path('.github/workflows/update-sitegraph-data.yml')
    assert workflow.exists()
    text = workflow.read_text(encoding='utf-8')
    assert 'repos/hicancan/njupt-search/dispatches' in text
    assert 'sitegraph-data-updated' in text
    assert 'NJUPT_SEARCH_DISPATCH_TOKEN' in text
    assert 'git rev-parse HEAD' in text
    assert 'force_downstream_dispatch' in text
    assert 'dispatch_only' in text
    assert 'dispatch_sitegraph_ref' in text
    assert 'dispatch-downstream-only' in text
    assert "github.event.inputs.dispatch_only == 'true'" in text
    assert "github.event_name != 'workflow_dispatch' || github.event.inputs.dispatch_only != 'true'" in text
    assert "steps.commit_sitegraph_data.outputs.changed == 'true' || github.event.inputs.force_downstream_dispatch == 'true'" in text
    assert 'client_payload[source_repo]' in text
    assert 'client_payload[source_run_id]' in text
    assert 'client_payload[dispatch_reason]' in text
    assert 'manual_dispatch_only' in text


def test_ci_workflow_uses_site_registry():
    workflow = Path('.github/workflows/ci.yml')
    assert workflow.exists()
    text = workflow.read_text(encoding='utf-8')
    assert 'scripts/sitegraph_registry.py validate-configs' in text
    assert 'scripts/sitegraph_registry.py dry-run --incremental' in text
    assert 'configs/sites/jwc/site.yaml' not in text
    assert 'configs/sites/xsc/site.yaml' not in text
    assert 'configs/sites/cxcy/site.yaml' not in text


def test_update_workflow_uses_site_registry():
    workflow = Path('.github/workflows/update-sitegraph-data.yml')
    text = workflow.read_text(encoding='utf-8')
    assert 'scripts/sitegraph_registry.py validate-configs' in text
    assert 'scripts/sitegraph_registry.py validate-configs --include "${{ matrix.site }}"' in text
    assert 'scripts/sitegraph_registry.py crawl --incremental --include "${{ matrix.site }}" --incremental-known-page-stop 2 --incremental-refresh-frontier 3' in text
    assert 'scripts/sitegraph_registry.py validate-packages --include "${{ matrix.site }}"' in text
    assert 'scripts/sitegraph_registry.py summary' in text
    assert 'scripts/sitegraph_registry.py summary --include "${{ matrix.site }}"' in text


def test_generated_commit_helper_retries_push_after_rebase():
    helper = Path('scripts/commit_generated_changes.py')
    assert helper.exists()
    text = helper.read_text(encoding='utf-8')
    assert 'git", "push", "origin", f"HEAD:{branch}"' in text
    assert 'git", "fetch", "origin", branch' in text
    assert 'git", "rebase", f"origin/{branch}"' in text
    assert 'GITHUB_OUTPUT' in text
