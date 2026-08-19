---
name: lumen-technical-loop
description: Use when the user explicitly asks for a Technical Loop or when the Feishu Loop Gateway detects a clear request to turn one business-ready Lumen Story or requirement into a technical plan/design. For a combined Story Plan + Technical Plan request, enter only after the Business/Story stage is ready. It may modify that Story's technical-plan.md and metadata.json; it must not modify application source code or story.md.
---

<!-- Lumen managed: agent-skill -->

# Lumen Technical Loop

Read `references/workflow.md` before acting. Frontend/Web/Native UI delivery, Figma-to-code work, browser/device runtime work, Visual Delivery Contracts, and visual QA are disabled; keep them out of scope or blocked. Use the smallest sufficient plan profile and keep status in `metadata.json`; do not use a CLI approval command.

In Feishu, do not make the user name this Loop. Start directly when the Loop Gateway marks the intent clear; ask one concise confirmation when it marks the intent ambiguous. Technical Loop entry is not delivery authorization, and it requires `businessStatus: ready` before planning can proceed.

If `businessStatus` is not `ready`, stop before drafting or presenting technical-plan.md, explain the Story prerequisite in Feishu text, and return to Business Loop. Keep the plan and progress as text by default; only attach a file when the user explicitly requests it.
