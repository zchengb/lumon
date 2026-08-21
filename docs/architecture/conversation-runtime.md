# Conversation Runtime

`AgentSessionHost` owns lifecycle and ordering for one provider session. A
Feishu Thread is a shared transport, not a single global lock: each Agent has
its own session, provider session ID, queue, waiting state, and checkpoint.

Provider adapters emit normalized `HarnessEvent` values while the subprocess
is running. `ConversationOutput` publishes visible progress, findings,
questions, handoffs, and artifacts immediately; the final result is replayed
through the same idempotency key so a provider that buffers output cannot
duplicate a message.

Questions are explicit state:

```json
{
  "type": "human_question",
  "question_id": "q-123",
  "question": "Which option should I use?"
}
```

Only the owning SessionHost may resume that question. The transport may append
another human message to the Thread without blocking unrelated Agents.
