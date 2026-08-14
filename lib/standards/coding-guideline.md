# Coding Guideline (Lumen Standard)

This is the official Lumen coding standard for delivery execution. It is shipped with the Lumen CLI at `lib/standards/coding-guideline.md` and injected into the delivery agent prompt by `lumen delivery run`.

Agents must follow it when implementing an approved `technical-plan.md`.

## Core Principles

1. **Implement the approved plan** — change only what `technical-plan.md` requires. Do not expand scope without returning to the Technical Loop.
2. **Match existing conventions** — read surrounding code before writing. New code should look like it was written by the same team.
3. **Minimal diff** — prefer the smallest correct change. Avoid drive-by refactors, renames, or formatting-only edits outside the touched behavior.
4. **Evidence over assumption** — inspect imports, callers, tests, migrations, and configuration before changing behavior.
5. **Safe by default** — preserve auth, validation, idempotency, transactions, and backward compatibility unless the plan explicitly changes them.
6. **Test what you change** — add or update focused tests when the repository already has a test pattern for the affected layer. Exception: when `repos.json` sets `generate_tests: false` for a repository, do not create or update unit or integration tests in that repository.

## Before Writing Code

For each impacted repository:

1. Read `technical-plan.md` and the linked Acceptance Criteria in `story.md`.
2. Read this coding guideline.
3. Inspect package/module layout, naming, recent commits, build configuration, and representative tests in that repository.
4. Identify the exact files, classes, endpoints, migrations, and tests named or implied by the plan.
5. Discover whether the repository has architecture guard tests (for example ArchUnit, package-boundary tests, ESLint import rules, PMD, or Checkstyle) and record the relevant guard in the delivery result.
6. Identify the repository's authentication, authorization, tenant/dealer scope, and audit conventions whenever a changed flow can read or mutate protected data.
7. Confirm the worktree is on a feature branch, not the default branch.

If the plan is missing file-level detail for a non-trivial change, stop and return to the Technical Loop.

## Workspace Layout

Code repositories live inside the docs project under `repos/`:

```text
<docs-repo>/
  repos/
    xxxx-backend/
    xxxx-frontend/
  stories/
  lumen/
```

Use the workspace paths provided in the delivery prompt. Repositories are not siblings of the docs project anymore; they are nested under `repos/`.

## Change Scope Rules

- Do not edit unrelated repositories.
- Do not rename packages, modules, or public APIs unless the technical plan requires it.
- Do not change dependency versions unless the plan requires it.
- Do not delete legacy code paths unless the plan documents why they are safe to remove.
- Do not add comments that restate obvious code.
- Do not leave dead code, unused imports, or temporary debug logging.

## Architecture Rules

Place code in the same layer the repository already uses. The actual repository package/module structure and its guard tests are authoritative; the generic names below are only a vocabulary for the delivery plan.

| Layer | Responsibility |
|-------|----------------|
| `representation` / `controller` / `api` | HTTP/API contract, request mapping, auth annotations |
| `application` / `service` | Use-case orchestration, transaction boundaries |
| `domain` | Business entities, invariants, domain services |
| `infrastructure` | Persistence, messaging, external clients |
| `query` / `read model` | Read-side queries and projections |

Rules:

- Keep business rules out of controllers when the repository already uses an application/domain layer.
- Keep persistence details out of domain models.
- Reuse existing builders, mappers, repositories, and DTO patterns instead of inventing parallel structures.
- Do not bypass an existing application/service boundary from a controller, job, consumer, or UI adapter.
- Do not introduce a new layer, package convention, or cross-layer dependency merely for this story.
- When the repository has architecture guard tests, extend the relevant guard for a new package/layer or keep the change compliant with it. Do not weaken or disable an existing guard to pass delivery.
- When no guard exists, follow the observed layering and record the absence as a delivery risk; propose a new guard only through a separately approved technical plan.

## Java (Spring) Rules

Use when the repository is Java-based.

- Prefer `var` for local variables when the type is obvious from the right-hand side.
- Use constructor injection for Spring beans.
- Keep controllers thin; put orchestration in application services.
- Use existing annotation patterns for auth, validation, and exception handling.
- Reuse existing request/response DTOs and mappers.
- For database changes, add Flyway/Liquibase migrations in the repository's existing migration folder and naming style.
- Do not create database foreign-key constraints. Preserve referential integrity through application validation, indexes, lifecycle handling, and the repository's existing data-access conventions.
- Name tests `<ClassUnderTest>Test` or follow the repository's existing suffix.
- Prefer focused unit tests for domain/application logic and slice/integration tests only when the repository already uses them.

## TypeScript / React Native Rules

Use when the repository is frontend or Node-based.

- Follow the existing folder structure under `App/`, `src/`, or the repository equivalent.
- Reuse existing hooks, services, selectors, and style files instead of duplicating patterns.
- Keep components focused; move data fetching and business logic into existing service/query layers when that is the local convention.
- Do not introduce a new state library or styling system unless the plan requires it.
- Prefer existing test utilities and naming conventions for component or hook tests.

## PHP / Laravel Rules

Use when the repository is PHP-based.

- Follow existing controller, service, request, and resource patterns.
- Keep validation in Form Requests when that is the repository convention.
- Reuse Eloquent relationships, repositories, and service classes already present in the module.
- Add migrations using the repository's existing timestamped migration style.

## API And Contract Rules

- Do not change public API shape unless `technical-plan.md` documents the contract change.
- Keep request and response field names consistent across frontend, backend, and docs.
- When adding endpoints, follow existing route naming, versioning, auth, and permission patterns.
- Document new configuration keys in the technical plan or repository config docs when the repository already does so.

## Security Rules

- Preserve existing authentication and authorization checks.
- Never weaken role, permission, dealer-scope, or tenant-scope checks to make implementation easier.
- For every new or changed endpoint, job, query, export, or mutation, explicitly assess: actor, permission/role, tenant/dealer/data scope, ownership check, and audit requirement. Reuse the repository's existing mechanism.
- Add or update an authorization-focused test when the repository has a matching test pattern and the change affects protected data or actions.
- Do not log secrets, tokens, passwords, or personal data.
- Validate all external input at the boundary the repository already uses.
- Prefer existing sanitization and encoding utilities.

## Database And Migration Rules

- One migration per logical change when possible.
- Make migrations backward-compatible unless the plan documents a coordinated release.
- Do not add database foreign keys, including `FOREIGN KEY`, `REFERENCES`, or cascading FK constraints. Use a normal index where query performance or application-level relationship checks require it.
- Do not hand-edit production data in code.
- Name tables, columns, and indexes consistently with the repository's existing schema.
- Update seeders/factories/tests when the repository already maintains them for the changed tables.

## Git, Branch, And Commit Rules

Branch naming:

```text
feature/<JIRA-KEY>-<short-slug>
```

If the repository already uses a different feature-branch convention, follow the repository history from `git log` and branch names instead.

### Commit message format

Before committing, inspect `git log --oneline -n 20` only to understand the work style of recent changes.

Always write Lumon-created commit subjects in this exact format, even when older history used a human author prefix such as `[xiaobin]`:

```text
[lumon] #{JIRA_NUMBER} {chore|docs|feat|fix|refactor|style|test}: {COMMIT_MESSAGE}
```

Examples:

```text
[lumon] #N/A feat: update user bind-car agreement content.
[lumon] #MBPAS-1369 refactor: refactor missing-contact dialog.
[lumon] #N/A feat: update delivery config
```

Never replace `[lumon]` with a person name. When past commits include an author name in the subject, still use **`[lumon]`** for every Lumon or delivery-docs commit.
Commit rules:

- Commit on a feature branch only, never directly on the default branch.
- Commit in small, incremental steps after completing each small feature.
- Always write concise, clear commit messages following the format above.
- Use the story JIRA key from `metadata.json` for `{JIRA_NUMBER}` (for example `MBPAS-1369`).
- If there is no JIRA number in the context, use `N/A` as the JIRA number: `[lumon] #N/A ...`
- Allowed types: `chore`, `docs`, `feat`, `fix`, `refactor`, `style`, `test`

## Pull Request Rules

Create a PR when the approved plan scope is complete or when the technical plan explicitly calls for an intermediate PR.

PR title:

```text
[<JIRA-KEY>] <Short delivery summary>
```

PR description must include:

```markdown
## Story
<link or JIRA key>

## Technical Plan
<relative path to technical-plan.md or short summary>

## Changes
- <repo/file level summary>

## Verification
- <commands run or manual checks performed>

## Risks
- <remaining risk or follow-up>
```

If the repository uses a different PR template, follow the repository template and still include story, verification, and risk sections.

## Verification Rules

Follow the `Verification` section of `technical-plan.md` when choosing tests to add or update in code. **Do not run the verification profile during implementation.** Lumen CLI runs compile, static analysis, and test commands in a dedicated verification stage after the agent exits.

During implementation:

- Write or update tests that match the plan and repository patterns.
- Do not run `./gradlew`, `npm run lint`, `php -l`, or similar project-wide checks as a pre-handoff gate.
- Do not record `verification_results` in `delivery-result.json`. Lumen fills them from real command output.

Lumen's default Java/Gradle profile (for reference only — Lumen runs these, not the agent):

| Check | Typical Java / Gradle command |
|---|---|
| Language Grammar Check | `./gradlew compileJava compileTestJava -x test` |
| PMD Check | `./gradlew pmdMain pmdTest` |
| Unit Test | `./gradlew test` with unit-focused test patterns |
| Integration Test | `./gradlew test` with controller/base/integration patterns |

If verification fails, Lumen may invoke a bounded remediation pass. Fix the reported failure; Lumen reruns verification.

## When To Stop And Escalate

Stop implementation and return to the Technical Loop when:

- The plan assumes APIs, tables, or modules that do not exist.
- The change requires a product decision not captured in `story.md`.
- The safest fix needs a broad refactor outside plan scope.
- Repository conventions conflict with the plan.

Stop and ask the user when:

- The worktree is dirty on the default branch.
- Multiple valid implementations exist and the plan does not choose one.
- Verification cannot be run and the plan requires runtime proof.

## Definition Of Done

A delivery run is done when:

- Code matches the approved `technical-plan.md`.
- This coding guideline was followed.
- Verification from the plan was run or explicitly recorded.
- `delivery-result.json` was written.
- PR URL is recorded when a PR was created.
