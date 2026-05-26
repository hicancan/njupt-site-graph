# JWC reference-site deep audit notes

This document is a research baseline for `https://jwc.njupt.edu.cn/`. It is not a substitute for the final generated manifest. Claude Code must use Chrome to complete the exhaustive site model locally.

## Observed homepage structure

The homepage exposes:

- global top navigation;
- multi-level dropdown navigation;
- homepage content modules;
- external systems;
- undergraduate teaching project links;
- footer internal and external link groups;
- visible address/postcode/maintainer metadata.

### Global navigation families

Observed top-level navigation:

- 校历查询
- 首页
- 机构设置
- 规章制度
- 办事流程
- 信息公开
- 支部建设
- 常用下载

### 机构设置

Observed child nodes:

- 部门领导
- 工作职能
- 综合办公室
- 本科招生办公室
- 教务管理办公室
- 质量工程建设中心
- 未来教师发展中心
- 创新创业教育学院
- 联系方式

Several nodes are external sites, so `NavNode.target_type` cannot assume same-domain.

### 规章制度

Observed hierarchy:

```text
规章制度
  国家
    法律
    法规
    政策文件
  学校
    教学工作
    专业建设
    课程建设
    学生培养
    考试工作
    教学运行
    实践教学
    教材建设
    教学研究
```

This page family is policy/regulation, not ordinary notification content. It must support internal detail pages and external policy links.

Representative section: `https://jwc.njupt.edu.cn/1746/list.htm`.
Observed pagination metadata in HTTP text: 14 records per page, total around 77, page 1/6. The crawler must not rely on a single total value; it must count actual items and record observed pagination values.

### 办事流程

Observed hierarchy:

```text
办事流程
  学生事务
    学籍
    选课
    考试
    成绩
    实践
    教材
    出国成绩单
    推免生
    毕业、结业与学位
  教师事务
    教学运行
    考试
    成绩
    实践
    教材
    教学改革
  教学管理事务
    培养方案
    专业建设
    课程建设
    考试
    教材
    评优评奖
```

This is workflow/procedure content. Search consumers should not rank these purely by recency.

### 信息公开

Observed child nodes:

- 校历查询
- 教学研究成果及评选办法
- 教学改革立项
- 精品课程介绍
- 本科生专业设置
- 考试规则
- 考试纪律和考试违纪处理
- 学籍管理办法
- 推荐免试研究生管理办法
- 学位授予办法
- 领导信箱

This is public-info / evergreen content.

### 常用下载

Observed root categories:

- 学生相关文件及表格
- 教师相关文件及表格
- 教学管理常用表格

Observed student subcategories:

- 学籍
- 课表
- 选课
- 成绩
- 自主学分
- 推免生
- 毕业、结业与学位
- 考试
- 出国成绩单
- 实验实践教学
- 毕业设计（论文）
- 实习工作
- 大学生创新创业训练计划
- 学科竞赛
- 新旧课程对照
- 访学生

Observed teacher/admin subcategories include teaching operation, grade, exam, practice, graduation thesis, internship, innovation project, competition, major construction, course construction, training plan, teaching reform, new course approval, teaching evaluation, textbook work.

Representative section: `https://jwc.njupt.edu.cn/1690/list.htm`.
Observed pagination metadata in HTTP text: 14 records per page, total 65, page 1/5.
The first item appears repeated in the parsed text, so crawler dedupe must operate on URL+label and manifest raw repeats.

## Homepage modules

Observed modules:

- 新闻动态
- 通知公告
- 教务快讯
- 教改动态
- 八面来风
- 综合信息服务
- 本科教学工程
- 校内链接
- 校外链接

### 综合信息服务

Observed external/system links:

- 教务管理系统
- 自主学分系统
- 创新管理系统
- 毕业设计系统
- 考试信息查询
- 作息时间查询
- 教学进程查询
- 学科竞赛系统

These should be `external_system_link` or same-domain tool links, not ordinary detail pages.

### 本科教学工程

Observed links include 教学成果、专业认证、卓越计划、品牌特色专业、专业综合改革、重点专业、精品课程、教学团队、专业评估、质量报告、名师风采. Some are external sub-sites.

## Detail page families

### Full detail article

Representative URL:

`https://jwc.njupt.edu.cn/2026/0327/c1594a298565/page.htm`

Observed fields:

- title
- publisher: 综合办公室
- published_at: 2026-03-27
- view_count
- body headings/numbered sections
- embedded system URL: 教务管理系统 URL
- inline images and captions
- QQ group value
- four attachments: xlsx, docx, docx, pdf

Required extraction:

- title;
- publisher;
- published_at;
- view_count;
- content_text;
- headings;
- inline_links;
- inline_images;
- attachment metadata;
- content_status.

### Low-content detail article

Representative URL:

`https://jwc.njupt.edu.cn/2026/0518/c1594a302043/page.htm`

Observed fields:

- title;
- publisher;
- published_at;
- view_count;
- little/no body content in HTTP text.

Required classification:

- `detail_article_page` with `content_status=low_content`;
- Chrome audit required before declaring extraction failure or true low content.

## Required final structured package

The final local run must generate:

```text
data/sites/jwc/index/site.json
data/sites/jwc/index/nav_tree.json
data/sites/jwc/index/sections.json
data/sites/jwc/index/list_pages.jsonl
data/sites/jwc/index/detail_pages.jsonl
data/sites/jwc/index/attachments.jsonl
data/sites/jwc/index/external_links.jsonl
data/sites/jwc/index/edges.jsonl
data/sites/jwc/index/manifest.json
data/sites/jwc/reports/audit_report.md
```

## Completion requirement

This document must be converted from notes into evidence-backed generated outputs. The final manifest must prove that every discovered URL has an outcome.
