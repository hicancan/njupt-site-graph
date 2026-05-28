from site_package_assertions import (
    assert_attachment_policy,
    assert_counts_match_files,
    assert_external_policy,
    assert_has_section_content,
    assert_manifest_complete,
    assert_output_urls_have_outcomes,
    assert_required_site_package,
)


def test_cxcy_site_package_complete():
    assert_required_site_package('cxcy')
    manifest = assert_manifest_complete('cxcy')
    assert_counts_match_files('cxcy', manifest)
    assert_output_urls_have_outcomes('cxcy', manifest)
    assert_attachment_policy('cxcy', manifest)
    assert_external_policy('cxcy', manifest)
    assert_has_section_content(
        'cxcy',
        {
            'https://cxcy.njupt.edu.cn/15485/list.htm',
            'https://cxcy.njupt.edu.cn/15490/list.htm',
            'https://cxcy.njupt.edu.cn/18404/list.htm',
        },
    )
