# Concise Auto Scan Jira Bug template

This optional format is selected through a Workspace's saved Auto Scan completion
prompt. It does not enable Jira for other Workspaces. Fill placeholders from the
current finding and scan receipt; never copy the example issue's data into new Bugs.

## Title

`[Lumon] {簡潔描述觸發條件與錯誤結果}`

## Description

Use the following Markdown body, without the outer Markdown fence. Keep exactly
these three section headings and their order.

````markdown
## 問題與影響

{一段簡短說明：什麼使用者／功能，在什麼條件下受到什麼具體影響}

**觸發步驟**

1. {必要的資料、狀態或前置條件}
2. {操作或系統事件}
3. {可觀察到的錯誤結果}

- **預期：** {正確行為}
- **實際：** {目前程式的錯誤行為}

## 根因與修正方向

{一段解釋根因及相關呼叫路徑，不重複問題說明}

```{language}
{最小必要、已脫敏的實際程式碼片段}
```

**建議：** {針對根因的具體修正方向與需涵蓋的相關路徑}

## 證據與驗證

- **位置：** {repository} → `{repository-relative file}`，{line_range}。
- **相關提交：** `{verified commit}`；掃描分支：`{configured branch}`。
- **驗證：** {本次掃描實際完成的檢查、未執行的驗證，以及尚未確認的正式環境影響範圍}。

---

**掃描來源：** {開始時間與時區}，回溯 {lookback_days} 天，{精確起訖或未確認說明}。嚴重程度：**{High / Medium / Low}**。
**Finding ID：** `{issue_id}`
**Run ID：** `{run_id}`
````

## Content rules

- Write titles and prose in Traditional Chinese. Preserve code, identifiers and
  paths exactly; keep severity labels High, Medium and Low in English.
- Use short paragraphs and only the steps needed for the original trigger.
  Do not add a separate metadata section, repeated evidence blocks or repeated
  disclaimer paragraphs. Put traceability in the footer.
- Record actual validation once. For a static review, explicitly say no tests or
  runtime reproduction were performed; describe reproduction steps as inferred
  from code. Do not imply a production incident was observed from code evidence.
- For missing facts, write `Not established by the scan`, with a brief explanation
  of what is unknown. Consolidate unknown production impact and validation limits
  into the validation bullet; keep any unknown review-window bounds in the footer.
- Only include a commit supported by the scan evidence. Do not confuse a commit
  introducing a bug with the reviewed branch revision, or invent a commit or line.
- Prefer Asia/Shanghai (UTC+8) for a known scan timestamp; preserve its actual
  instant and state the timezone. Never infer exact lookback bounds from a duration.
- On native read-back of a newly created Bug, verify the single `[Lumon] ` prefix,
  all three headings in order, required evidence and the Finding ID/Run ID footer.
  Reuse existing matching cards without rewriting their content.
