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
- 在启动 Agent CLI 前保存实际发送的完整 Prompt，便于分析 Mark 当时看到的上下文。

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

持久化状态写入：

```text
$LUMON_HOME/mark.sqlite3
```

## Session 与完整 Prompt

Mark 的 Session 边界是稳定的：

- 私聊使用 Feishu `chat_id`，同一私聊不会因为消息带有不同的 thread metadata 而拆成多个 Session。
- 群聊优先使用 Feishu `thread_id`，没有时使用 `root_id`，最后使用根消息 ID；同一 Thread 内的消息会进入同一个 Session。
- Session ID、消息和 Run 都写入本地 SQLite，服务重启后仍按同一边界恢复历史。

每次真正调用 Agent CLI 时，Lumon 会先把完整 Prompt 写入对应的 `runs` 记录，随后才启动外部进程。Prompt 记录与该次执行的
`run_id`、`session_id`、Provider、Workspace、最终状态和结果关联。Prompt 包含：

1. 包内或用户覆盖的 `SOUL.md`。
2. Workspace 的 `AGENTS.md`、身份信息、Repository metadata 和路径信息。
3. 当前 Session 的有限历史消息。
4. 当前用户消息以及执行约束。

这是为分析 Agent 视角保留的本机审计数据，不会出现在日志、CLI 输出、诊断结果或飞书回复中。由于 Prompt 可能包含工作区中的敏感上下文，完整记录只保存在 `$LUMON_HOME/mark.sqlite3`，文件和父目录分别限制为当前用户可读写（`600` / `700`）。不要把该数据库同步到外部系统。

当前 SQLite 主要表：

| 表 | 用途 |
| --- | --- |
| `sessions` | 保存私聊或群组 Thread 的稳定 Session 身份、边界和最近活动时间 |
| `events` | 保存飞书事件去重、入队和恢复状态，并关联 Session |
| `messages` | 保存用于上下文连续性的入站与出站消息 |
| `runs` | 保存一次实际 Agent 调用的状态、Provider、完整 Prompt 和安全后的最终结果 |

`runs` 的一行对应一次 Agent CLI 调用，不对应 Agent 内部执行的每一条命令；命令和文件操作事件不会各自产生新的 Run。

Mark 的默认 SOUL 位于安装包中：

```text
lumon/agents/mark/SOUL.md
```

用户可以创建覆盖文件来加入本机规则：

```text
$LUMON_HOME/agents/mark/SOUL.md
```

Lumon 只读取现有覆盖文件，不会自动覆盖或升级它。

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
