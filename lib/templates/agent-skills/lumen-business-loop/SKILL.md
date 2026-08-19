---
name: lumen-business-loop
description: Use when the user explicitly asks for a Business Loop or when the Feishu Loop Gateway detects a clear request to create, capture, or turn something into a requirement or Story. For a combined Story Plan + Technical Plan request, this is always the first stage. It may modify topics/<slug>.md, stories/<slug>/story.md, and that Story's metadata.json; it must not modify application source code or technical-plan.md.
---

<!-- Lumen managed: agent-skill -->

# Lumen Business Loop

Read `references/workflow.md` before acting. Work in the user's business language. Use `templates/topic.md` and `templates/story.md` from the workspace. Status remains in `metadata.json`; do not use a CLI approval command.

In Feishu, do not make the user name this Loop. Start directly when the Loop Gateway marks the intent clear; ask one concise confirmation when it marks the intent ambiguous. Starting the Business Loop does not authorize technical planning or delivery.

When the request also asks for a Technical Plan, finish the Story stage first. Do not hand off to Technical Loop until `story.md` exists and `metadata.json.businessStatus` is `ready`. Keep progress, questions, and the Story Plan in the Feishu text response; do not create a PDF or other attachment unless the user explicitly asks for one.
