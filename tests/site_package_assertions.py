from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import date


PACKAGE_FILES = [
    'site.json',
    'nav_tree.json',
    'sections.json',
    'list_pages.jsonl',
    'detail_pages.jsonl',
    'attachments.jsonl',
    'external_links.jsonl',
    'edges.jsonl',
    'manifest.json',
    'homepage_modules.json',
    'coverage_report.json',
]

UNKNOWN_ALLOWLIST_FILE = 'unknown_url_allowlist.json'

BINARY_ATTACHMENT_SUFFIXES = {
    '.pdf',
    '.doc',
    '.docx',
    '.xls',
    '.xlsx',
    '.ppt',
    '.pptx',
    '.zip',
    '.rar',
}


def read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def assert_required_site_package(site_id: str) -> None:
    root = Path('data/sites') / site_id / 'index'
    assert (Path('configs/sites') / site_id / 'site.yaml').exists()
    for filename in PACKAGE_FILES:
        assert (root / filename).exists(), f'{site_id} missing {filename}'


def assert_manifest_complete(site_id: str) -> dict:
    root = Path('data/sites') / site_id / 'index'
    manifest = read_json(root / 'manifest.json')
    assert manifest['site_id'] == site_id
    assert manifest['quality']['all_discovered_urls_have_outcomes'] is True
    errors = manifest['errors']
    assert manifest['quality']['errors'] == 0, json.dumps(errors[:10], ensure_ascii=False, indent=2)
    assert manifest['quality']['attachment_policy'] == 'metadata_only'
    assert manifest['quality']['external_link_policy'] == 'record_only'
    allowed_statuses = {'complete', 'complete_with_exclusions'}
    assert manifest['coverage_status'] in allowed_statuses
    assert manifest['quality']['coverage_status'] == manifest['coverage_status']
    assert manifest['evidence_source'] == 'full_crawl'
    assert manifest['quality']['evidence_source'] == 'full_crawl'
    assert manifest['pagination_terminal_verified'] is True
    assert manifest['unknown_url_count'] == 0
    assert manifest['audit_evidence_ref']
    assert manifest['audit_evidence_json_ref']
    coverage = read_json(root / 'coverage_report.json')
    assert 'existing_package_under_safety_cap' not in json.dumps(coverage, ensure_ascii=False)
    assert coverage['site_id'] == site_id
    assert coverage['coverage_status'] == manifest['coverage_status']
    assert coverage['evidence_source'] == 'full_crawl'
    assert coverage['pagination']['terminal_verified'] is True
    assert coverage['audit_evidence_ref'] == manifest['audit_evidence_ref']
    assert coverage['audit_evidence_json_ref'] == manifest['audit_evidence_json_ref']
    exclusions = coverage['urls'].get('exclusions', [])
    assert manifest['coverage_status'] == ('complete_with_exclusions' if exclusions else 'complete')
    invalid_sources = set((coverage['sections'].get('by_source') or {})) - {
        'declared_section',
        'homepage_nav',
        'homepage_module',
        'inline_section_link',
        'api_category',
        'archive_section',
    }
    assert invalid_sources == set()
    for exclusion in exclusions:
        assert exclusion['reason']
        assert exclusion['scope']
        assert exclusion['evidence_url']
        assert exclusion['owner_action']
        assert exclusion['expiry'] >= date.today().isoformat()
    audit_path = root / manifest['audit_evidence_ref']
    assert audit_path.exists(), f'{site_id} missing audit evidence {manifest["audit_evidence_ref"]}'
    audit_json_path = root / manifest['audit_evidence_json_ref']
    assert audit_json_path.exists(), f'{site_id} missing audit JSON evidence {manifest["audit_evidence_json_ref"]}'
    audit_json = read_json(audit_json_path)
    assert audit_json['site_id'] == site_id
    assert 'existing_package_under_safety_cap' not in json.dumps(audit_json, ensure_ascii=False)
    assert errors == []
    assert manifest['url_outcomes']
    assert_unknown_outcomes_allowlisted(site_id, manifest)
    return manifest


def unknown_outcomes(manifest: dict) -> list[tuple[str, dict]]:
    return [
        (url, record)
        for url, record in manifest['url_outcomes'].items()
        if 'unknown' in record.get('target_type', '') or 'unknown' in record.get('outcome', '')
    ]


def assert_unknown_outcomes_allowlisted(site_id: str, manifest: dict) -> None:
    unknown = unknown_outcomes(manifest)
    if not unknown:
        return

    allowlist_path = Path('data/sites') / site_id / 'index' / UNKNOWN_ALLOWLIST_FILE
    assert allowlist_path.exists(), f'{site_id} has unknown URL outcomes but no {UNKNOWN_ALLOWLIST_FILE}'
    allowlist = read_json(allowlist_path)
    assert isinstance(allowlist, dict)
    assert allowlist.get('site_id') == site_id
    rules = allowlist.get('allowed_unknowns')
    assert isinstance(rules, list) and rules

    compiled_rules = []
    for rule in rules:
        assert isinstance(rule, dict)
        assert rule.get('reason')
        pattern = rule.get('url_pattern')
        assert isinstance(pattern, str) and pattern
        compiled_rules.append((rule, re.compile(pattern)))

    unexpected = []
    matched_rules: set[int] = set()
    for url, record in unknown:
        matched = False
        for index, (rule, pattern) in enumerate(compiled_rules):
            if not pattern.search(url):
                continue
            if rule.get('target_type') and rule['target_type'] != record.get('target_type'):
                continue
            if rule.get('outcome') and rule['outcome'] != record.get('outcome'):
                continue
            matched = True
            matched_rules.add(index)
            break
        if not matched:
            unexpected.append((url, record))

    assert unexpected == []
    stale_rules = [
        rule.get('url_pattern')
        for index, (rule, _pattern) in enumerate(compiled_rules)
        if index not in matched_rules
    ]
    assert stale_rules == []


def assert_counts_match_files(site_id: str, manifest: dict) -> None:
    root = Path('data/sites') / site_id / 'index'
    assert manifest['totals']['sections'] == len(read_json(root / 'sections.json'))
    assert manifest['totals']['nav_nodes'] == len(read_json(root / 'nav_tree.json')['nodes'])
    assert manifest['totals']['homepage_modules'] == len(read_json(root / 'homepage_modules.json')['modules'])
    assert manifest['totals']['list_pages'] == len(read_jsonl(root / 'list_pages.jsonl'))
    assert manifest['totals']['detail_pages'] == len(read_jsonl(root / 'detail_pages.jsonl'))
    assert manifest['totals']['attachments'] == len(read_jsonl(root / 'attachments.jsonl'))
    assert manifest['totals']['external_links'] == len(read_jsonl(root / 'external_links.jsonl'))
    assert manifest['totals']['edges'] == len(read_jsonl(root / 'edges.jsonl'))
    assert manifest['totals']['url_outcomes'] == len(manifest['url_outcomes'])


def assert_output_urls_have_outcomes(site_id: str, manifest: dict) -> None:
    root = Path('data/sites') / site_id / 'index'
    outcome_urls = set(manifest['url_outcomes'])
    urls: set[str] = set()

    site = read_json(root / 'site.json')
    urls.add(site['base_url'])

    for node in read_json(root / 'nav_tree.json')['nodes']:
        urls.add(node['url'])
    for section in read_json(root / 'sections.json'):
        urls.add(section['url'])
    for page in read_jsonl(root / 'list_pages.jsonl'):
        urls.add(page['url'])
    for page in read_jsonl(root / 'detail_pages.jsonl'):
        urls.add(page['url'])
        for link in page.get('inline_links', []):
            urls.add(link['url'])
        for image in page.get('inline_images', []):
            urls.add(image['url'])
    for attachment in read_jsonl(root / 'attachments.jsonl'):
        urls.add(attachment['url'])
    for external in read_jsonl(root / 'external_links.jsonl'):
        urls.add(external['url'])
        if external.get('source_redirect_url'):
            urls.add(external['source_redirect_url'])
    for edge in read_jsonl(root / 'edges.jsonl'):
        urls.add(edge['from_url'])
        urls.add(edge['to_url'])

    missing = sorted(url for url in urls if url and url.startswith(('http://', 'https://')) and url not in outcome_urls)
    assert missing == []


def assert_attachment_policy(site_id: str, manifest: dict) -> None:
    root = Path('data/sites') / site_id / 'index'
    attachment_records = read_jsonl(root / 'attachments.jsonl')
    assert attachment_records
    for attachment in attachment_records:
        assert attachment['url'] in manifest['url_outcomes']
        assert manifest['url_outcomes'][attachment['url']]['outcome'] == 'attachment_metadata_only'
        assert attachment.get('extension')
        assert 'content' not in attachment

    saved_binaries = [
        path
        for path in (Path('data/sites') / site_id).rglob('*')
        if path.is_file() and path.suffix.lower() in BINARY_ATTACHMENT_SUFFIXES
    ]
    assert saved_binaries == []


def assert_external_policy(site_id: str, manifest: dict) -> None:
    root = Path('data/sites') / site_id / 'index'
    external_records = read_jsonl(root / 'external_links.jsonl')
    assert external_records
    for external in external_records:
        assert external['category'].endswith('_link') or external['category'] == 'cross_domain_article_link'
        assert external['url'] in manifest['url_outcomes']
        assert manifest['url_outcomes'][external['url']]['outcome'].endswith('_recorded')
        if external.get('source_redirect_url'):
            assert external['source_redirect_url'] in manifest['url_outcomes']
            assert manifest['url_outcomes'][external['source_redirect_url']]['outcome'].endswith('_recorded')


def assert_has_section_content(site_id: str, expected_urls: set[str]) -> None:
    details = read_jsonl(Path('data/sites') / site_id / 'index' / 'detail_pages.jsonl')
    section_content = {item['url']: item for item in details if item.get('page_type') == 'section_content_page'}
    assert expected_urls <= set(section_content)
    for url in expected_urls:
        assert section_content[url]['title']
        assert section_content[url]['content_status'] in {'normal_content', 'low_content'}
