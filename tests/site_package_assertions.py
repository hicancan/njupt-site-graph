from __future__ import annotations

import json
from pathlib import Path


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
]

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
    assert manifest['quality']['errors'] == 0
    assert manifest['quality']['attachment_policy'] == 'metadata_only'
    assert manifest['quality']['external_link_policy'] == 'record_only'
    assert manifest['errors'] == []
    assert manifest['url_outcomes']
    assert not [
        (url, record)
        for url, record in manifest['url_outcomes'].items()
        if 'unknown' in record.get('target_type', '') or 'unknown' in record.get('outcome', '')
    ]
    return manifest


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
