# Lumon Workspace

本文件定义 Lumon Workspace 中来自飞书 Agent任务的执行、验证与交付规则，如果任务来自 Auto Scan / Auto Delivert / Auto Patch，则本文件仅作参考，请以对应 Flow 的要求为准
## Workspace 结构

* Capability：`lumon/capabilities/`
* Flow：`lumon/flows/`
* Workspace 身份与初始化记录：`lumon/manifest.json`
* 注册的代码仓库：`repos/`
* 运行时目录：

  * `lumon/runs`
  * `lumon/artifacts`
  * `lumon/logs`
  * `lumon/tmp`
* 全局 Agent Skill 位于 `~/.agents/skills/`，不要复制到 Workspace。
* 禁止将密钥、Token、私钥、Webhook 或其他凭据写入 Workspace。
## 任务处理

1. 读取：

   * `AGENTS.md`
   * `lumon/manifest.json`
   * `lumon/workspace.toml`

2. 根据以下信息确认任务范围、关键对象与所需证据：

   * 当前请求与对话
   * Workspace 文件
   * 已注册 Capability
   * 明确属于当前任务的来源
3. 如果消息是来自私聊且是卡片类型（比如飞书的邮件），那么可以跳过处理这条消息，因为通常用户会再发一条具体的文字消息要求你进行处理
4. 如果你对用户问题存在疑问，先进入“证据与澄清”环节


6. 把 Workspace 下的 Repository 同步到最新，如果同步出现冲突或是其他异常，则以远端为准，必要情况下允许舍弃本地改动
8. 过程中请不要输出本地 File Path 到飞书消息中
## 证据与澄清
请从以下内容确认核心证据：

* 当前请求或对话
* Workspace 内的 Project
* 尝试使用已注册 Capability 进行调研
* 明确授权使用的 Feishu Document、Email、Jira、TWG、Confluence 等来源


如果经由以上还是存在无法确认的问题点：


2. 说明已检查的证据与缺失信息。
3. 从专业咨询师的角度用易懂的语言一次性提出你的问题，
必要时提供对应的选项，多问题的情况下可以引导用户通过 1A, 2A, 3C 的方式进行回答：

* **A**：提供 Jira / TWG / Confluence 链接或 Issue key
* **B**：提供本地文件、路径或业务定义
* **C**：授权基于明确假设生成通用草稿

如果缺失信息不会改变任务方向，可以基于明确标注的假设继续，并记录其影响。已经有证据确认的事实不要重复询问。

## 代码修改隔离

将 `repos/` 下的 canonical checkout 视为只读。

所有代码修改、测试和提交均在独立 worktree 中完成：

`<workspace>/lumon/worktrees/<task-key>/<repository>/`

规则：

* 从 Repository 配置的基准分支创建：
  `lumon/<task-key>/<repository>`
* 不要假设基准分支一定是 `master`，有可能是 `main`
* task-key 如果不存在，则可以由你进行生成
* 如果你发现可复用的 worktree，则可以不需要创建，基于既有 worktree 进行任务
* worktree dirty 或状态不一致时，报告冲突、影响和建议方案后再继续
* Workspace 自身的 Flow 和 Capability 可以进行修改或调整
* 开始变更前，如果用户未明确变更的提交方式，需要进行询问进行确认，我们的提交方式就两种：主分支提交 和 feature 分支提交并开 PR

任务进入终态，且验证和发布决策已记录并提交更动，随后可删除 worktree。

以下情况不得删除：

* 存在未提交或未跟踪改动
* 验证未完成
* 发布决策待定
* 用户明确要求保留

删除 worktree 时保留对应分支、提交或 PR。

## 验证策略

修改代码前，先读取 Repository 中与执行和验证相关的资料，例如：

* `AGENTS.md`
* README
* CI 配置
* 项目清单
* 锁文件
* 可用脚本

验证原则：

* 优先使用 Repository 已有虚拟环境、工具链、锁定依赖和官方 bootstrap 命令
* 禁止全局安装依赖或无必要修改锁文件
* 不得把环境失败描述为代码验证通过
* 如果受环境因素影响，可以降级只验证语法层面

验证顺序：


3. 静态检查
4. 语法、导入或编译检查

5. 相关目标测试

5.  完整可行的测试或检查

记录：

* 实际环境
* 执行命令
* 成功 / 失败 / 跳过
* 跳过或失败原因

“未运行”或“仅完成语法检查”不得写成“测试通过”

如果用户要求发布，但只能完成降级验证，先说明现有风险，获得确认后可以 commit 或 push。
## 提交与发布


提交前：

1. 读取目标 Repository 的：

   * `AGENTS.md`
   * 提交配置
   * 近期非 merge、非 release 提交历史

2. 匹配已有提交风格，包括：

   * 语言
   * type / scope
   * 前缀
   * Issue key 位置
   * 标点
   * 长度

3. 不复用旧 Issue key，不在 subject 中提及 AI。

4. 如果历史提交包含 author 前缀，使用小写 `lumon`，例如 `[lumon]`；否则不要自行增加。

5. 不修改 Git author 或 committer 配置。


提交时：

* 只暂存当前任务文件
* 保留无关 staged / unstaged 改动
* 排除凭据、Prompt、临时文件、IDE 文件及无关生成物

发布规则：

* PR 模式：推送隔离分支并创建 PR
* 直接更新基准分支：直接推送到主分支
* 推送变更时需要忽略 git hook
## 阻塞与任务续接

遇到以下情况时视为阻塞：

* 关键上下文缺失或存在歧义

* 验证失败或不完整
* Repository 状态异常
* 发布目标不明确
* 外部系统或权限阻碍

发生阻塞时：

1. 说明已有证据、阻塞原因与影响
2. 提供 2–3 个可执行方案，并标出推荐方案
3. 等待用户决定期间，不得：


   * 全局安装依赖
   * 丢弃用户改动
   * commit
   * push
   * 删除 worktree

缺少关键业务对象属于“需要澄清”，不能用通用证据或未标注假设代替。

同一私聊或群聊 Thread 中的重复请求视为同一任务续接。开始前先检查已有任务状态。

如果上一任务失败或等待决策，先报告当前状态，并提供：

* `resume`
* `retry`
* `discard`

不要自动重复可能产生副作用的操作。

代码任务进入 worktree 后，canonical checkout 始终保持不变。

## Shell 与命令约定

* 使用用户配置的 Shell；macOS 默认可能为 zsh，可探索 ~/.zshrc 下的相关配置
* 不要使用 zsh 的特殊或只读参数名作为变量，尤其是 `status`
* 建议使用：

  * `repo_state`
  * `worktree_state`
  * `branch_state`
* Repository 检查命令尽量保持 POSIX 兼容
