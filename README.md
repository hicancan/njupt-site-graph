<div align="center">

# njupt-site-graph

南京邮电大学全域静态知识图谱管线 (NJUPT Static Knowledge Graph Pipeline)

[![Python](https://img.shields.io/badge/Python-3.10+-FFD43B.svg)](https://www.python.org/)
[![Dependency](https://img.shields.io/badge/upstream-static--site--graph-235A97.svg)](https://github.com/hicancan/static-site-graph)
[![Continuous Integration](https://img.shields.io/badge/GitHub%20Actions-Automated%20ETL-2088FF.svg)](https://github.com/features/actions)

</div>

---

## 📖 项目定位 (The Vision)

`njupt-site-graph` 是上游框架 `static-site-graph` 的核心生产级实例。
它的职责是将南京邮电大学域内（如教务处网站等）极其碎片化、非结构化的公告与附件，严格映射、爬取并清洗为一张具备高度结构化与确定性的静态知识图谱（Site Package）。

它作为一座稳固的数据桥梁，连接着凌乱的高校官网底座与下游的语义搜索引擎。

---

## 🗺️ 检索生态拓扑 (Ecosystem Topology)

本项目在整个“南邮去服务端化检索生态”中扮演中枢调度角色，数据流向如下：

```text
[ 底层引擎 ] static-site-graph 
    │ (提供纯粹的声明式爬取与建模框架)
    ▼
[ 实例管线 ] njupt-site-graph (★ 本仓库)
    │ (承载南邮特定站点的爬取规则、业务断言，并输出 SG 包)
    ▼
[ 端侧消费 ] njupt-search
      (利用 Github Actions 接收产物，编译为二进制倒排并分发至终端)
```

---

## ⚙️ 自动化交付契约 (CI/CD Pipeline)

本仓库不是孤立运行的，它与下游引擎通过严格的 **Webhook 机制** 绑定：

1. **流水线生产**：当配置发生变更或触发定时任务时，Github Actions 将启动全量爬取管线。
2. **事件派发 (Repository Dispatch)**：管线成功构建并打包图谱数据后，会携带 `sitegraph-data-updated` 事件静默触发 `hicancan/njupt-search` 仓库的构建流。
3. **安全鉴权**：派发机制由安全的跨库 `NJUPT_SEARCH_DISPATCH_TOKEN` 保护，确保底层倒排索引（SGIXB002）的构建永远紧跟最新数据源。

*(如需调试下游集成，可在 Github Actions 面板手动触发工作流并设置 `dispatch_only=true` 以仅发送事件而不发起真实爬取。)*

---

## 🚀 本地开发与实例调试 (Development)

### 仓库边界约束

为了保证图谱包的纯粹可复用性，本仓库**仅维护南邮特异性的 YAML 配置、实例特定测试、工作流脚本以及最终的产物包**。禁止任何底层的爬虫框架功能侵入本库（请提交 PR 至上游 `static-site-graph`）。

### 环境启动方案

开发环境深度依赖本地的上游 `static-site-graph` 引擎库。

```powershell
# 1. 激活本地虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 以 editable 模式挂载上游框架引擎
python -m pip install -e D:\code\github\hicancan\static-site-graph[dev]

# 3. 安装本实例的依赖
python -m pip install -e .[dev]
```

### 标准校验流

通过以下 CLI 命令可针对目标学院（如 JWC 教务处）进行增量开发与模型验证：

```powershell
# 语法级模型审计 (Schema Validation)
python -m sitegraph.cli validate-config configs/sites/jwc/site.yaml

# 局部拓扑探查与导航树导出 (Dry-run Discovery)
python -m sitegraph.cli discover-homepage configs/sites/jwc/site.yaml --out data/sites/jwc/index/nav_tree.generated.json
```

---

## 🎯 管线完备性准则 (Completion Target)

一个标准的站点被认为“接入完毕”，必须满足以下绝对准则：
1. **模型覆盖率**：主页、导航、专栏、列表、分页、详情、附件以及外部游离边（Edge）均被 YAML 拓扑模型涵盖。
2. **零容忍遗漏**：引擎发现的任何一个 URL 都能在其生成的 Manifest 中找到对应的最终归宿分类。
3. **实机验证**：该站点的特异性页面族均经过本地 Headless Chrome 提取验证。
4. **契约达标**：导出的 Package 结构完全满足 `njupt-search` 下游二进制重编译的 Type 约束。
