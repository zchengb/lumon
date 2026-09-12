# Mark Agent

Mark 是 Lumon 的本地 Workspace Agent。它通过飞书 WebSocket 长连接接收消息，
把当前用户选定的 Workspace 作为 Codex 的工作目录，并把进度与最终回答回复到
原来的聊天线程。

## 当前能力

- 私聊消息直接处理。
- 群聊消息只有在明确 `@Mark` 时处理。
- 使用配置的默认 Workspace；只有一个已注册 Workspace 时可以自动选择。
- 读取 Workspace 根目录的 `AGENTS.md`、`lumon/manifest.json`、
  `lumon/workspace.toml` 和 Repository metadata。
- 使用本机 Codex CLI 的 `codex exec --json` 完成用户明确提出的 Workspace 内分析、
  命令和文件操作。
- 发送简短进度消息和一条最终回答。
- 使用本地 SQLite 做消息去重、历史记录、运行结果和中断恢复。

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

doctor 会检查配置权限、Channel SDK、Codex CLI、Codex 登录状态、默认 Workspace、
运行目录和 SQLite 权限；不会输出 App Secret。

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

Mark 当前使用 `full_access` 的 Codex 执行模式。它允许用户通过飞书明确要求的
Workspace 内命令和文件操作直接执行；因此不要把密码、Token、Webhook、私钥等
敏感信息放进 Workspace，也不要在不清楚影响时要求 Mark 执行删除、重置、发布或
推送等高影响动作。

## 测试边界

自动化测试使用 fake Channel 和 fake Codex，不访问真实飞书或执行真实 Workspace
动作。真实验收需要在已配置飞书 Bot、已登录 Codex 的本机运行：

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
