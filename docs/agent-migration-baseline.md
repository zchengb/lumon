# Agent Migration Baseline

Regression checklist for Feishu multi-agent work. Re-verify after each PR that touches notifications, agents, or workflow adapters.

## CLI

- [ ] `lumen scan --project <slug> --dry-run`
- [ ] `lumen scan --project <slug>`
- [ ] `lumen patch run --project <slug> --dry-run`
- [ ] `lumen patch run --project <slug>`
- [ ] `lumen delivery run --story <story-key>`
- [ ] `lumen delivery run --story <story-key> --dry-run`

## Schedule

- [ ] Scan schedule (launchd / cron) runs without Agent Gateway
- [ ] Patch schedule runs without Agent Gateway
- [ ] Delivery schedule runs without Agent Gateway

## Notifications

- [ ] Legacy webhook (`FEISHU_WEBHOOK_URL`) still receives cards when `notifications.mode` is `legacy` or unset
- [ ] `LUMEN_SKIP_FEISHU=1` skips Feishu send
- [ ] `notifications.feishu.enabled: false` skips Feishu send
- [ ] Notification failure does not fail the workflow exit path

## Result contracts

- [ ] `<scan-workspace>/results/scan-result.json`
- [ ] `<workspace>/lumen/results/patch-result.json`
- [ ] `<docs>/lumen/results/delivery-result.json`
- [ ] Wrapper-filled `feishu` status fields remain (`sent` / `failed` / `skipped` / dry-run variants)

## Locks and worktrees

- [ ] Scan lock: `<scan-workspace>/state/run.lock/`
- [ ] Patch lock: `<workspace>/lumen/locks/patch-run/`
- [ ] Delivery lock: `<docs>/lumen/locks/delivery-run/`
- [ ] Scan / patch / delivery worktrees prepare and clean as before

## Agent Gateway (Dylan MVP)

- [ ] `agents.enabled=false` (default): gateway does not process messages
- [ ] Gateway stopped: scheduled and CLI scan still work
- [ ] Invalid Dylan App Secret: scan workflow still completes; notify may fail/fallback
- [ ] `@Dylan` scan: ack in thread, then result reply; duplicate `message_id` does not start a second scan

### Ops (Dylan)

1. Create Feishu self-built app "Dylan", enable bot + long connection, subscribe `im.message.receive_v1`.
2. Set `FEISHU_DYLAN_APP_ID` / `FEISHU_DYLAN_APP_SECRET` in `~/.lumon/.env.local` or `$LUMEN_HOME/.env.local`.
3. Write `$LUMEN_HOME/agents/config.json` with `{"enabled": true}` (template: `lib/templates/agents/config.json`) or export `LUMEN_AGENTS_ENABLED=1`.
4. Install WS dependency once: `pip install lark-oapi`.
5. Run `lumen agents start` (foreground). Use `status` / `stop` for lifecycle.
6. For dual notify while testing: set workspace `notifications.mode` to `dual` (default remains `legacy`).

## Notes

- Default notification mode must remain `legacy` until dual/agent rollout.
- Credentials (`FEISHU_*_APP_SECRET`, `CURSOR_API_KEY`, tokens) must never appear in result JSON, prompts, or logs.
