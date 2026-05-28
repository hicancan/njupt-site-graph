# XSC deep audit notes

Target site: `https://xsc.njupt.edu.cn/`  
Browser audit date: 2026-05-28 Asia/Shanghai  
Browser surface: Codex in-app Browser

## Homepage structure

The homepage title is `学生工作部（处）`. Browser inspection found a WebPlus-style homepage with:

- logo/home link;
- global navigation in `#nav` / `.wp-menu`;
- nested dropdown navigation under department overview, student management, ideological education, financial aid, party branch, and downloads;
- homepage modules for 学工要闻, 通知公告, 下载专区/奖助管理, 学工之家, 学院风采, 榜样力量, 光荣使命, 学工荣誉;
- footer link groups for 校内链接 and 校外链接;
- inline images in homepage carousels and article bodies;
- direct homepage attachment link for `学生手册（2025版）`.

## Navigation hierarchy

Browser-observed navigation contains 30 nodes:

```text
网站首页
部门概况
  工作职责
  联系方式
综合管理
  学风建设
  服务指南
  工作参考
  违纪处理
思政专题
  主题教育活动
  辅导员队伍建设
资助工作
  政策规定
  服务指南
心理健康
宿舍管理
就业指导
人民武装
支部建设
  支部介绍
  支部动态
“一站式”学生社区
下载专区
  奖助管理
  学籍管理
  教学管理
  日常管理
  工作表格
  宣传视频
```

`心理健康`, `就业指导`, and `人民武装` are external systems/sites and must be record-only.

## Homepage modules

Representative module entry points verified in-browser:

- 学工要闻: `https://xsc.njupt.edu.cn/1176/list.htm`, 8 records/page, 55 records, 7 pages.
- 通知公告: `https://xsc.njupt.edu.cn/1173/list.htm`, 4 records, 1 page.
- 下载专区 / 奖助管理: `https://xsc.njupt.edu.cn/1169/list.htm`, mixed detail and direct attachment records, 22 records, 3 pages.
- 学工之家: `https://xsc.njupt.edu.cn/17674/list.htm`, 117 records, 15 pages.
- 学院风采: `https://xsc.njupt.edu.cn/1175/list.htm`, 1066 records, 134 pages.
- 榜样力量: `https://xsc.njupt.edu.cn/17675/list.htm`, external WeChat links, 24 records, 3 pages.
- 光荣使命: `https://xsc.njupt.edu.cn/17676/list.htm`, external WeChat links, 18 records, 3 pages.
- 学工荣誉: `https://xsc.njupt.edu.cn/ryq/list.htm`, 6 records, 1 page.

## Representative pages

List pages:

- `https://xsc.njupt.edu.cn/1176/list.htm`: `.news_list2.list2` list container, `wp_paging` next-link pagination.
- `https://xsc.njupt.edu.cn/1169/list.htm`: download/resource family, includes a direct PDF item plus detail pages.
- `https://xsc.njupt.edu.cn/_s24/_t3618/1160%20/list.psp`: legacy policy URL exposed in navigation; same content also works at `https://xsc.njupt.edu.cn/1160/list.htm`.

Detail/content pages:

- Normal detail example: `https://xsc.njupt.edu.cn/2010/0420/c1147a13374/page.htm`, title `综合管理科（学生事务中心）`, extraction strategy `.wp_articlecontent`.
- Low-content detail example: `https://xsc.njupt.edu.cn/2025/0324/c1160a280209/page.htm`, title `校学发〔2025〕12号南京邮电大学“甘霖励志奖学金”评选办法`.
- Static section-content examples: `https://xsc.njupt.edu.cn/1149/list.htm` 联系方式 and `https://xsc.njupt.edu.cn/djgz/list.htm` 支部介绍 use `list.htm` URLs but contain body content and no list items.

Attachments:

- Homepage PDF: `学生手册（2025版）`.
- Work-form attachments under `https://xsc.njupt.edu.cn/1170/list.htm`, including dormitory and work-study forms.

External/system links:

- `http://xl.njupt.edu.cn`
- `https://njupt.91job.org.cn/sub-station/home/10293`
- `https://rwb.njupt.edu.cn/`
- WeChat article links in 榜样力量 and 光荣使命 modules.
- Footer links to NJUPT units and external education/policy sites.

## Modeling implications

- Use `njupt_wp` WebPlus selectors.
- Treat `.news_list2.list2` as the primary XSC list container.
- Accept both `list.htm` and `list.psp` as list pages.
- Preserve zero-item `list.htm` pages as `section_content_page` records.
- Record attachments as metadata only.
- Record external systems and WeChat links only; do not recursively crawl them.
