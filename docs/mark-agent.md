# Mark Agent

Mark 是 Lumon 的本地 Workspace Agent。它通过飞书 WebSocket 长连接接收消息，
把当前用户选定的 Workspace 作为本地 Agent CLI 的工作目录，并把进度与最终回答
回复到原来的聊天线程。当前唯一实现是 Codex；Mark 本身只依赖通用的
`AgentRunner`、`AgentResult` 和 provider-neutral 错误码，因此未来替换 CLI 时不需要
改动消息、Workspace 或 SQLite 流程。

## 当前能力

- 私聊消息直接处理。
- 群聊消息只有在明确 `@Mark` 时处理。
- 使用配置的默认 Workspace；只有一个已注册 Workspace 时可以自动选择。
- 读取 Workspace 根目录的 `AGENTS.md`、`lumon/manifest.json`、
  `lumon/workspace.toml` 和 Repository metadata。
- 使用当前配置的 Agent CLI 完成用户明确提出的 Workspace 内分析、命令和文件操作；
  v1 的具体实现使用本机 Codex CLI 的 `codex exec --json`。
- 发送简短进度消息和一条最终回答。
- 使用本地 SQLite 做 Session、消息去重、历史记录、运行结果和中断恢复。
- 首次调用保存完整 bootstrap Prompt；后续调用复用 Codex 原生 Session，只发送新的用户消息，减少重复上下文。

## Codex 工具与输出策略

Codex 不是 Mark 的专属模块。共享的执行工具位于：

```text
lumon/tools/codex.py
```

它只负责在指定 Workspace 中启动本机 Codex、读取 JSONL 事件、返回执行状态、
安全后的文本和文件/命令事件。它不负责发送消息，也不要求必须产生最终文本。
因此 Auto Scan、Auto Delivery 等 Flow 可以只检查执行状态或消费文件变化，忽略
文本输出。

Mark 的对话适配器位于 `lumon/agents/mark/runner.py`。它调用共享的
`CodexTool`，把命令/文件事件转换为聊天进度，并额外要求有可回复的最终文本；
没有最终文本时，才由 Mark 转换为 `EMPTY_RESULT`。这样聊天输出策略不会反向
污染其他 Flow。

Mark 不会因为打开 Dashboard 自动启动；必须明确运行 `lumon agent start`。

## 配置

先准备一个已安装且可用的飞书机器人应用：

1. 在飞书开发者后台创建 Bot 应用。
2. 开启事件订阅，并选择 WebSocket 事件订阅方式。
3. 订阅 `im.message.receive_v1`。
4. 授予机器人接收和发送消息所需的权限，并重新安装或更新租户内的应用。

配置 Mark：

```text
lumon agent configure
```

命令会交互式收集 App ID、App Secret 和默认 Workspace ID。配置写入：

```text
$LUMON_HOME/agent.toml
```

没有设置 `LUMON_HOME` 时使用 `~/.lumon/agent.toml`。App Secret 会以明文保存在
owner-only 的 `600` 文件中；Lumon 不会把它写入 Workspace、日志、CLI 输出或飞书
消息。运行前请确保本机用户目录本身受到保护。

Codex CLI 默认使用 GPT-5.6 Luna 和 `max` reasoning effort。对应的配置项是：

```toml
agent_model = "gpt-5.6-luna"
agent_reasoning_effort = "max"
```

直接编辑 `$LUMON_HOME/agent.toml`（默认 `~/.lumon/agent.toml`）即可更改模型或
reasoning effort；`lumon agent configure` 会保留已有设置。运行
`lumon agent doctor` 可以确认当前生效的模型与 effort。

## Langfuse Cloud 可观测性（可选）

Mark 可以把每条已处理的飞书消息记录为一个 Langfuse trace。该能力默认关闭，
并且不会阻止 Agent 执行：Langfuse SDK 不可用、凭据缺失或发送失败时，消息仍按
原有流程处理。

开发环境通过 uv 安装可选依赖：

```text
.venv/bin/uv sync --dev --extra observability
```

Shell 安装则使用安装器选项：

```text
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/release/packaging/install.sh | bash -s -- --observability
```

在 Langfuse Cloud 创建项目并生成 project API keys，然后把凭据放在运行 Agent 的
进程环境中。不要把它们写入 `agent.toml`、Workspace、日志或 commit：

```text
export LANGFUSE_PUBLIC_KEY='pk-lf-...'
export LANGFUSE_SECRET_KEY='sk-lf-...'
```

编辑 `$LUMON_HOME/agent.toml` 开启 Cloud trace。`base_url` 可以换成组织所需的
Langfuse Cloud 区域地址，默认值是 `https://cloud.langfuse.com`：

```toml
[observability]
enabled = true
provider = "langfuse"
base_url = "https://cloud.langfuse.com"
capture_content = false
sample_rate = 1.0
```

运行 `lumon agent doctor` 会显示 endpoint、content capture、sample rate、SDK
安装状态和凭据是否存在；它只输出 presence，不输出 key 的值。启动前台或后台
Agent 时，确保这两个环境变量仍然对该进程可见。

默认的 `capture_content = false` 只导出 trace 和 span 元数据，不导出原始消息、
Workspace context、rendered Prompt 或最终回复。启用 `capture_content = true` 后，
Lumon 会在客户端先遮盖已配置的 App/API secrets、Bearer token、密码、私钥和常见
key 格式，再把入站消息、rendered Prompt 和最终回复交给 Langfuse SDK；只有在确认
metadata 视图不足时才建议打开它。

每条 trace 使用 Feishu 对话的 Session ID 做多轮分组，并记录 Lumon run/event ID、
Workspace ID、Provider、实际模型、reasoning effort、版本、结果状态、安全错误码和
SDK 记录的耗时。当前 Codex 是子进程，因此 trace 表示 Codex execution boundary，
不会伪造 token usage、cost 或 Codex 内部模型调用数据。常见的子 span 包括
`workspace.resolve`、`history.load`、`prompt.build`、`codex.exec` 和
`feishu.reply`。

Pilot 验证流程：

1. 在 Cloud 项目中确认 API keys 和 endpoint。
2. 先保持 `capture_content = false`，运行 `lumon agent doctor` 和 `lumon agent start`。
3. 从 Feishu 发送几条私聊或群聊测试消息。
4. 在 Langfuse UI 检查 trace tree、Session grouping、model/reasoning metadata、耗时、失败状态和 error code。
5. 确认 metadata-only trace 没有原始消息或未遮盖内容后，再按需启用 redacted content capture。

持久化状态写入：

```text
$LUMON_HOME/mark.sqlite3
```

## Session 与 Codex 原生 Session

Mark 的 Session 边界是稳定的：

- 私聊使用 Feishu `chat_id`，同一私聊不会因为消息带有不同的 thread metadata 而拆成多个 Session。
- 群聊优先使用 Feishu `thread_id`，没有时使用 `root_id`，最后使用根消息 ID；同一 Thread 内的消息会进入同一个 Session。
- Lumon Session ID、Codex 原生 Session ID、消息和 Run 都写入本地 SQLite，服务重启后仍按同一边界恢复。

每个 Lumon Session 的第一条消息会启动一个新的 Codex 原生 Session，并把完整 bootstrap Prompt 写入对应的 `runs.prompt_text`，随后才启动外部进程。bootstrap Prompt 包含：

1. 包内或用户覆盖的 `SOUL.md`。
2. Workspace 的 `AGENTS.md`、身份信息、Repository metadata 和路径信息。
3. 当前 Session 的有限历史消息。
4. 当前用户消息以及执行约束。

当同一个 Session 收到后续消息时，Lumon 执行 `codex exec resume <codex-session-id>`，只把新的用户消息作为本轮输入，不再重新发送 SOUL、Workspace 规则或完整历史。后续 Run 的 `prompt_text` 保存实际发送的这段增量输入；原始完整 bootstrap Prompt 仍保留在第一条 Run 中，Codex 原生 Session 负责维护后续上下文。

一个 Lumon Session 只绑定一个 Codex 原生 Session：私聊按 `chat_id` 绑定，群聊按 Thread 绑定，互不共享。如果 Workspace 发生变化，或原生 Session resume 失败，Lumon 会清除绑定；当前失败请求不会自动重试，下一条消息会重新发送 bootstrap Prompt，避免重复执行用户动作。

这是为分析 Agent 视角保留的本机审计数据，不会出现在日志、CLI 输出、诊断结果或飞书回复中。由于 Prompt 可能包含工作区中的敏感上下文，完整记录只保存在 `$LUMON_HOME/mark.sqlite3`，文件和父目录分别限制为当前用户可读写（`600` / `700`）。不要把该数据库同步到外部系统。

Langfuse telemetry 与本机审计是两条边界：telemetry 默认关闭；开启后默认只发送
上述 metadata。只有显式设置 `capture_content = true` 时，客户端脱敏后的内容子集才
会进入 Langfuse Cloud。

当前 SQLite 主要表：

| 表 | 用途 |
| --- | --- |
| `sessions` | 保存私聊或群组 Thread 的稳定 Session 身份、Workspace 绑定、Codex 原生 Session ID 和最近活动时间 |
| `events` | 保存飞书事件去重、入队和恢复状态，并关联 Session |
| `messages` | 保存用于上下文连续性的入站与出站消息 |
| `runs` | 保存一次实际 Agent 调用的状态、Provider、实际发送的 Prompt（首轮为完整 bootstrap，后续为增量输入）、安全后的最终结果，以及异常阶段/类型/源码位置（不保存异常文本） |

`runs` 的一行对应一次 Agent CLI 调用，不对应 Agent 内部执行的每一条命令；命令和文件操作事件不会各自产生新的 Run。

Mark 的默认模板集中位于安装包中：

```text
lumon/agents/mark/templates/
├── SOUL.md
└── workspace_prompt.md
```

用户可以创建覆盖文件来加入本机规则：

```text
$LUMON_HOME/agents/mark/templates/SOUL.md
```

Lumon 只读取现有覆盖文件，不会自动覆盖或升级它。为兼容旧版本，旧路径
`$LUMON_HOME/agents/mark/SOUL.md` 仍会作为回退路径读取，但新配置应使用
`templates/SOUL.md`。

## 运行与检查

建议先检查：

```text
lumon agent doctor
lumon agent doctor --json
```

doctor 会检查配置权限、Channel SDK、Agent CLI、Agent 登录状态、默认 Workspace、
运行目录和 SQLite 权限；当前检查的具体 CLI 是 Codex，不会输出 App Secret。

前台运行：

```text
lumon agent start
```

后台运行：

```text
lumon agent start --background
lumon agent status
lumon agent stop
```

Mark 当前使用 `full_access` 的 Agent 执行模式，具体由 Codex runner 实现。它允许
用户通过飞书明确要求的 Workspace 内命令和文件操作直接执行；因此不要把密码、Token、Webhook、私钥等
敏感信息放进 Workspace，也不要在不清楚影响时要求 Mark 执行删除、重置、发布或
推送等高影响动作。

## 测试边界

自动化测试使用 fake Channel 和 provider-neutral fake Agent runner，不访问真实飞书或
执行真实 Workspace 动作。真实验收需要在已配置飞书 Bot、已登录 Codex 的本机运行：

```text
lumon agent configure
lumon agent doctor
lumon agent start
```

随后私聊 Mark，或在群里 `@Mark` 提出一个读取当前 Workspace README/Repository
结构的问题，检查进度、Workspace 选择、最终回答和重复消息去重。

官方 Channel SDK 参考：

- https://github.com/larksuite/channel-sdk-python
- https://github.com/larksuite/channel-sdk-python/blob/main/docs/quickstart.md
