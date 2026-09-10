# Lumon Agent Workflow

本文件记录 Lumon 项目在实现、验证和发布阶段的协作约定。

## 变更完成后的默认行为

1. 完成实现后先运行与变更相关的测试和质量门禁。
2. 未明确要求发布时，不自动升级版本号、创建 commit 或 push。
3. 验证通过后，在对话中一次性说明验证结果，并询问是否执行“升级版本号 + commit + push”。
4. 不依赖操作系统弹窗；确认通过当前 Agent 对话完成。仓库说明不能绕过系统或用户授权规则。

## 用户明确要求发布时

当用户明确要求“提交并推送”或等价表达时，按以下顺序执行：

1. 根据变更类型升级 `src/lumon/version.py` 中的版本号；兼容性改动默认递增 patch 版本。
2. 同步更新必要的版本断言、发布说明和测试，不修改无关文件。
3. 运行前端 typecheck/test/build、Python pytest/ruff/pyright、静态资源检查和 `uv build`。
4. 只暂存本次变更，检查 staged diff 中没有凭据、临时文件或意外生成物。
5. 按 Conventional Commits 创建本地 commit。
6. 版本号与 tag 一致后创建 `vX.Y.Z` tag，并 push 分支和 tag。
7. 跟踪 GitHub Actions，确认 GitHub Release 与包产物成功生成。

如果用户只要求 commit，则在第 5 步结束；如果只要求 push，则先确认已有待推送 commit 和发布目标，不替用户创建无关 commit。

## Lumon 发布约定

- 主开发分支：`release`。
- Python 包版本唯一来源：`src/lumon/version.py`。
- Release tag 必须使用 `vX.Y.Z`，并与包版本完全一致。
- GitHub Actions 的 release workflow 由版本 tag 触发。
- 发布包只存储在 GitHub Release/Actions artifact，不发布到公共包索引。
- 发布后升级入口为 `lumon update`；升级不修改 Workspace。
- 不把 token、密码、Webhook 或 SSH 私钥写入仓库、日志、commit 或命令输出。
