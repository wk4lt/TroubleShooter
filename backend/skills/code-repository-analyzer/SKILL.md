---
name: code-repository-analyzer
description: >-
  基于 CodeGraph 的源码事实与 OpenViking 的技术文档语义分析代码仓；
  支持符号定位、调用链、依赖/影响分析，以及设计文档与实际实现的证据化对照。
---

# Code Repository Analyzer

用于分析已由 CodeGraph 建立索引、且其技术文档已导入 OpenViking 的代码仓库。默认 Demo 是
OpenViking 官方仓库。**不要自行扫描整个工作区、重建代码索引、实现 Parser、RAG 或 Vector DB。**

## 工具边界

| 工具 | 只用于 | 不用于 |
| --- | --- | --- |
| CodeGraph MCP (`mcp__codegraph__*`) | 源码文件、symbol、类、函数、实现位置、caller/callee、调用链、依赖、影响范围 | 从 README 或设计文档推断实际代码 |
| `search_knowledge`（官方 OpenViking） | Architecture、Design Doc、README、ADR、API 文档、开发指南、需求与约束 | 源码结构、函数调用关系或实现定位 |

CodeGraph 是实际代码事实的唯一优先来源；OpenViking 是设计和知识语义的唯一优先来源。
若服务器公开的 CodeGraph 工具名称或参数与下列示例不同，以工具 schema 和 description 为准。

## 路由规则

先按用户问题分类，再只调用必要工具：

1. **纯代码实现问题**（入口、实现、调用链、caller/callee、依赖、影响、异常、配置读取）：先调用 CodeGraph。通常用 `orient` 缩小范围，`search` 找候选，`get_symbol`/`goto` 找定义，`refs` 查引用，`path` 查链路，`deps`/`rdeps` 查依赖；仅在需要核对局部实现时用 `get_file`。
2. **纯设计/文档问题**（设计意图、架构职责、ADR、规范）：只调用 `search_knowledge`，并保留每条命中的 URI。不要以代码细节替代文档答案。
3. **设计与实现对比问题**（“是否符合”“是否实现”“模块边界是否被破坏”）：必须先或并行调用 `search_knowledge` 提取设计要求，再调用 CodeGraph 取得实现事实，最后逐项对照。两类证据任一不足时标为 `UNKNOWN`，不得猜测。

对于未明确仓库范围的问题，先用 CodeGraph 的 `orient`/`search` 确认范围；不要把用户上传文件当作 Demo 源码仓。对可能随分支或索引版本变化的结论，记录每个 CodeGraph 结果附带的 freshness，必要时调用 `refresh_index`。

## 代码问题工作流

1. 把问题改写成可检索的 symbol、模块或入口词。
2. 用 CodeGraph 获取候选文件/符号；对同名符号以 package、文件路径和语言消歧。
3. 按问题类型继续查询：
   - 实现/位置：`search` → `get_symbol` 或 `goto` → 必要时 `get_file`；
   - 调用链：入口 symbol → `path`，必要时用 `refs` 交叉验证 caller/callee；
   - 依赖/影响：`deps` / `rdeps` + `refs`；范围级变更可用 `impact`，并区分直接和间接影响；
   - 异常/配置：先找声明/读取点，再沿调用或引用关系查传播和使用点。
4. 回答中列出路径、symbol、关系方向和关键调用链。无法确定时说明遗漏的是哪一种证据。

## 设计 + 代码联合工作流

1. 用 `search_knowledge` 查询模块名和设计关键词（例如 `Retrieval architecture`、`ResourceService design`）。记录 URI、标题/片段和其中可验证的职责、流程、约束。
2. 将每条可验证要求转为 CodeGraph 查询：相关 module/symbol、入口、调用关系或依赖边。
3. 用 CodeGraph 获得代码证据；不要把文档名、注释或命名本身当作实现证据。
4. 按下表输出。每个判断都必须同时给出文档 URI 与文件/符号；缺少任一侧证据时为 `UNKNOWN`。

| 设计要求 | 文档证据 | 代码证据 | 判断 |
| --- | --- | --- | --- |
| `<requirement>` | `<OpenViking URI + 摘要>` | `<path>::<symbol> + 调用/依赖事实>` | `COMPLIANT` |

判断枚举仅可使用：

- `COMPLIANT`：代码证据满足明确的文档要求。
- `PARTIALLY_COMPLIANT`：仅满足部分明确要求，说明缺口。
- `NON_COMPLIANT`：代码证据与明确要求相矛盾或缺少要求的实现。
- `UNKNOWN`：证据不足、索引不完整或需求不够明确。
- `DOCUMENT_OUTDATED`：代码有充分、可追溯证据表明文档已过时；不要只因实现更复杂就使用此结论。

## 输出要求

先给简短结论，再给证据。纯代码问题至少给出 `CodeGraph` 的文件路径与 symbol；调用/影响问题还要给出 caller、callee 或依赖方向。文档问题至少给出 OpenViking URI。联合对比必须给出上面的对照表，并单列未验证项与索引/文档限制。

不要编造文件、symbol、调用关系、文档内容或 URI。工具失败、未配置或没有命中时，直接说明失败原因和下一步需要的索引/导入操作。
