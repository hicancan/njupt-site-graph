# CXCY deep audit notes

Target site: `https://cxcy.njupt.edu.cn/`  
Browser audit date: 2026-05-28 Asia/Shanghai  
Browser surface: Codex in-app Browser

## Homepage structure

The homepage title is `南京邮电大学|创新创业教育学院`. Browser inspection found:

- logo/home link;
- global navigation in `#nav` / `.wp-menu`;
- nested dropdown navigation under 学院简介, 规章制度, 双创教育, 双创项目, 党群工作, 信息公开;
- homepage modules for 新闻资讯, 通知公告, 双创项目, 竞赛成果;
- quick-link band for 大学生创业园, 双创平台, 双创导师, 大学生创协, 路演大厅, 双创信息管理系统;
- footer friendly links implemented as same-domain `_redirect` URLs;
- article images and attachments in detail pages.

## Navigation hierarchy

Browser-observed navigation includes the homepage link plus these crawlable nodes:

```text
学院简介
  学院概况
  现任领导
  联系方式
规章制度
  上级文件
  学校规章
双创教育
  创新创业课程
  创新创业培训
  创新创业师资
双创项目
  大创项目
    相关通知
    立项公示
  学科竞赛
    相关通知
    通讯报道
  双创活动
双创基地
党群工作
  党建工作
  分工会
  师德师风建设
下载中心
信息公开
  会议信息
  书记信箱
  院长信箱
```

## Homepage modules

Representative module entry points verified in-browser:

- 新闻资讯: `https://cxcy.njupt.edu.cn/xwzx/list.htm`, 14 records/page, 178 records, 13 pages.
- 通知公告: `https://cxcy.njupt.edu.cn/tzgg/list.htm`, 14 records/page, 237 records, 17 pages.
- 双创项目: `https://cxcy.njupt.edu.cn/scxm/list.htm`, 24 records, 2 pages.
- 竞赛成果: `https://cxcy.njupt.edu.cn/jscx/list.htm`, 21 records, 2 pages.
- 下载中心: `https://cxcy.njupt.edu.cn/15468/list.htm`, direct attachment records.

## Representative pages

List pages:

- `https://cxcy.njupt.edu.cn/xwzx/list.htm`: `.news_list.list2` list container, 14/page pagination.
- `https://cxcy.njupt.edu.cn/tzgg/list.htm`: notice family, 237 records across 17 pages.
- `https://cxcy.njupt.edu.cn/15468/list.htm`: direct attachment list with xls/doc metadata.

Detail/content pages:

- Normal detail with attachments: `https://cxcy.njupt.edu.cn/2022/0712/c15489a224094/page.htm`, title `南京邮电大学大学生创新训练计划管理办法（修订）`.
- Recent detail with attachments: `https://cxcy.njupt.edu.cn/2026/0521/c11336a302380/page.htm`, title `【资助项目遴选】关于遴选第十四批“南邮-紫金科创学生创业基金” 资助项目的通知`.
- Static section-content examples: `https://cxcy.njupt.edu.cn/15485/list.htm` 学院概况, `https://cxcy.njupt.edu.cn/15490/list.htm` 创新创业课程, and `https://cxcy.njupt.edu.cn/18404/list.htm` 书记信箱.

External/system links:

- Footer `_redirect` links resolve by HTTP 302 to:
  - 江苏省大学生创新创业平台: `http://180.108.46.32:83/index.html`
  - 江苏省教育厅: `http://www.ec.js.edu.cn/`
  - 教育部网站: `http://www.moe.gov.cn/`
  - 教务处首页: `http://jwc.njupt.edu.cn/`
  - 学校首页: `http://www.njupt.edu.cn/`
- Browser navigation to `_redirect` was blocked by the client, so final modeling records the redirect source URL and HTTP 302 destination without crawling the external destination.

## Modeling implications

- Use `njupt_wp` WebPlus selectors.
- Treat `.news_list.list2` as the primary list container.
- Preserve zero-item `list.htm` pages as `section_content_page` records because several are static content pages.
- Resolve same-domain `_redirect` URLs only to record external destination metadata.
- Record direct download center files as attachment metadata only.
- Do not recursively crawl external platforms, policy sites, or IP-hosted systems.
