from site_package_assertions import (
    assert_attachment_policy,
    assert_counts_match_files,
    assert_external_policy,
    assert_has_section_content,
    assert_manifest_complete,
    assert_output_urls_have_outcomes,
    assert_required_site_package,
)


def test_xsc_site_package_complete():
    assert_required_site_package('xsc')
    manifest = assert_manifest_complete('xsc')
    assert_counts_match_files('xsc', manifest)
    assert_output_urls_have_outcomes('xsc', manifest)
    assert_attachment_policy('xsc', manifest)
    assert_external_policy('xsc', manifest)
    assert_has_section_content(
        'xsc',
        {
            'https://xsc.njupt.edu.cn/1149/list.htm',
            'https://xsc.njupt.edu.cn/djgz/list.htm',
            'https://xsc.njupt.edu.cn/16749/list.htm',
        },
    )
