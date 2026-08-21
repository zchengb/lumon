---
status: "draft"
---
# Technical Plan: Normalize the reminder label

## Goal & Scope

### Goal

The reminder settings screen already stores a notification label, but the local renderer uses two different capitalization paths. This change makes the label presentation deterministic without changing the stored value, message payload, or delivery behavior. The user should see the same label in the settings preview and in the generated reminder summary.

### Acceptance Criteria

- **AC1:** A label with mixed capitalization is rendered using the existing display convention in both local views.
- **AC2:** Empty labels keep the current fallback text and do not produce an empty visual value.
- **AC3:** The persisted setting and outbound reminder payload remain unchanged.

### In Scope

- One repository, one notification presentation module, and the shared formatter already used by the preview component.
- The existing unit test data for ordinary, mixed-case, and empty labels.

### Out of Scope

- Storage migration, API shape, permission behavior, message delivery, and any frontend framework change.

## Technical Decision

### Decision 1: Reuse the existing display formatter

**What is the problem?**

The preview path currently performs a local capitalization step while the summary path calls the shared formatter. Maintaining two rules allows the same setting to be displayed differently and makes the empty-value behavior depend on the caller.

**Decision content**

- Move the preview call to the existing shared formatter rather than creating a second formatter.
- Keep the formatter's current fallback behavior and leave the stored value untouched.

**Decision conclusion**

**Use the existing shared display formatter in both local presentation paths.**

## Implementation Plan

1. **`notification/presentation/ReminderPreview`:** replace the local capitalization expression with the existing formatter call and preserve the surrounding layout data.
2. **`notification/presentation/ReminderSummary`:** keep the current formatter call and add a focused regression case showing that both paths use the same result.
3. **`notification/presentation/LabelFormatterTest`:** cover mixed-case input, already-normalized input, and an empty value with the established fallback.

The change stays inside the existing presentation layer. No new public method, persisted field, event property, or configuration key is introduced. Private local names remain an implementation detail and do not need to be catalogued.

## Verification

- **Happy path:** run the presentation module's focused unit test; mixed-case input produces one consistent display label.
- **Empty input:** verify that the existing fallback is returned and neither view emits an empty label.
- **Core regression:** run the module's existing test command and confirm the stored setting and outbound payload assertions remain unchanged.

## Risks / Out of Scope

- The formatter's established fallback is intentionally preserved; changing its wording is a separate Story.
- No data or delivery behavior is changed.
