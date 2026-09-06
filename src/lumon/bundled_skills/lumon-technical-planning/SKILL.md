---
name: lumon-technical-planning
description: 用于技术规划：结合需求、代码和历史背景产出可审阅的 Technical Plan。
---

# 技术规划

这个 Skill 用于在业务目标和验收边界明确后，基于真实代码和项目上下文形成
可审阅的 Technical Plan。它适用于使用 JIRA 的项目，也适用于没有 JIRA 的纯本地
项目。规划完成前不得开始实现。

## 先判断上下文模式

开始调查前，读取当前 Workspace 的 `AGENTS.md`，并根据以下证据选择一种模式：

### JIRA 模式

仅在用户提供 JIRA Key/URL、`AGENTS.md` 明确要求使用 JIRA/TWG，或 Workspace
已有明确的 JIRA/TWG 配置时进入此模式。

1. 在提出技术结论前，使用 TWG CLI 读取完整的 JIRA 工作项：

   ```text
   twg jira workitem get <JIRA-KEY> --full -o json
   ```

2. 使用 TWG CLI 可用的查询命令探索相关业务背景、评论、链接、附件、历史工作项、
   相关 Story、Pull Request 或其他项目记录。先查看 `twg --help` 和当前子命令
   帮助，不猜测未确认的命令参数。
3. 检查 JIRA 上下文涉及的当前代码仓：实际模块、配置、公共契约、数据存储、
   集成、测试和 Git 历史。TWG 的项目记录不能替代本地代码事实。
4. JIRA 是业务目标与验收的权威来源；本地代码是当前实现的权威证据；Git 历史
   用于理解变更背景，不用于推断未确认的需求。
5. 如果明确存在 JIRA 但 TWG CLI 不可用，说明无法完成 JIRA 证据读取；只有用户
   明确同意后，才可以基于已有资料继续，并标记证据缺口。

### 独立项目模式

没有上述 JIRA 证据时，不调用 TWG，不要求 JIRA Key，也不假设存在外部项目管理
系统。使用以下资料完成规划：

- 用户确认的 Story 或需求
- Workspace 内的 `AGENTS.md` 和用户提供的文档
- 当前代码仓的实际代码、配置、测试、构建文件和 Git 历史

独立项目模式下，Technical Plan 保留在当前对话中；只有用户明确要求时，才写入
指定文件。不得为了填补流程而创建 JIRA 或伪造外部状态。

## 基于 Code Base 的访问与分析

只要当前环境存在可访问的代码仓，Technical Planning 必须先以真实 code base 作为
实现事实的主要来源，再提出问题或形成设计结论。调查要围绕实际请求收敛，不要求扫描
无关仓库或所有历史：

- 先确认真正受影响的仓库和入口，再检查相关模块、公共接口、配置、数据结构、外部
  集成、测试、构建 / 运行方式和必要的 Git 历史。
- 先用代码、测试和历史回答“现在是什么”；不要把本可以查到的事实变成用户问卷，
  也不要根据命名或习惯猜测未知契约。
- 澄清问题应从“现有实现”和“目标需求”的差异中产生，并在问题前简要列出相关的
  现状证据；选项要说明对模块边界、接口、数据、验证或实现顺序的影响。
- 明确区分已确认事实、用户选择、合理假设和证据缺口。若 code base 不可访问或没有
  相关实现，必须说明缺少代码证据，并基于现有资料继续保持草稿，不得假装完成分析。

## 调查要求

在写计划前，根据实际范围检查：

- 受影响的模块、入口、公共接口和调用关系
- 配置、数据结构、持久化、外部集成和权限影响
- 同类实现、现有约定、错误处理和并发/异步行为
- 现有测试、架构约束、构建命令和可执行的验证方式
- 相关 Git 历史，以及 JIRA 模式下由 TWG 找到的业务和历史记录

只记录会影响设计的事实，不罗列每个私有函数或未变化的文件。

## 澄清访问（Clarification Interview）

完成上下文读取和代码调查后，先判断是否存在会改变技术边界、公共契约、数据行为、
权限、时序、失败处理、验收方式或实现顺序的未决问题。这个环节同时适用于 JIRA 项目
和纯本地项目。

- 尽可能在同一轮列出所有已经从 code base / 需求差异中识别、且互不依赖的高影响问题，
  让用户一次回答；不要把可以同时回答的问题拆成多轮。
- 如果问题依赖另一个答案，先询问前置问题，收到回答后再继续下一轮；不要基于未确认
  的选择提前写死后续设计。
- 每个问题使用 A、B、C 选项，说明选项影响，并在证据充分时标记推荐项；允许用户直接
  给出自定义答案。格式例如：

  ```text
  1. <需要确认的问题>
  A. <选项 A>（推荐）
  B. <选项 B>
  C. <选项 C>
  影响：<不同选择会改变什么>
  ```

  用户可以用类似 `1A，2C` 的方式一次回答，也可以用自然语言覆盖选项。
- 不询问已经被 JIRA、AGENTS.md、实际代码、测试或 Git 历史明确解决的问题；证据不足
  时要明确指出缺口，不得用猜测填补。每个问题都应尽量回指相关现状，而不是成为脱离
  code base 的通用问卷。
- 收到回答后，只记录确认过的技术决策和仍然有效的假设；在高影响问题未解决前，
  Technical Plan 保持草稿状态。若问题实质上改变了业务目标、参与者或验收边界，先
  回到 Story Planning 澄清。

## JIRA Comment 写入与 Repository Mapping

JIRA 模式下，Technical Plan 的规范存储位置是当前工作项的 **Comments**，不是
Description：

- 细化阶段只把 Technical Plan 保留在当前会话中，不提前写入 JIRA。
- 用户明确批准后，使用可用的 JIRA / TWG CLI comment 操作创建或更新一条规范的
  Technical Plan Comment；Comment 正文使用 Markdown，并以 `## Technical Plan` 作为
  顶层标题。
- 如果当前工作项已经有规范的 Technical Plan Comment，应更新它而不是重复创建；不要
  改写无关的 Comments 或 Description，也不要在本地创建同步镜像。
- 写入前重新读取当前工作项；如果期间发生人工修改，先重新分析、澄清并获得批准。写入
  后再次读取并确认 Comment 内容和 Repository Mapping 正确。
- 如果 Technical Plan 包含图表，Comment 中增加 `### Architecture / Diagrams`，保留
  图表类型、目的、source of truth 和简短的结构化文字摘要；渲染后的 PNG 必须通过
  Jira 原生附件 / 媒体能力嵌入这条 Comment。不要把 raw HTML、inline SVG 或本地文件
  路径直接贴进 Comment。
- 图表源文件（HTML / Draw.io）默认保留为当前会话 artifact；只有用户明确需要时才作为
  补充附件上传。上传后必须重新读取 Jira，确认 Comment 中实际显示了图片；如果原生媒体
  能力不可用，只能报告“图片未嵌入”，不得声称 Jira 已展示图表。

每条写入 JIRA 的 Technical Plan Comment 都必须包含 Repository Mapping：

```markdown
## Technical Plan

### Goal
<observable technical outcome>

### Scope and Boundaries
- <in scope>
- <out of scope>

### Repository Mapping
- `<repository-name-that-will-change>`

### Architecture / Diagrams（仅当需要时）
- **Type:** UML Class Diagram / Sequence Diagram / Component Diagram / State Diagram
- **Artifact:** `technical-plan-uml.html`; PNG: `technical-plan-uml.png`
- **Purpose:** <the relationship or flow this diagram makes reviewable>
- **Source of truth:** <current code, approved requirement, or explicit assumption>
- **Jira presentation:** <PNG embedded through Jira native media in this Comment>
```

Repository Mapping 只列本次 Story 实际需要修改的 repository 的规范名称，不列仅用于
参考或调查的 repository，也不列路径、分支、runtime 或自动化配置。若涉及多个 repository，
逐项列出；如果没有代码变更，明确写 `None`。无法从 Workspace、JIRA 或实际 Git 仓库
明确解析名称时，保持草稿并向用户提问，不得从计划正文猜测。

纯本地项目也在会话中的 Technical Plan 草稿里保留相同的 Repository Mapping；只有用户
明确指定写入位置并批准后，才写入本地文档。

## Architecture / Diagrams

Technical Planning 支持按需产出图表。是否画图由设计复杂度决定，不因为模板存在就为
每个小改动强制添加图表；但如果图表能显著降低用户 review 成本，就必须产出并先让用户
审阅。

- 涉及新类、接口或模块之间的职责和关系时，优先使用 UML Class Diagram。只呈现设计级
  的 public/shared class、interface、关键属性或方法、继承 / 实现 / 组合 / 依赖关系，
  以及必要的 repository boundary；不要把所有 private helper 和局部变量画进去。
- 涉及跨模块调用或外部集成时，使用 Sequence Diagram 或 Component Diagram；涉及状态、
  异步处理、重试、恢复或分支流转时，使用 State Diagram 或 Process Flow。
- 图中必须区分“现有实现”和“拟议设计”，并标出来源、用户确认的决策、合理假设和未决
  问题。图表不能替代接口、数据、错误和验证说明。
- 使用可用的 `cloudy-tech-diagrams` Skill 生成 browser-ready HTML、inline SVG 和 PNG；
  Mermaid 代码块或 ASCII 图只能作为文字备份，不能声称它们是已经呈现的图表。
- 生成后先完成渲染、重叠 / 裁切 / 端点检查和可用导出检查，再把图表交给用户 review。
  图表中的设计关系发生实质变化时，需要重新审阅 Technical Plan。

## Technical Plan 内容

根据实际需要使用以下结构，省略不适用的部分：

```markdown
### Goal
### Scope and Boundaries
### Repository Mapping
### Architecture / Diagrams（仅当需要时）
### 上下文与证据
### 设计决策
### 模块与接口
### 数据、配置与契约
### 实现步骤
### 验证方式
### 风险与未决问题
```

要求：

- 每个设计决策说明问题、选择和结论。
- Technical Plan 必须列出本次实际变更涉及的 repository；JIRA 模式写入 Comments 时也
  必须保留同一份 Repository Mapping。
- 如果使用图表，必须记录图表类型、目的、source of truth、artifact 名称和完成的视觉
  验证；涉及新类关系时优先记录 UML Class Diagram。
- 每个模块定义清晰的 Interface、输入输出、不变量和错误模式。
- 优先设计深模块：让调用方学习较少的 Interface，把复杂度隐藏在实现内部。
- API、事件、配置、命令和数据载荷使用明确的代码块描述。
- 将每一条已确认的验收标准映射到一个可观察的验证方式。
- 新增抽象前先确认是否存在两个真实实现需要同一个 Seam；不要预先创建通用
  Adapter、Registry 或工具层。
- 对未知的代码事实、数据结构或外部契约明确标记未知，不得猜测。
- 如果涉及 UI，先确认已有页面、设计系统、截图或其他视觉参考，并写明验证范围。

## 审批与写入规则

Technical Plan 始终先作为当前会话草稿供用户审阅。只有用户明确批准后，才可以：

- 在 JIRA 模式下，通过 TWG CLI 写入或更新规范的 Technical Plan；写入前重新读取
  工作项，避免覆盖人工修改。规范内容必须写入当前工作项的 Comments，不得写入
  Description，并且必须包含 Repository Mapping。
- 在独立项目模式下，写入用户明确指定的文档或项目位置。
- 进入实现阶段或授权其他 Agent 修改代码。

批准前不得修改应用源代码、配置、测试或 Workspace 的 `AGENTS.md`。

## 约束

- 这是规划 Skill，不是实现 Skill。
- 不把 JIRA、TWG 或任何外部系统变成 Lumon v1 CLI 的运行时依赖。
- 不因为项目没有 JIRA 而跳过业务背景、代码调查、历史分析或验收设计。
- 不把 Repository Mapping、分支、运行时配置或未参与变更的仓库塞进计划。
- 不添加没有实际价值的图表、迁移、集成、性能指标或发布步骤。
