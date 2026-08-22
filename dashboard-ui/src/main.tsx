import { createContext, memo, useCallback, useContext, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { marked } from "marked";
import mermaid from "mermaid";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import TurndownService from "turndown";
import {
  Activity, Bold, ChevronDown, ChevronLeft, ChevronRight, CircleAlert, CircleCheck, CircleDot, CircleHelp, Code2, Copy, LayoutDashboard,
  Calendar, Eye, EyeOff, ExternalLink, FileCode2, FolderGit2, GitBranch, Heading2, Italic, Link2, List, ListFilter, LoaderCircle,
  Play, RotateCcw, Save, ScanSearch, Search, Settings2, Terminal, Trash2, User,
  Maximize2, Minimize2, ShieldCheck, Sparkles, Truck, Workflow, X, ZoomIn, ZoomOut
} from "lucide-react";
import "./styles.css";
import "./typography.css";

const lumonVersion = __LUMON_VERSION__;

mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });
marked.setOptions({ gfm: true, breaks: false });
const mermaidSvgCache = new Map<string, string>();
const mermaidChartById = new Map<string, string>();
let mermaidPaintSeq = 0;
const FULLSCREEN_ZOOM_MIN = 0.5;
const FULLSCREEN_ZOOM_MAX = 3;
const FULLSCREEN_ZOOM_STEP = 0.25;

type RecordValue = Record<string, any>;
type Tab = "overview" | "activity" | "scan" | "delivery" | "patch" | "observatory" | "repositories" | "prompts" | "settings";
type NoticeTone = "success" | "error" | "info";
type Notice = { message: string; tone: NoticeTone };
type Notify = (message: string, tone?: NoticeTone) => void;
type Locale = "en" | "zh-Hans" | "zh-Hant";
type Translate = (key: string, variables?: Record<string, unknown>) => string;

const localeStorageKey = "lumon-dashboard-locale";
const legacyLocaleStorageKey = "lumen-dashboard-locale";
const localeOptions: Array<{ value: Locale; label: string }> = [
  { value: "en", label: "English" },
  { value: "zh-Hans", label: "简体中文" },
  { value: "zh-Hant", label: "繁體中文" },
];

const translations: Record<Locale, Record<string, string>> = {
  en: {
    "language.label": "Language",
    "language.en": "English",
    "language.zhHans": "简体中文",
    "language.zhHant": "繁體中文",
    "nav.overview": "OVERVIEW",
    "nav.activity": "ACTIVITY",
    "nav.scan": "AUTO SCAN",
    "nav.delivery": "AUTO DELIVERY",
    "nav.patch": "AUTO PATCH",
    "nav.observatory": "OBSERVATORY",
    "nav.repositories": "REPOSITORY",
    "nav.prompts": "WORKFLOW",
    "nav.settings": "SETTINGS",
    "context.overview.title": "MANAGER OVERVIEW",
    "context.overview.description": "Agent ownership, workflow health, and the next human decision.",
    "context.activity.title": "AGENT ACTIVITY",
    "context.activity.description": "Conversation records, outcomes, and the evidence behind each Agent turn.",
    "context.scan.title": "AUTO SCAN",
    "context.scan.description": "Review history and manage tracked findings.",
    "context.delivery.title": "AUTO DELIVERY",
    "context.delivery.description": "Story execution, verification, and pull request delivery.",
    "context.patch.title": "AUTO PATCH",
    "context.patch.description": "Jira Task and Bug capture, focused fixes, and safe handoff.",
    "context.observatory.title": "OBSERVATORY",
    "context.observatory.description": "Browse and edit story briefs and technical plans.",
    "context.repositories.title": "REPOSITORY",
    "context.repositories.description": "Local repositories, automation permissions, and delivery verification policy.",
    "context.prompts.title": "WORKFLOW",
    "context.prompts.description": "The prompts, scripts, control points, and recovery paths behind each local automation.",
    "context.settings.title": "SETTINGS",
    "context.settings.description": "Workspace configuration, scheduling, and local integrations.",
    "common.updated": "Updated {{value}}",
    "common.syncing": "Syncing…",
    "common.project": "Project",
    "common.currentProject": "Current project",
    "common.openSettings": "Open Settings",
    "common.manageCapture": "Manage capture",
    "common.loadingWorkspace": "Loading local workspace state…",
    "common.expandNavigation": "Expand navigation",
    "common.collapseNavigation": "Collapse navigation",
    "common.version": "Version {{value}}",
    "common.staticReport": "Static report mode: interactive actions are unavailable.",
    "common.unableLoadState": "Unable to load Dashboard state",
    "common.requestFailed": "Request failed",
    "common.unsavedSettings": "You have unsaved Settings changes. Leave without saving?",
    "common.unsavedObservatory": "You have unsaved Observatory changes. Leave without saving?",
    "common.noData": "No data available.",
    "common.cancel": "Cancel",
    "common.close": "Close",
    "common.later": "Later",
    "common.save": "Save",
    "common.saving": "Saving…",
    "common.confirm": "Confirm",
    "common.continue": "Continue",
    "common.start": "Start",
    "common.stop": "Stop",
    "common.retry": "Retry",
    "common.loading": "Loading…",
    "common.enabled": "Enabled",
    "common.paused": "Paused",
    "common.active": "Active",
    "common.off": "Off",
    "common.all": "All",
    "common.clear": "Clear",
    "common.selected": "{{count}} selected",
    "common.statusesSelected": "{{count}} statuses selected",
    "common.previous": "Previous",
    "common.next": "Next",
    "common.pageOf": "Page {{page}} of {{count}}",
    "common.showing": "{{count}} shown",
    "common.debugDetails": "Debug details",
    "common.originalPrompt": "Original Agent prompt",
    "common.records": "{{count}} records",
    "common.runs": "{{count}} runs",
    "common.recentEvents": "{{count}} recent events",
    "common.yes": "Yes",
    "common.no": "No",
    "common.unknown": "Unknown",
    "common.workspace": "Workspace",
    "common.agent": "Agent",
    "common.clarification": "Clarification",
    "common.manager": "Manager",
    "common.you": "You",
    "common.trace": "Trace",
    "common.viewActivity": "View activity",
    "common.viewLog": "View log",
    "common.viewTrace": "View trace",
    "common.open": "Open",
    "common.inspect": "Inspect",
    "common.noAgentRoles": "No Agent roles available yet.",
    "common.noAgentQuestions": "No unanswered Agent questions.",
    "common.noConversationRecords": "No conversation records match this filter.",
    "common.noFindings": "No findings match this status.",
    "common.noStoriesFilter": "No stories match this filter.",
    "common.noStories": "No stories found in the docs repository.",
    "common.selectStory": "Select a story to inspect.",
    "common.noAgentHistory": "No Agent conversation store is available yet. New Feishu conversations will appear here after the gateway starts.",
    "common.askAgents": "Ask one of the Agents in Feishu, then refresh this page.",
    "common.activityStoreFirstTurn": "The local activity store will be created by the first Agent turn.",
    "common.noDeliveryHistory": "No delivery history yet.",
    "common.noPatchHistory": "No Auto Patch history yet.",
    "common.noDeliveryActivity": "No scheduled delivery activity recorded yet.",
    "common.noPatchActivity": "No Auto Patch activity recorded yet.",
    "common.noAgentRolesSettings": "No agent roles available yet.",
    "common.noIntegrationKeys": "No local integration keys configured.",
    "common.valueFor": "Value for {{name}}",
    "common.revealValue": "Reveal value",
    "common.copyValue": "Copy value",
    "common.copyCode": "Copy code",
    "common.showFullscreen": "Show fullscreen",
    "common.closeFullscreen": "Close fullscreen",
    "common.zoomOut": "Zoom out",
    "common.resetView": "Reset view",
    "common.zoomIn": "Zoom in",
    "common.diagram": "Diagram",
    "common.image": "Image",
    "common.formattingTools": "Formatting tools",
    "common.documentBody": "Document body",
    "common.add": "Add",
    "common.navigation": "Lumon navigation",
    "common.dashboardSections": "Dashboard sections",
    "common.explainSetting": "Explain this setting",
    "common.originalMarkdown": "Original Markdown",
    "common.preview": "Preview",
    "common.live": "Live",
    "common.attempt": "Attempt {{number}}: {{duration}}",
    "common.overwriting": "Overwriting…",
    "common.overwriteRemote": "Overwrite remote",
    "common.remoteDecision": "Remote updates need your decision",
    "common.remoteConflictCopy": "Lumon committed local workspace changes, but the remote branch changed before the push. Review the remote changes before choosing whether to overwrite them.",
    "common.onlyTaskBugCards": "Only Task and Bug cards in the current active sprint are shown.",
    "common.noPendingPatchCards": "No pending Auto Patch Jira cards were found in the current active sprint.",
    "common.patchFlow": "Capture → repository → patch → publish",
    "common.retryDeliveryCopy": "This removes the Story worktrees, resets its Delivery and JIRA status, then starts a new run. The failed run and logs stay in history.",
    "common.repositoryGovernance": "Repository Governance",
    "common.addRepository": "Add repository",
    "common.repositoryIntro": "Connect repositories by Git URL. Lumon clones them into repos/, detects runtime and build tooling, then lets you approve the automation that may change or publish code.",
    "common.attentionNote": "Needs attention means uncommitted changes, a branch behind remote, or a diverged branch/sync.",
    "common.repositoryConfiguration": "Repository configuration",
    "common.unnamedRepository": "Unnamed repository",
    "common.generic": "Generic",
    "common.noBuildTool": "No build tool detected",
    "common.identityConnection": "Identity & connection",
    "common.identityConnectionHelp": "Detected locally; the default branch is the only editable connection setting.",
    "common.localPath": "Local path",
    "common.remote": "Remote",
    "common.gitStatus": "Git status",
    "common.branchSync": "Branch sync",
    "common.defaultBranch": "Default branch",
    "common.runtimeBuild": "Runtime & build",
    "common.runtimeBuildHelp": "Detected from repository files. These values are read-only until the repository changes.",
    "common.language": "Language",
    "common.java": "Java",
    "common.node": "Node",
    "common.buildTools": "Build tools",
    "common.notDetected": "Not detected",
    "common.automationPermissions": "Automation permissions",
    "common.frontendDeliveryDisabled": "Frontend delivery remains disabled globally and cannot be enabled here.",
    "common.autoScanFixes": "Auto Scan fixes",
    "common.autoScanFixesHelp": "Allow high-confidence Scan fixes and their configured publish flow.",
    "common.deliveryPermission": "Auto Delivery",
    "common.deliveryPermissionHelp": "Allow approved technical delivery work for this repository.",
    "common.patchPermission": "Auto Patch",
    "common.patchPermissionHelp": "Allow Jira-driven fixes and publishing for this repository.",
    "common.deliveryVerification": "Delivery verification",
    "common.deliveryVerificationHelp": "Choose what Lumon should run for this repository after implementation.",
    "common.policy": "Policy",
    "common.runVerification": "Run verification",
    "common.runVerificationHelp": "Use the automatic profile or your custom commands.",
    "common.skipVerification": "Skip verification",
    "common.skipVerificationHelp": "Do not run compile, static checks, or tests.",
    "common.executionSource": "Execution source",
    "common.automaticProfile": "Automatic profile",
    "common.automaticProfileHelp": "Detect commands from repository files at runtime.",
    "common.customCommands": "Custom commands",
    "common.customCommandsHelp": "Run only the commands entered below.",
    "common.checksToRun": "Checks to run",
    "common.compileChecks": "Compile & static checks",
    "common.compileChecksHelp": "Compile, syntax, typecheck, lint, or PMD checks.",
    "common.tests": "Tests",
    "common.testsHelp": "Unit, integration, and test-suite commands.",
    "common.commands": "Commands",
    "common.useSuggestedCommands": "Use {{count}} suggested command{{suffix}}",
    "common.oneCommandPerLine": "One command per line.",
    "common.cloneUrl": "Clone URL",
    "common.cloneInspect": "Clone and inspect",
    "common.addRepositoryDescription": "Lumon clones the Git URL, detects the branch and tooling, enables existing Scan and Delivery behavior, and authorizes Auto Patch by default.",
    "common.settingsSections": "Settings sections",
    "common.schedules": "Schedules",
    "common.agentConversations": "Agent conversations",
    "common.integrations": "Integrations",
    "common.configuredKeys": "configured keys",
    "settings.automation": "Automation",
    "settings.automationDescription": "Schedules and execution policies that decide when work can move.",
    "settings.agentTeam": "Agent team",
    "settings.agentTeamDescription": "Who speaks to people, what each role owns, and which conversations may mutate state.",
    "settings.projectOutput": "Project output",
    "settings.projectOutputDescription": "Defaults used when Mark and Milchick turn a request into a testable Story.",
    "settings.runtime": "Runtime & integrations",
    "settings.runtimeDescription": "Model selection, publish behavior, notifications, and local secret values.",
    "settings.nextAgentTeam": "Next: Agent team",
    "settings.nextProjectOutput": "Next: Project output",
    "settings.nextRuntime": "Next: Runtime & integrations",
    "settings.backAutomation": "Back to Automation",
    "settings.localConfiguration": "Local configuration",
    "settings.controlPlane": "01 · CONTROL PLANE",
    "settings.humanAgents": "02 · HUMAN-FACING AGENTS",
    "settings.businessOutput": "03 · BUSINESS OUTPUT",
    "settings.operatingDetails": "04 · OPERATING DETAILS",
    "settings.globalFeishuAgents": "Global Feishu agents",
    "settings.defaultReplyLanguage": "Agent default reply language",
    "settings.defaultReplyLanguageDescription": "Used when the human has not explicitly established a language. Dashboard UI language is separate.",
    "settings.accessControl": "Access Control",
    "settings.accessControlDescription": "Authorize group chats as a whole, while private chats require one-to-one approval. Group membership is discovered from every configured Agent app.",
    "settings.accessPerson": "Person",
    "settings.accessChat": "Group chat",
    "settings.selectPerson": "Select a person",
    "settings.selectChat": "Select a group chat",
    "settings.identityRoles": "Access for this identity",
    "settings.selectIdentityHelp": "Choose one identity, then edit the three access roles below.",
    "settings.canTalk": "Can talk to Agents",
    "settings.canMutate": "Can run mutations",
    "settings.canAdmin": "Can administer Agents",
    "settings.accessSummary": "Configured identities",
    "settings.identityCount": "{{count}} identity records",
    "settings.pendingAccess": "Pending authorization",
    "settings.rolesApplied": "roles",
    "settings.agentCoreDescription": "Core controls are editable here. Role ownership, safety boundaries, and SOUL files stay managed by the Agent registry.",
    "settings.responsibility": "Responsibility",
    "settings.legacyWarning": "Legacy allow mode is unsafe for local agents. Prefer per-agent Access & Exposure with default_policy=deny.",
    "settings.recentPeople": "Recent people",
    "settings.recentChats": "Recent chats",
    "settings.groupChats": "Authorized group chats",
    "settings.groupChatsDescription": "Everyone in an allowed group can talk to the Agents; no per-person approval is needed.",
    "settings.privateContacts": "Private contacts",
    "settings.privateContactsDescription": "Private chats are authorized one person at a time. Review the display name and Feishu ID before enabling access.",
    "settings.noGroupChats": "No Feishu group chats discovered yet.",
    "settings.noPrivateContacts": "No private contacts discovered yet.",
    "settings.agentMembership": "Agents: {{value}}",
    "settings.addMutationUser": "Click to add as mutation user",
    "settings.allowChat": "Click to allow the chat",
    "settings.noRecentPeople": "No recent Feishu people yet. Message Dylan or Mark once, then refresh Settings.",
    "settings.generationLanguage": "Generation language",
    "settings.generationDescription": "Controls the language Mark writes into the Feishu Spreadsheet for this project. Traditional Chinese is the default for mbpass.",
    "settings.afterGeneration": "After changing language or sheet, ask Milchick/Mark to re-generate the story so new rows use the selected sheet.",
    "settings.executionDescription": "Choose a provider and model ID. Lumon sends API requests through the selected provider and does not validate model availability.",
    "settings.modelCenter": "Model center",
    "settings.modelCenterDescription": "Configure every conversational Agent and automation model in one place.",
    "settings.globalModelConfig": "Global AI configuration",
    "settings.globalModelScope": "Applied to all four conversational Agents and all three automation workflows.",
    "settings.inheritsGlobalModel": "Inherits global configuration",
    "settings.conversationModels": "Conversational Agents",
    "settings.conversationModelsDescription": "Every Feishu Agent uses the global provider and model above.",
    "settings.workflowModels": "Automation workflows",
    "settings.workflowModelsDescription": "Auto Scan, Auto Delivery, and Auto Patch use the same global provider and model.",
    "settings.workflowRuntimeLabel": "Applied to every Agent and workflow",
    "settings.openCodeHarness": "OpenCode Harness",
    "settings.openCodeHarnessDescription": "OpenCode runs the configured model and owns workspace tools and persistent sessions.",
    "settings.codexHarness": "Codex CLI",
    "settings.codexHarnessDescription": "Codex CLI uses the selected local ChatGPT account, full host and network access, and persistent sessions.",
    "settings.openCodeRuntime": "Agent runtime",
    "settings.openCodeRuntimeDescription": "This is the live Harness status used by conversational Agents and automation workflows.",
    "settings.harness": "Harness",
    "settings.runtimeModel": "Model",
    "settings.cliVersion": "CLI version",
    "settings.sessionMode": "Session",
    "settings.permissionProfile": "Permissions",
    "settings.harnessStatus": "Harness readiness",
    "settings.harnessStatusDescription": "The provider can use native tools and the canonical workspace; Feishu trust gating and audit remain the Host infrastructure seam.",
    "settings.harnessMode": "Mode",
    "settings.harnessCapabilities": "Capabilities",
    "settings.harnessSecurity": "Security boundary",
    "settings.harnessWarnings": "Warnings",
    "settings.harnessReady": "ready",
    "settings.harnessBlocked": "blocked",
    "settings.actionCatalog": "Action catalog",
    "settings.deepSeekCredential": "Model credentials",
    "settings.runtimeAccount": "Codex account",
    "settings.reasoningEffort": "Reasoning effort",
    "settings.deepSeekCredentialConfigured": "Configured in ~/.lumon/.env.local",
    "settings.deepSeekCredentialMissing": "Not configured (local models need no key)",
    "settings.automationOutcome": "Automation outcome",
    "settings.notificationsDescription": "Control whether Scan and Delivery post cards to the configured Feishu webhook. The webhook URL still lives under Variable Keys.",
    "settings.storedWorkspace": "Stored in this workspace",
    "settings.storedWorkspaceOrLumon": "Workspace + Lumon local",
    "settings.storedLumon": "Stored in Lumon local",
    "settings.availableKeys": "Available keys",
    "settings.availableKeysDescription": "Reveal a value to inspect it, or enter a replacement directly. Values are saved without display quotes.",
    "settings.revealReplacement": "Reveal or enter a replacement value",
    "settings.unsavedChanges": "You have unsaved changes",
    "settings.allSaved": "All changes saved",
    "settings.deliveryPaused": "Delivery polling is paused.",
    "settings.patchPaused": "Auto Patch polling is paused.",
    "settings.deliveryStatusHelp": "Select every Jira status that may start Auto Delivery. The Story must also be Business Ready, Technical Approved, and not already running.",
    "settings.deliveryStatusNote": "Select To Do, Backlog, In Progress, or any other eligible Jira status. On failure, Lumon moves the Jira card to the selected Block status and adds a Needs attention comment.",
    "settings.patchStatusNote": "Only Task and Bug cards are captured. Blocked cards retry after a new external Jira comment.",
    "settings.scanDefaultDescription": "No recurring scan is configured.",
    "settings.direct": "Direct",
    "settings.merge": "Merge",
    "settings.pullRequest": "PR",
    "settings.openPullRequest": "Open pull request",
    "settings.mergeAfterPullRequest": "Merge after pull request",
    "settings.pushDirectly": "Push directly to main branch",
    "settings.feishuNotifications": "Feishu notifications",
    "settings.allowedChatIds": "Allowed chat IDs",
    "settings.allowedUserIds": "Allowed user IDs",
    "settings.mutationUserIds": "Mutation user IDs",
    "settings.adminUserIds": "Admin user IDs",
    "settings.allowedChatHelp": "Whitelist group chats as a whole. Private chats still require one-to-one approval; @mention is still required in groups.",
    "settings.allowedUserHelp": "Empty = all users may ask read-only questions.",
    "settings.mutationUserHelp": "Required for resolve / schedule update / delivery start. Fail-closed when empty.",
    "settings.adminUserHelp": "Admins can also mutate.",
    "settings.appSecretRequired": "Required for Feishu client login.",
    "settings.keepSecret": "Leave blank to keep current secret",
    "settings.enterSecret": "Enter app secret",
    "settings.runtimeIdentityHelp": "Runtime identity is managed by the Agent registry.",
    "settings.workflowOwnershipHelp": "Workflow ownership is managed by the Agent registry.",
    "settings.publishDescription": "Direct push uses the repository credentials already configured for Git; PR and Merge use GitHub CLI. Auto Scan keeps a PR review gate and does not support direct push.",
    "settings.deploymentTracking": "Deployment tracking",
    "settings.deploymentTrackingDescription": "After publish, follow the configured CI/CD run and report only the actual deployment result. Credentials stay in local environment variables.",
    "settings.deploymentProvider": "Provider",
    "settings.deploymentDisabled": "Disabled",
    "settings.jenkins": "Jenkins",
    "settings.githubActions": "GitHub Actions",
    "settings.pollInterval": "Poll interval (seconds)",
    "settings.deploymentTimeout": "Timeout (seconds)",
    "settings.deploymentProviderHelp": "The CI/CD system whose deployment run should be observed after publish.",
    "settings.deploymentOwner": "Tracking owner",
    "settings.deploymentOwnerValue": "Milchick · Engineering Operations Manager",
    "settings.deploymentOwnerHelp": "Milchick owns the follow-up decision. Source or delivery failures go to Mark; Jira repair work goes to Irving; unclear infrastructure failures are reported for a human decision.",
    "settings.deploymentFailureHandling": "The host worker polls the provider. Milchick receives the terminal evidence and decides the next owner; no failure is hard-coded to Mark.",
    "settings.credentials": "Credentials",
    "settings.configured": "Configured",
    "settings.notConfigured": "Not configured",
    "settings.localGhLogin": "Local gh login",
    "settings.jenkinsPipeline": "Jenkins deployment pipeline",
    "settings.jenkinsPipelineHelp": "Required to identify the Jenkins pipeline to observe. Example: folder/job-name. Lumon does not use this field to run code.",
    "settings.jenkinsCredentials": "Set JENKINS_URL and JENKINS_AUTH in Variable Keys. Values stay in the workspace environment and are never written to delivery.json.",
    "settings.githubCredentials": "GitHub Actions uses the workspace runner's local gh login. No token is entered or stored here.",
    "settings.githubRepository": "GitHub repository",
    "settings.githubWorkflow": "Workflow (optional)",
    "label.deployment": "Deployment",
    "label.provider": "Provider",
    "label.lastChecked": "Last checked",
    "action.openDeployment": "Open deployment",
    "editor.heading": "Heading",
    "editor.editLink": "Edit link URL",
    "editor.linkUrl": "Link URL",
    "editor.bold": "Bold",
    "editor.italic": "Italic",
    "editor.link": "Link — Shift+click a link to place the caret, then edit",
    "editor.list": "List",
    "editor.code": "Code",
    "prompt.original": "Original Markdown",
    "prompt.preview": "Preview",
    "customModel.enter": "Enter a custom model",
    "customModel.id": "Model ID",
    "customModel.placeholder": "e.g. deepseek-v4-flash",
    "customModel.copy": "Lumon does not validate model availability. The value will be used on the next run.",
    "customModel.edit": "Edit custom model",
    "customModel.option": "Custom model ID…",
    "customModel.badge": "Custom",
    "customModel.help": "Use a model ID supported by the selected provider.",
    "status.completed": "Completed",
    "status.passed": "Passed",
    "status.failed": "Failed",
    "status.skipped": "Skipped",
    "status.open": "Open",
    "status.inProgress": "In progress",
    "status.awaitingDeploy": "Awaiting deployment",
    "status.running": "Running",
    "status.active": "Active",
    "status.notSet": "Not set",
    "status.notConfigured": "Not configured",
    "status.resolved": "Resolved",
    "status.reopened": "Reopened",
    "status.synced": "Synced",
    "status.ignored": "Ignored",
    "status.blocked": "Blocked",
    "status.pending": "Pending",
    "status.prOpen": "PR open",
    "status.notStarted": "Not started",
    "status.devDone": "Dev done",
    "status.approved": "Approved",
    "status.ready": "Ready",
    "status.draft": "Draft",
    "status.done": "Done",
    "status.clarifying": "Clarifying",
    "status.changed": "Changed",
    "label.business": "Business",
    "label.technical": "Technical",
    "workflow.auto_scan.feature": "Auto Scan",
    "workflow.auto_scan.mission": "Find recurring engineering risk and turn it into review-ready evidence.",
    "workflow.auto_scan.input": "Repositories, scan window, risk signals",
    "workflow.auto_scan.output": "Findings, severity, links, and next questions",
    "workflow.auto_delivery.feature": "Auto Delivery",
    "workflow.auto_delivery.mission": "Move an approved Story through implementation, verification, and delivery.",
    "workflow.auto_delivery.input": "Ready Story, approved plan, delivery policy",
    "workflow.auto_delivery.output": "Commits, checks, PR/merge result, or a clear blocker",
    "workflow.auto_patch.feature": "Auto Patch",
    "workflow.auto_patch.mission": "Pick up Jira Task/Bug work, apply a focused fix, and hand it off safely.",
    "workflow.auto_patch.input": "Eligible Jira card, repository guardrails",
    "workflow.auto_patch.output": "Patch evidence, verification, and PR/direct-push result",
    "workflow.manager.feature": "Manager",
    "workflow.manager.mission": "Clarify intent, create the right work item, and coordinate the three capability owners.",
    "workflow.manager.input": "Business request, missing decisions, loop state",
    "workflow.manager.output": "A question, a work card, or a routed execution request",
    "label.autoScan": "Auto Scan",
    "label.autoDelivery": "Auto Delivery",
    "label.autoPatch": "Auto Patch",
    "label.manager": "Manager",
    "label.entryPoint": "Entry point",
    "label.feishuEntry": "User / Feishu entry",
    "label.managerLayer": "Coordination layer",
    "label.capabilityOwners": "Capability owners",
    "label.role": "Role",
    "label.input": "Input",
    "label.output": "Output",
    "label.owns": "Owns",
    "label.receives": "Receives",
    "label.returns": "Returns",
    "label.gateway": "Gateway",
    "label.agentDefaultLanguage": "Reply language",
    "label.agentsReady": "Agents ready",
    "label.workflowsActive": "Workflows active",
    "label.questionsWaiting": "Questions waiting",
    "label.agentRoles": "Agent roles",
    "label.recordedTurns": "Recorded turns",
    "label.processedQuestions": "Questions handled",
    "label.averageDuration": "Average duration",
    "label.needsAttention": "Needs attention",
    "label.rolesSeen": "Roles seen",
    "label.businessReadyCapabilities": "Three human-owned capabilities",
    "label.conversationClear": "Conversation is clear",
    "label.unanswered": "{{count}} unanswered",
    "label.sharedRuntime": "{{count}} roles · shared runtime",
    "label.currentStory": "Current story",
    "label.status": "Status",
    "label.elapsed": "Elapsed",
    "label.finished": "Finished",
    "label.jiraCard": "Jira card",
    "label.branch": "Branch",
    "label.repositories": "Repositories",
    "label.started": "Started",
    "label.issues": "Issues",
    "label.duration": "Duration",
    "label.artifacts": "Artifacts",
    "label.story": "Story",
    "label.pullRequests": "Pull requests",
    "label.checks": "Checks",
    "label.operation": "Operation",
    "label.finishedAt": "Finished",
    "label.log": "Log",
    "label.summary": "Summary",
    "label.jira": "Jira",
    "label.trace": "Trace",
    "label.repository": "Repository",
    "label.localCommit": "Local commit",
    "label.roleId": "Role id",
    "label.workflow": "Workflow",
    "label.prompt": "prompt",
    "label.conversation": "Conversation",
    "label.typingReaction": "Typing reaction",
    "label.lookbackDays": "Lookback, days",
    "label.cron": "Five-field cron",
    "label.intervalMinutes": "Interval, minutes",
    "label.eligibleStatuses": "Eligible JIRA statuses",
    "label.moveStarted": "Move to when started",
    "label.moveCompleted": "Move to when completed",
    "label.moveFailed": "Move to when failed",
    "label.moveBlocked": "Move to when blocked",
    "label.outputLanguage": "Output language",
    "label.languageGeneration": "Generation language",
    "label.spreadsheetTab": "Spreadsheet tab name",
    "label.spreadsheetToken": "Spreadsheet token / URL",
    "label.cursorModel": "Execution model",
    "label.modelProvider": "Model provider",
    "label.apiBaseUrl": "API base URL",
    "label.apiKeyEnv": "API key environment variable",
    "label.softTimeout": "Soft timeout, seconds",
    "label.hardTimeout": "Hard timeout, seconds",
    "label.maxJobs": "Max concurrent jobs",
    "label.soulVersion": "SOUL version",
    "label.feishuAppId": "Feishu App ID",
    "label.feishuAppSecret": "Feishu App Secret",
    "label.completed": "Completed",
    "label.openFindings": "Open findings",
    "label.successfulScan": "Successful Scan · 7d",
    "label.failed7d": "Failed · 7d",
    "label.lookbackWindow": "Lookback window",
    "label.conversationAndActions": "Conversation and actions available",
    "label.conversationPaused": "Conversation is paused in Settings",
    "label.credentialsRequired": "Credentials are required",
    "label.requestResult": "Request + result",
    "label.resultCaptured": "Result captured · request predates transcript capture",
    "label.traceOnly": "Trace only",
    "label.executionTrail": "Execution trail",
    "label.debugDetails": "Debug details",
    "label.promptNotCaptured": "This runtime did not capture the original prompt.",
    "label.olderTrace": "This older trace has an outcome, but its incoming message was not captured by that runtime version.",
    "label.noFinalResponse": "No final response text was retained; open the source trace in the Agent logs if deeper evidence is needed.",
    "label.activityRetention": "Only bounded local request/result text is shown here. Trace IDs and raw execution evidence remain available in the local Agent store.",
    "label.high": "High",
    "label.medium": "Medium",
    "label.low": "Low",
    "label.untitledFinding": "Untitled finding",
    "label.unknownRepository": "Unknown repository",
    "label.reasonOptional": "Reason (optional)",
    "label.ignoreQuestion": "Mark this finding as ignored?",
    "label.ignorePlaceholder": "Why is this safe to ignore?",
    "label.noSnippet": "No code snippet was captured for this historical finding.",
    "label.notRecorded": "Not recorded.",
    "label.notStarted": "Awaiting delivery trigger",
    "label.running": "Running",
    "label.pending": "Pending",
    "label.stopped": "Stopped",
    "label.needsAttentionState": "Needs attention",
    "label.startedAt": "Started {{value}}",
    "label.finishedAtValue": "Finished {{value}}",
    "label.requested": "Request",
    "label.result": "Result",
    "label.noLog": "No log content recorded.",
    "label.noSchedulerLog": "No scheduler output recorded.",
    "label.noSummary": "No summary recorded.",
    "label.recentRawOutput": "Recent raw output",
    "label.close": "Close",
    "label.checksPassed": "{{count}} passed",
    "label.checksFailed": "{{count}} failed",
    "label.checksSkipped": "{{count}} skipped",
    "label.verification": "Verification",
    "label.checksTitle": "Checks",
    "heading.managerOverview": "Manager overview",
    "heading.agentActivity": "Agent activity",
    "heading.conversationRecords": "Conversation records",
    "heading.agentRoster": "Agent roster",
    "heading.agentTeam": "Agent team & workflows",
    "heading.agentArchitecture": "Agent architecture",
    "heading.workflowControl": "Workflow control",
    "heading.questionsWaiting": "Questions waiting for you",
    "heading.scanHistory": "Scan History",
    "heading.trackedFindings": "Tracked Findings",
    "heading.currentProgress": "Current Progress",
    "heading.deliveryHistory": "Delivery History",
    "heading.schedulerActivity": "Scheduler Activity",
    "heading.patchHistory": "Patch History",
    "heading.stories": "Stories",
    "heading.workspaceSettings": "Workspace settings",
    "heading.agentRoles": "Agent Roles",
    "heading.automationSchedules": "Automation Schedules",
    "heading.executionModels": "Execution Models",
    "heading.publishPolicy": "Publish Policy",
    "heading.notifications": "Notifications",
    "heading.variableKeys": "Variable Keys",
    "heading.testCases": "Test Cases",
    "heading.workflow": "{{feature}} Workflow",
    "action.openSettings": "Open Settings",
    "action.configureAgent": "Configure agent",
    "action.manageCapture": "Manage capture",
    "action.viewActivity": "View activity",
    "action.inspect": "Inspect {{feature}}",
    "action.startScan": "Start scan",
    "action.runCycle": "Run one cycle",
    "action.viewRawLog": "View raw log",
    "action.openLog": "Open failure log",
    "action.markIgnored": "Mark ignored",
    "action.viewDetail": "View detail",
    "action.hideDetail": "Hide detail",
    "action.pullRequest": "Pull request",
    "action.startDelivery": "Start delivery",
    "action.saveChanges": "Save changes",
    "action.savePrompt": "Save prompt",
    "action.searchStories": "Search stories",
    "action.filterStories": "Filter stories",
    "action.showingReadyStories": "Showing business-ready stories",
    "action.filterReadyStories": "Filter business-ready stories",
    "action.exitFullscreen": "Exit full screen",
    "action.viewFullscreen": "View full screen",
    "action.start": "Start",
    "action.save": "Save",
    "action.runScan": "Start a scan?",
    "action.confirmScan": "Confirm scan start",
    "action.scanBody": "This will launch an auto-scan for {{project}}.",
    "action.scanConfirmBody": "Are you sure you want to start a scan for {{project}} now? A scan agent will run against the configured repositories.",
  },
  "zh-Hans": {
    "language.label": "语言",
    "language.en": "English",
    "language.zhHans": "简体中文",
    "language.zhHant": "繁體中文",
    "nav.overview": "总览",
    "nav.activity": "活动记录",
    "nav.scan": "自动扫描",
    "nav.delivery": "自动交付",
    "nav.patch": "自动修复",
    "nav.observatory": "观测台",
    "nav.repositories": "代码仓库",
    "nav.prompts": "工作流",
    "nav.settings": "设置",
    "context.overview.title": "管理者总览",
    "context.overview.description": "查看 Agent 职责、工作流健康度和下一项需要人工决策的事项。",
    "context.activity.title": "Agent 活动",
    "context.activity.description": "查看对话记录、处理结果以及每次 Agent 执行背后的证据。",
    "context.scan.title": "自动扫描",
    "context.scan.description": "查看扫描历史并管理已跟踪的问题。",
    "context.delivery.title": "自动交付",
    "context.delivery.description": "查看 Story 执行、验证和 Pull Request 交付。",
    "context.patch.title": "自动修复",
    "context.patch.description": "查看 Jira Task/Bug 捕获、聚焦修复和安全交接。",
    "context.observatory.title": "观测台",
    "context.observatory.description": "浏览和编辑 Story 说明与技术方案。",
    "context.repositories.title": "代码仓库",
    "context.repositories.description": "管理本地仓库、自动化权限和交付验证策略。",
    "context.prompts.title": "工作流",
    "context.prompts.description": "查看各项本地自动化背后的提示词、脚本、控制点和恢复路径。",
    "context.settings.title": "设置",
    "context.settings.description": "配置工作区、调度和本地集成。",
    "common.updated": "更新于 {{value}}",
    "common.syncing": "同步中…",
    "common.project": "项目",
    "common.currentProject": "当前项目",
    "common.openSettings": "打开设置",
    "common.manageCapture": "管理记录",
    "common.loadingWorkspace": "正在加载本地工作区状态…",
    "common.expandNavigation": "展开导航",
    "common.collapseNavigation": "收起导航",
    "common.version": "版本 {{value}}",
    "common.staticReport": "静态报告模式：交互操作不可用。",
    "common.unableLoadState": "无法加载 Dashboard 状态",
    "common.requestFailed": "请求失败",
    "common.unsavedSettings": "设置中有未保存的更改，要不保存就离开吗？",
    "common.unsavedObservatory": "观测台有未保存的更改，要不保存就离开吗？",
    "common.noData": "暂无数据。",
    "common.cancel": "取消",
    "common.close": "关闭",
    "common.later": "稍后",
    "common.save": "保存",
    "common.saving": "保存中…",
    "common.confirm": "确认",
    "common.continue": "继续",
    "common.start": "开始",
    "common.stop": "停止",
    "common.retry": "重试",
    "common.loading": "加载中…",
    "common.enabled": "已启用",
    "common.paused": "已暂停",
    "common.active": "运行中",
    "common.off": "关闭",
    "common.all": "全部",
    "common.clear": "清除",
    "common.selected": "已选择 {{count}} 项",
    "common.statusesSelected": "已选择 {{count}} 个状态",
    "common.previous": "上一页",
    "common.next": "下一页",
    "common.pageOf": "第 {{page}} 页，共 {{count}} 页",
    "common.showing": "显示 {{count}} 项",
    "common.debugDetails": "调试详情",
    "common.originalPrompt": "发送给 Agent 的原始提示词",
    "common.records": "{{count}} 条记录",
    "common.runs": "{{count}} 次运行",
    "common.recentEvents": "最近 {{count}} 个事件",
    "common.yes": "是",
    "common.no": "否",
    "common.unknown": "未知",
    "common.workspace": "工作区",
    "common.agent": "Agent",
    "common.clarification": "澄清",
    "common.manager": "Manager",
    "common.you": "你",
    "common.trace": "Trace",
    "common.viewActivity": "查看活动",
    "common.viewLog": "查看日志",
    "common.viewTrace": "查看 Trace",
    "common.open": "打开",
    "common.inspect": "查看",
    "common.noAgentRoles": "暂无可用的 Agent 角色。",
    "common.noAgentQuestions": "没有待回答的 Agent 问题。",
    "common.noConversationRecords": "没有符合筛选条件的对话记录。",
    "common.noFindings": "没有符合该状态的问题。",
    "common.noStoriesFilter": "没有符合筛选条件的 Story。",
    "common.noStories": "文档仓库中没有找到 Story。",
    "common.selectStory": "选择一个 Story 查看。",
    "common.noAgentHistory": "暂无 Agent 对话存储。网关启动后，新飞书对话会显示在这里。",
    "common.askAgents": "在飞书中询问 Agent，然后刷新此页面。",
    "common.activityStoreFirstTurn": "首次 Agent 对话后会创建本地活动记录。",
    "common.noDeliveryHistory": "暂无交付历史。",
    "common.noPatchHistory": "暂无自动修复历史。",
    "common.noDeliveryActivity": "暂无已记录的定时交付活动。",
    "common.noPatchActivity": "暂无已记录的自动修复活动。",
    "common.noAgentRolesSettings": "暂无可用的 Agent 角色。",
    "common.noIntegrationKeys": "未配置本地集成密钥。",
    "common.valueFor": "{{name}} 的值",
    "common.revealValue": "显示值",
    "common.copyValue": "复制值",
    "common.copyCode": "复制代码",
    "common.showFullscreen": "全屏显示",
    "common.closeFullscreen": "关闭全屏",
    "common.zoomOut": "缩小",
    "common.resetView": "重置视图",
    "common.zoomIn": "放大",
    "common.diagram": "图表",
    "common.image": "图片",
    "common.formattingTools": "格式工具",
    "common.documentBody": "文档正文",
    "common.add": "添加",
    "common.navigation": "Lumon 导航",
    "common.dashboardSections": "Dashboard 分区",
    "common.explainSetting": "解释此设置",
    "common.originalMarkdown": "原始 Markdown",
    "common.preview": "预览",
    "common.live": "实时",
    "common.attempt": "第 {{number}} 次：{{duration}}",
    "common.overwriting": "覆盖中…",
    "common.overwriteRemote": "覆盖远程版本",
    "common.remoteDecision": "远程更新需要你的决定",
    "common.remoteConflictCopy": "Lumon 已提交本地工作区变更，但远程分支在推送前发生了变化。请先检查远程变更，再决定是否覆盖。",
    "common.onlyTaskBugCards": "这里只显示当前活跃 Sprint 中的 Task 和 Bug 卡片。",
    "common.noPendingPatchCards": "当前活跃 Sprint 中没有待处理的 Auto Patch Jira 卡片。",
    "common.patchFlow": "捕获 → 仓库 → 修复 → 发布",
    "common.retryDeliveryCopy": "这会移除 Story 工作树，重置其 Delivery 和 Jira 状态，然后启动新一轮运行。失败运行和日志仍会保留在历史记录中。",
    "common.repositoryGovernance": "仓库治理",
    "common.addRepository": "添加仓库",
    "common.repositoryIntro": "通过 Git URL 连接仓库。Lumon 会将其克隆到 repos/，检测运行时和构建工具，然后让你批准可以修改或发布代码的自动化能力。",
    "common.attentionNote": "“需要关注”表示存在未提交变更、分支落后远程，或分支/同步发生分叉。",
    "common.repositoryConfiguration": "仓库配置",
    "common.unnamedRepository": "未命名仓库",
    "common.generic": "通用",
    "common.noBuildTool": "未检测到构建工具",
    "common.identityConnection": "身份与连接",
    "common.identityConnectionHelp": "从本地检测得到；只有默认分支是可编辑的连接设置。",
    "common.localPath": "本地路径",
    "common.remote": "远程地址",
    "common.gitStatus": "Git 状态",
    "common.branchSync": "分支同步",
    "common.defaultBranch": "默认分支",
    "common.runtimeBuild": "运行时与构建",
    "common.runtimeBuildHelp": "从仓库文件中检测得到。仓库发生变化前，这些值为只读。",
    "common.language": "语言",
    "common.java": "Java",
    "common.node": "Node",
    "common.buildTools": "构建工具",
    "common.notDetected": "未检测到",
    "common.automationPermissions": "自动化权限",
    "common.frontendDeliveryDisabled": "前端交付在全局策略中保持关闭，无法在这里启用。",
    "common.autoScanFixes": "Auto Scan 修复",
    "common.autoScanFixesHelp": "允许高置信度的 Scan 修复及其配置的发布流程。",
    "common.deliveryPermission": "Auto Delivery",
    "common.deliveryPermissionHelp": "允许此仓库执行已批准的技术交付工作。",
    "common.patchPermission": "Auto Patch",
    "common.patchPermissionHelp": "允许针对 Jira 驱动的修复并发布。",
    "common.deliveryVerification": "交付验证",
    "common.deliveryVerificationHelp": "选择实现完成后 Lumon 应为此仓库运行哪些验证。",
    "common.policy": "策略",
    "common.runVerification": "运行验证",
    "common.runVerificationHelp": "使用自动配置或你自定义的命令。",
    "common.skipVerification": "跳过验证",
    "common.skipVerificationHelp": "不运行编译、静态检查或测试。",
    "common.executionSource": "执行来源",
    "common.automaticProfile": "自动配置",
    "common.automaticProfileHelp": "运行时从仓库文件中检测命令。",
    "common.customCommands": "自定义命令",
    "common.customCommandsHelp": "只运行下面输入的命令。",
    "common.checksToRun": "要运行的检查",
    "common.compileChecks": "编译与静态检查",
    "common.compileChecksHelp": "编译、语法、类型检查、Lint 或 PMD 检查。",
    "common.tests": "测试",
    "common.testsHelp": "单元测试、集成测试和测试套件命令。",
    "common.commands": "命令",
    "common.useSuggestedCommands": "使用 {{count}} 条建议命令{{suffix}}",
    "common.oneCommandPerLine": "每行一条命令。",
    "common.cloneUrl": "克隆 URL",
    "common.cloneInspect": "克隆并检查",
    "common.addRepositoryDescription": "Lumon 会克隆 Git URL、检测分支和工具，启用现有的 Scan 与 Delivery 行为，并默认授权 Auto Patch。",
    "common.settingsSections": "设置分区",
    "common.schedules": "调度",
    "common.agentConversations": "Agent 对话",
    "common.integrations": "集成",
    "common.configuredKeys": "个已配置密钥",
    "settings.automation": "自动化",
    "settings.automationDescription": "决定工作何时可以推进的调度和执行策略。",
    "settings.agentTeam": "Agent 团队",
    "settings.agentTeamDescription": "谁与人沟通、各角色负责什么，以及哪些对话可以修改状态。",
    "settings.projectOutput": "项目产出",
    "settings.projectOutputDescription": "Mark 和 Milchick 将请求转成可测试 Story 时使用的默认设置。",
    "settings.runtime": "运行时与集成",
    "settings.runtimeDescription": "模型选择、发布行为、通知和本地密钥值。",
    "settings.nextAgentTeam": "下一步：Agent 团队",
    "settings.nextProjectOutput": "下一步：项目产出",
    "settings.nextRuntime": "下一步：运行时与集成",
    "settings.backAutomation": "返回自动化",
    "settings.localConfiguration": "本地配置",
    "settings.controlPlane": "01 · 控制面",
    "settings.humanAgents": "02 · 面向人的 Agent",
    "settings.businessOutput": "03 · 业务产出",
    "settings.operatingDetails": "04 · 运行细节",
    "settings.globalFeishuAgents": "全局飞书 Agent",
    "settings.defaultReplyLanguage": "Agent 默认回复语言",
    "settings.defaultReplyLanguageDescription": "当用户没有明确建立语言时使用。它与 Dashboard 界面语言相互独立。",
    "settings.accessControl": "访问控制",
    "settings.accessControlDescription": "群组按整个群授权，私聊则需要逐个授权。系统会从每个已配置的 Agent 应用发现它加入的群组。",
    "settings.accessPerson": "用户",
    "settings.accessChat": "群聊",
    "settings.selectPerson": "选择用户",
    "settings.selectChat": "选择群聊",
    "settings.identityRoles": "此身份的访问权限",
    "settings.selectIdentityHelp": "选择一个身份，然后编辑下面的三项访问权限。",
    "settings.canTalk": "可以与 Agent 对话",
    "settings.canMutate": "可以执行变更操作",
    "settings.canAdmin": "可以管理 Agent",
    "settings.accessSummary": "已配置身份",
    "settings.identityCount": "{{count}} 个身份记录",
    "settings.pendingAccess": "待授权",
    "settings.rolesApplied": "项权限",
    "settings.agentCoreDescription": "这里只编辑核心控制项。角色归属、安全边界和 SOUL 文件仍由 Agent 注册表管理。",
    "settings.responsibility": "职责",
    "settings.legacyWarning": "旧版 allow 模式对本地 Agent 不安全。建议使用按 Agent 配置的 Access & Exposure，并将 default_policy 设为 deny。",
    "settings.recentPeople": "最近联系人",
    "settings.recentChats": "最近群聊",
    "settings.groupChats": "已授权群组",
    "settings.groupChatsDescription": "允许群组后，群内所有人都可以与 Agent 沟通，不需要逐一授权。",
    "settings.privateContacts": "私聊联系人",
    "settings.privateContactsDescription": "私聊按人员逐一授权。请确认显示名称和飞书 ID 后再开启权限。",
    "settings.noGroupChats": "暂时没有发现飞书群组。",
    "settings.noPrivateContacts": "暂时没有发现私聊联系人。",
    "settings.agentMembership": "Agents：{{value}}",
    "settings.addMutationUser": "点击添加为可变更用户",
    "settings.allowChat": "点击允许此群聊",
    "settings.noRecentPeople": "暂无最近的飞书联系人。先给 Dylan 或 Mark 发一条消息，再刷新设置。",
    "settings.generationLanguage": "生成语言",
    "settings.generationDescription": "控制 Mark 为此项目写入飞书电子表格的语言。mbpass 默认使用繁体中文。",
    "settings.afterGeneration": "修改语言或表格后，请让 Milchick/Mark 重新生成 Story，使新行使用选定的表格。",
    "settings.executionDescription": "选择提供商和模型 ID。Lumon 会通过所选提供商发送 API 请求，不会验证模型是否可用。",
    "settings.modelCenter": "模型中心",
    "settings.modelCenterDescription": "在一个地方配置所有对话 Agent 和自动化模型。",
    "settings.globalModelConfig": "全局 AI 配置",
    "settings.globalModelScope": "应用于四个对话 Agent 和三个自动化工作流。",
    "settings.inheritsGlobalModel": "继承全局配置",
    "settings.conversationModels": "对话 Agent",
    "settings.conversationModelsDescription": "所有飞书 Agent 都使用上方的全局提供商和模型。",
    "settings.workflowModels": "自动化工作流",
    "settings.workflowModelsDescription": "自动扫描、自动交付和自动修复使用同一组全局提供商和模型。",
    "settings.workflowRuntimeLabel": "应用于所有 Agent 和工作流",
    "settings.openCodeHarness": "OpenCode Harness",
    "settings.openCodeHarnessDescription": "通过 OpenCode 调用已配置的模型，由 OpenCode 管理工作区工具和持久会话。",
    "settings.codexHarness": "Codex CLI",
    "settings.codexHarnessDescription": "Codex CLI 使用选定的本地 ChatGPT 账号、完整主机与网络访问和持久会话。",
    "settings.openCodeRuntime": "Agent 运行时",
    "settings.openCodeRuntimeDescription": "这里显示对话 Agent 和自动化工作流实际使用的 Harness 状态。",
    "settings.harness": "Harness",
    "settings.runtimeModel": "模型",
    "settings.cliVersion": "CLI 版本",
    "settings.sessionMode": "会话",
    "settings.permissionProfile": "权限",
    "settings.harnessStatus": "Harness 就绪状态",
    "settings.harnessStatusDescription": "Provider 可以使用原生工具和规范工作区；飞书信任门与审计仍由 Host 基础设施负责。",
    "settings.harnessMode": "模式",
    "settings.harnessCapabilities": "能力",
    "settings.harnessSecurity": "安全边界",
    "settings.harnessWarnings": "警告",
    "settings.harnessReady": "已就绪",
    "settings.harnessBlocked": "已阻断",
    "settings.actionCatalog": "Action 清单",
    "settings.deepSeekCredential": "模型凭证",
    "settings.runtimeAccount": "Codex 账号",
    "settings.reasoningEffort": "推理强度",
    "settings.deepSeekCredentialConfigured": "已配置于 ~/.lumon/.env.local",
    "settings.deepSeekCredentialMissing": "未配置（本地模型无需密钥）",
    "settings.automationOutcome": "自动化结果",
    "settings.notificationsDescription": "控制 Scan 和 Delivery 是否向已配置的飞书 Webhook 发布卡片。Webhook URL 仍位于变量密钥中。",
    "settings.storedWorkspace": "存储在此工作区",
    "settings.storedWorkspaceOrLumon": "工作区 + Lumon 本地",
    "settings.storedLumon": "存储在 Lumon 本地",
    "settings.availableKeys": "可用密钥",
    "settings.availableKeysDescription": "显示值以检查，或直接输入替换值。保存时不会包含显示引号。",
    "settings.revealReplacement": "显示或输入替换值",
    "settings.unsavedChanges": "有未保存的更改",
    "settings.allSaved": "所有更改已保存",
    "settings.deliveryPaused": "交付轮询已暂停。",
    "settings.patchPaused": "Auto Patch 轮询已暂停。",
    "settings.deliveryStatusHelp": "选择所有可以启动 Auto Delivery 的 Jira 状态。Story 还必须处于 Business Ready、Technical Approved 且未在运行。",
    "settings.deliveryStatusNote": "选择 To Do、Backlog、In Progress 或其他符合条件的 Jira 状态。失败时，Lumon 会将 Jira 卡片流转到选定的 Block 状态，并添加需要关注的评论。",
    "settings.patchStatusNote": "只捕获 Task 和 Bug 卡片。阻塞卡片会在收到新的外部 Jira 评论后重试。",
    "settings.scanDefaultDescription": "尚未配置周期性扫描。",
    "settings.direct": "直接推送",
    "settings.merge": "合并",
    "settings.pullRequest": "PR",
    "settings.openPullRequest": "打开 Pull Request",
    "settings.mergeAfterPullRequest": "在 Pull Request 后合并",
    "settings.pushDirectly": "直接推送到 main 分支",
    "settings.feishuNotifications": "飞书通知",
    "settings.allowedChatIds": "允许的群聊 ID",
    "settings.allowedUserIds": "允许的用户 ID",
    "settings.mutationUserIds": "可变更用户 ID",
    "settings.adminUserIds": "管理员用户 ID",
    "settings.allowedChatHelp": "将群聊按整个群加入白名单。私聊仍需逐一授权；在群聊中仍必须 @提及。",
    "settings.allowedUserHelp": "为空表示所有用户都可以询问只读问题。",
    "settings.mutationUserHelp": "解决问题、更新调度和启动交付时必需。为空时默认拒绝。",
    "settings.adminUserHelp": "管理员也可以执行变更操作。",
    "settings.appSecretRequired": "飞书客户端登录必需。",
    "settings.keepSecret": "留空以保留当前密钥",
    "settings.enterSecret": "输入 App Secret",
    "settings.runtimeIdentityHelp": "运行时身份由 Agent 注册表管理。",
    "settings.workflowOwnershipHelp": "工作流归属由 Agent 注册表管理。",
    "settings.publishDescription": "直接推送使用已配置的 Git 仓库凭证；PR 和合并使用 GitHub CLI。Auto Scan 保留 PR 审查门禁，不支持直接推送。",
    "settings.deploymentTracking": "部署状态跟踪",
    "settings.deploymentTrackingDescription": "发布后跟踪配置好的 CI/CD 运行，并只在部署真正完成后回报结果。凭证保留在本地环境变量中。",
    "settings.deploymentProvider": "提供商",
    "settings.deploymentDisabled": "未启用",
    "settings.jenkins": "Jenkins",
    "settings.githubActions": "GitHub Actions",
    "settings.pollInterval": "轮询间隔（秒）",
    "settings.deploymentTimeout": "超时（秒）",
    "settings.deploymentProviderHelp": "发布后需要观察哪个 CI/CD 系统的部署运行。",
    "settings.deploymentOwner": "跟踪负责人",
    "settings.deploymentOwnerValue": "Milchick · 工程运营经理",
    "settings.deploymentOwnerHelp": "Milchick 负责判断后续归属：源码或交付失败交给 Mark，Jira 修复交给 Irving，基础设施或无法判断的问题回报人工决策。",
    "settings.deploymentFailureHandling": "后台 worker 负责轮询提供商；Milchick 接收最终证据并决定下一位负责人，不再把所有失败硬编码交给 Mark。",
    "settings.credentials": "凭证",
    "settings.configured": "已配置",
    "settings.notConfigured": "未配置",
    "settings.localGhLogin": "本地 gh 登录",
    "settings.jenkinsPipeline": "Jenkins 部署流水线",
    "settings.jenkinsPipelineHelp": "用于定位需要观察的 Jenkins 流水线。例如：folder/job-name。Lumon 不会用此字段执行代码。",
    "settings.jenkinsCredentials": "请在变量密钥中配置 JENKINS_URL 和 JENKINS_AUTH。值保留在工作区环境中，不会写入 delivery.json。",
    "settings.githubCredentials": "GitHub Actions 使用工作区运行器的本地 gh 登录状态。这里不输入也不保存 Token。",
    "settings.githubRepository": "GitHub 仓库",
    "settings.githubWorkflow": "Workflow（可选）",
    "label.deployment": "部署",
    "label.provider": "提供商",
    "label.lastChecked": "最近检查",
    "action.openDeployment": "打开部署",
    "editor.heading": "标题",
    "editor.editLink": "编辑链接 URL",
    "editor.linkUrl": "链接 URL",
    "editor.bold": "粗体",
    "editor.italic": "斜体",
    "editor.link": "链接 — Shift+点击链接可定位光标，然后编辑",
    "editor.list": "列表",
    "editor.code": "代码",
    "prompt.original": "原始 Markdown",
    "prompt.preview": "预览",
    "customModel.enter": "输入自定义模型",
    "customModel.id": "模型 ID",
    "customModel.placeholder": "例如：deepseek-v4-flash",
    "customModel.copy": "Lumon 不会验证模型是否可用，该值将在下一次运行时使用。",
    "customModel.edit": "编辑自定义模型",
    "customModel.option": "自定义模型 ID…",
    "customModel.badge": "自定义",
    "customModel.help": "使用所选提供商支持的模型 ID。",
    "status.completed": "已完成",
    "status.passed": "通过",
    "status.failed": "失败",
    "status.skipped": "已跳过",
    "status.open": "开放",
    "status.inProgress": "进行中",
    "status.awaitingDeploy": "等待部署",
    "status.running": "运行中",
    "status.active": "活跃",
    "status.notSet": "未设置",
    "status.notConfigured": "未配置",
    "status.resolved": "已解决",
    "status.reopened": "已重新打开",
    "status.synced": "已同步",
    "status.ignored": "已忽略",
    "status.blocked": "已阻塞",
    "status.pending": "待处理",
    "status.prOpen": "PR 已打开",
    "status.notStarted": "未开始",
    "status.devDone": "开发完成",
    "status.approved": "已批准",
    "status.ready": "就绪",
    "status.draft": "草稿",
    "status.done": "完成",
    "status.clarifying": "澄清中",
    "status.changed": "已变更",
    "label.business": "业务",
    "label.technical": "技术",
    "workflow.auto_scan.feature": "自动扫描",
    "workflow.auto_scan.mission": "发现反复出现的工程风险，并整理成可供评审的证据。",
    "workflow.auto_scan.input": "代码仓库、扫描窗口、风险信号",
    "workflow.auto_scan.output": "问题、严重程度、链接和后续问题",
    "workflow.auto_delivery.feature": "自动交付",
    "workflow.auto_delivery.mission": "推动已批准的 Story 完成实现、验证和交付。",
    "workflow.auto_delivery.input": "就绪 Story、已批准方案、交付策略",
    "workflow.auto_delivery.output": "提交、检查、PR/合并结果，或明确的阻塞原因",
    "workflow.auto_patch.feature": "自动修复",
    "workflow.auto_patch.mission": "接手 Jira Task/Bug，完成聚焦修复并安全交接。",
    "workflow.auto_patch.input": "符合条件的 Jira 卡片、仓库边界",
    "workflow.auto_patch.output": "修复证据、验证结果和 PR/直接推送结果",
    "workflow.manager.feature": "Manager",
    "workflow.manager.mission": "澄清意图、创建合适的工作项，并协调三个能力负责人。",
    "workflow.manager.input": "业务请求、待决策事项、Loop 状态",
    "workflow.manager.output": "一个问题、一张工作卡，或一项路由后的执行请求",
    "label.autoScan": "自动扫描",
    "label.autoDelivery": "自动交付",
    "label.autoPatch": "自动修复",
    "label.manager": "Manager",
    "label.entryPoint": "入口",
    "label.feishuEntry": "用户 / 飞书入口",
    "label.managerLayer": "协调层",
    "label.capabilityOwners": "能力负责人",
    "label.role": "角色",
    "label.input": "输入",
    "label.output": "输出",
    "label.owns": "负责",
    "label.receives": "接收",
    "label.returns": "产出",
    "label.gateway": "网关",
    "label.agentDefaultLanguage": "回复语言",
    "label.agentsReady": "就绪 Agent",
    "label.workflowsActive": "运行中工作流",
    "label.questionsWaiting": "待回答问题",
    "label.agentRoles": "Agent 角色",
    "label.recordedTurns": "已记录对话",
    "label.processedQuestions": "已处理问题",
    "label.averageDuration": "平均耗时",
    "label.needsAttention": "需要关注",
    "label.rolesSeen": "涉及角色",
    "label.businessReadyCapabilities": "三个真人负责的能力",
    "label.conversationClear": "对话清晰",
    "label.unanswered": "{{count}} 个未回答",
    "label.sharedRuntime": "{{count}} 个角色 · 共享运行时",
    "label.currentStory": "当前 Story",
    "label.status": "状态",
    "label.elapsed": "耗时",
    "label.finished": "结束时间",
    "label.jiraCard": "Jira 卡片",
    "label.branch": "分支",
    "label.repositories": "代码仓库",
    "label.started": "开始时间",
    "label.issues": "问题",
    "label.duration": "时长",
    "label.artifacts": "产物",
    "label.story": "Story",
    "label.pullRequests": "Pull Request",
    "label.checks": "检查",
    "label.operation": "操作",
    "label.finishedAt": "结束时间",
    "label.log": "日志",
    "label.summary": "摘要",
    "label.jira": "Jira",
    "label.trace": "Trace",
    "label.repository": "代码仓库",
    "label.localCommit": "本地提交",
    "label.roleId": "角色 ID",
    "label.workflow": "工作流",
    "label.prompt": "提示词",
    "label.conversation": "对话",
    "label.typingReaction": "输入反馈",
    "label.lookbackDays": "回溯天数",
    "label.cron": "五字段 Cron",
    "label.intervalMinutes": "间隔（分钟）",
    "label.eligibleStatuses": "符合条件的 Jira 状态",
    "label.moveStarted": "开始时流转到",
    "label.moveCompleted": "完成时流转到",
    "label.moveFailed": "失败时流转到",
    "label.moveBlocked": "阻塞时流转到",
    "label.outputLanguage": "输出语言",
    "label.languageGeneration": "生成语言",
    "label.spreadsheetTab": "表格页签名称",
    "label.spreadsheetToken": "表格 Token / URL",
    "label.cursorModel": "执行模型",
    "label.modelProvider": "模型提供商",
    "label.apiBaseUrl": "API 基础 URL",
    "label.apiKeyEnv": "API Key 环境变量",
    "label.softTimeout": "软超时（秒）",
    "label.hardTimeout": "硬超时（秒）",
    "label.maxJobs": "最大并发任务数",
    "label.soulVersion": "SOUL 版本",
    "label.feishuAppId": "飞书 App ID",
    "label.feishuAppSecret": "飞书 App Secret",
    "label.completed": "已完成",
    "label.openFindings": "开放问题",
    "label.successfulScan": "成功扫描 · 7 天",
    "label.failed7d": "失败 · 7 天",
    "label.lookbackWindow": "回溯窗口",
    "label.conversationAndActions": "对话和操作均可用",
    "label.conversationPaused": "对话已在设置中暂停",
    "label.credentialsRequired": "需要配置凭证",
    "label.requestResult": "请求 + 结果",
    "label.resultCaptured": "已记录结果 · 请求来自未记录转录的旧版本",
    "label.traceOnly": "仅 Trace",
    "label.executionTrail": "执行轨迹",
    "label.debugDetails": "调试详情",
    "label.promptNotCaptured": "当前运行时没有记录原始提示词。",
    "label.olderTrace": "这条旧 Trace 有结果，但当时的运行时没有记录收到的消息。",
    "label.noFinalResponse": "没有保留最终响应文本；如需更多证据，请打开 Agent 日志中的源 Trace。",
    "label.activityRetention": "这里只显示有边界的本地请求/结果文本。Trace ID 和原始执行证据仍保存在本地 Agent 存储中。",
    "label.high": "高",
    "label.medium": "中",
    "label.low": "低",
    "label.untitledFinding": "未命名问题",
    "label.unknownRepository": "未知代码仓库",
    "label.reasonOptional": "原因（可选）",
    "label.ignoreQuestion": "要将此问题标记为忽略吗？",
    "label.ignorePlaceholder": "为什么可以安全忽略？",
    "label.noSnippet": "此历史问题没有记录代码片段。",
    "label.notRecorded": "未记录。",
    "label.notStarted": "等待交付触发",
    "label.running": "运行中",
    "label.pending": "待处理",
    "label.stopped": "已停止",
    "label.needsAttentionState": "需要关注",
    "label.startedAt": "开始于 {{value}}",
    "label.finishedAtValue": "结束于 {{value}}",
    "label.requested": "请求",
    "label.result": "结果",
    "label.noLog": "没有记录日志内容。",
    "label.noSchedulerLog": "没有记录调度输出。",
    "label.noSummary": "没有记录摘要。",
    "label.recentRawOutput": "最近的原始输出",
    "label.close": "关闭",
    "label.checksPassed": "{{count}} 个通过",
    "label.checksFailed": "{{count}} 个失败",
    "label.checksSkipped": "{{count}} 个跳过",
    "label.verification": "验证",
    "label.checksTitle": "检查",
    "heading.managerOverview": "Manager 总览",
    "heading.agentActivity": "Agent 活动",
    "heading.conversationRecords": "对话记录",
    "heading.agentRoster": "Agent 阵容",
    "heading.agentTeam": "Agent 阵容与工作流",
    "heading.agentArchitecture": "Agent 架构",
    "heading.workflowControl": "工作流控制",
    "heading.questionsWaiting": "等待你的问题",
    "heading.scanHistory": "扫描历史",
    "heading.trackedFindings": "跟踪中的问题",
    "heading.currentProgress": "当前进度",
    "heading.deliveryHistory": "交付历史",
    "heading.schedulerActivity": "调度活动",
    "heading.patchHistory": "修复历史",
    "heading.stories": "Stories",
    "heading.workspaceSettings": "工作区设置",
    "heading.agentRoles": "Agent 角色",
    "heading.automationSchedules": "自动化调度",
    "heading.executionModels": "执行模型",
    "heading.publishPolicy": "发布策略",
    "heading.notifications": "通知",
    "heading.variableKeys": "变量密钥",
    "heading.testCases": "测试用例",
    "heading.workflow": "{{feature}} 工作流",
    "action.openSettings": "打开设置",
    "action.configureAgent": "配置 Agent",
    "action.manageCapture": "管理记录",
    "action.viewActivity": "查看活动",
    "action.inspect": "查看 {{feature}}",
    "action.startScan": "开始扫描",
    "action.runCycle": "运行一轮",
    "action.viewRawLog": "查看原始日志",
    "action.openLog": "打开失败日志",
    "action.markIgnored": "标记为忽略",
    "action.viewDetail": "查看详情",
    "action.hideDetail": "隐藏详情",
    "action.pullRequest": "Pull Request",
    "action.startDelivery": "开始交付",
    "action.saveChanges": "保存更改",
    "action.savePrompt": "保存提示词",
    "action.searchStories": "搜索 Story",
    "action.filterStories": "筛选 Story",
    "action.showingReadyStories": "正在显示业务就绪的 Story",
    "action.filterReadyStories": "筛选业务就绪的 Story",
    "action.exitFullscreen": "退出全屏",
    "action.viewFullscreen": "查看全屏",
    "action.start": "开始",
    "action.save": "保存",
    "action.runScan": "开始扫描吗？",
    "action.confirmScan": "确认开始扫描",
    "action.scanBody": "这将为 {{project}} 启动自动扫描。",
    "action.scanConfirmBody": "确定现在为 {{project}} 启动扫描吗？扫描 Agent 将针对已配置的代码仓库运行。",
  },
  "zh-Hant": {
    "language.label": "語言",
    "language.en": "English",
    "language.zhHans": "簡體中文",
    "language.zhHant": "繁體中文",
    "nav.overview": "總覽",
    "nav.activity": "活動記錄",
    "nav.scan": "自動掃描",
    "nav.delivery": "自動交付",
    "nav.patch": "自動修復",
    "nav.observatory": "觀測台",
    "nav.repositories": "程式碼儲存庫",
    "nav.prompts": "工作流",
    "nav.settings": "設定",
    "context.overview.title": "管理者總覽",
    "context.overview.description": "查看 Agent 職責、工作流健康度和下一項需要人工決策的事項。",
    "context.activity.title": "Agent 活動",
    "context.activity.description": "查看對話記錄、處理結果以及每次 Agent 執行背後的證據。",
    "context.scan.title": "自動掃描",
    "context.scan.description": "查看掃描歷史並管理已追蹤的問題。",
    "context.delivery.title": "自動交付",
    "context.delivery.description": "查看 Story 執行、驗證和 Pull Request 交付。",
    "context.patch.title": "自動修復",
    "context.patch.description": "查看 Jira Task/Bug 擷取、聚焦修復和安全交接。",
    "context.observatory.title": "觀測台",
    "context.observatory.description": "瀏覽和編輯 Story 說明與技術方案。",
    "context.repositories.title": "程式碼儲存庫",
    "context.repositories.description": "管理本地儲存庫、自動化權限和交付驗證策略。",
    "context.prompts.title": "工作流",
    "context.prompts.description": "查看各項本地自動化背後的提示詞、腳本、控制點和恢復路徑。",
    "context.settings.title": "設定",
    "context.settings.description": "配置工作區、排程和本地整合。",
    "common.updated": "更新於 {{value}}",
    "common.syncing": "同步中…",
    "common.project": "專案",
    "common.currentProject": "目前專案",
    "common.openSettings": "開啟設定",
    "common.manageCapture": "管理記錄",
    "common.loadingWorkspace": "正在載入本地工作區狀態…",
    "common.expandNavigation": "展開導覽",
    "common.collapseNavigation": "收起導覽",
    "common.version": "版本 {{value}}",
    "common.staticReport": "靜態報告模式：互動操作不可用。",
    "common.unableLoadState": "無法載入 Dashboard 狀態",
    "common.requestFailed": "請求失敗",
    "common.unsavedSettings": "設定中有未儲存的變更，要不儲存就離開嗎？",
    "common.unsavedObservatory": "觀測台有未儲存的變更，要不儲存就離開嗎？",
    "common.noData": "暫無資料。",
    "common.cancel": "取消",
    "common.close": "關閉",
    "common.later": "稍後",
    "common.save": "儲存",
    "common.saving": "儲存中…",
    "common.confirm": "確認",
    "common.continue": "繼續",
    "common.start": "開始",
    "common.stop": "停止",
    "common.retry": "重試",
    "common.loading": "載入中…",
    "common.enabled": "已啟用",
    "common.paused": "已暫停",
    "common.active": "執行中",
    "common.off": "關閉",
    "common.all": "全部",
    "common.clear": "清除",
    "common.selected": "已選擇 {{count}} 項",
    "common.statusesSelected": "已選擇 {{count}} 個狀態",
    "common.previous": "上一頁",
    "common.next": "下一頁",
    "common.pageOf": "第 {{page}} 頁，共 {{count}} 頁",
    "common.showing": "顯示 {{count}} 項",
    "common.debugDetails": "除錯詳情",
    "common.originalPrompt": "傳送給 Agent 的原始提示詞",
    "common.records": "{{count}} 筆記錄",
    "common.runs": "{{count}} 次執行",
    "common.recentEvents": "最近 {{count}} 個事件",
    "common.yes": "是",
    "common.no": "否",
    "common.unknown": "未知",
    "common.workspace": "工作區",
    "common.agent": "Agent",
    "common.clarification": "釐清",
    "common.manager": "Manager",
    "common.you": "你",
    "common.trace": "Trace",
    "common.viewActivity": "查看活動",
    "common.viewLog": "查看日誌",
    "common.viewTrace": "查看 Trace",
    "common.open": "開啟",
    "common.inspect": "查看",
    "common.noAgentRoles": "暫無可用的 Agent 角色。",
    "common.noAgentQuestions": "沒有待回答的 Agent 問題。",
    "common.noConversationRecords": "沒有符合篩選條件的對話記錄。",
    "common.noFindings": "沒有符合該狀態的問題。",
    "common.noStoriesFilter": "沒有符合篩選條件的 Story。",
    "common.noStories": "文件儲存庫中沒有找到 Story。",
    "common.selectStory": "選擇一個 Story 查看。",
    "common.noAgentHistory": "暫無 Agent 對話儲存。閘道啟動後，新飛書對話會顯示在這裡。",
    "common.askAgents": "在飛書中詢問 Agent，然後重新整理此頁面。",
    "common.activityStoreFirstTurn": "首次 Agent 對話後會建立本地活動記錄。",
    "common.noDeliveryHistory": "暫無交付歷史。",
    "common.noPatchHistory": "暫無自動修復歷史。",
    "common.noDeliveryActivity": "暫無已記錄的定時交付活動。",
    "common.noPatchActivity": "暫無已記錄的自動修復活動。",
    "common.noAgentRolesSettings": "暫無可用的 Agent 角色。",
    "common.noIntegrationKeys": "未設定本地整合金鑰。",
    "common.valueFor": "{{name}} 的值",
    "common.revealValue": "顯示值",
    "common.copyValue": "複製值",
    "common.copyCode": "複製程式碼",
    "common.showFullscreen": "全螢幕顯示",
    "common.closeFullscreen": "關閉全螢幕",
    "common.zoomOut": "縮小",
    "common.resetView": "重設視圖",
    "common.zoomIn": "放大",
    "common.diagram": "圖表",
    "common.image": "圖片",
    "common.formattingTools": "格式工具",
    "common.documentBody": "文件正文",
    "common.add": "新增",
    "common.navigation": "Lumon 導航",
    "common.dashboardSections": "Dashboard 區段",
    "common.explainSetting": "解釋此設定",
    "common.originalMarkdown": "原始 Markdown",
    "common.preview": "預覽",
    "common.live": "即時",
    "common.attempt": "第 {{number}} 次：{{duration}}",
    "common.overwriting": "覆寫中…",
    "common.overwriteRemote": "覆寫遠端版本",
    "common.remoteDecision": "遠端更新需要你的決定",
    "common.remoteConflictCopy": "Lumon 已提交本地工作區變更，但遠端分支在推送前發生了變化。請先檢查遠端變更，再決定是否覆寫。",
    "common.onlyTaskBugCards": "這裡只顯示目前活躍 Sprint 中的 Task 和 Bug 卡片。",
    "common.noPendingPatchCards": "目前活躍 Sprint 中沒有待處理的 Auto Patch Jira 卡片。",
    "common.patchFlow": "捕獲 → 儲存庫 → 修復 → 發布",
    "common.retryDeliveryCopy": "這會移除 Story 工作樹，重置其 Delivery 和 Jira 狀態，然後啟動新一輪執行。失敗執行和日誌仍會保留在歷史紀錄中。",
    "common.repositoryGovernance": "儲存庫治理",
    "common.addRepository": "新增儲存庫",
    "common.repositoryIntro": "透過 Git URL 連接儲存庫。Lumon 會將其複製到 repos/，偵測執行環境和建置工具，然後讓你批准可以修改或發布程式碼的自動化能力。",
    "common.attentionNote": "「需要關注」表示存在未提交變更、分支落後遠端，或分支/同步發生分叉。",
    "common.repositoryConfiguration": "儲存庫設定",
    "common.unnamedRepository": "未命名儲存庫",
    "common.generic": "通用",
    "common.noBuildTool": "未偵測到建置工具",
    "common.identityConnection": "身分與連線",
    "common.identityConnectionHelp": "從本地偵測得到；只有預設分支是可編輯的連線設定。",
    "common.localPath": "本地路徑",
    "common.remote": "遠端位址",
    "common.gitStatus": "Git 狀態",
    "common.branchSync": "分支同步",
    "common.defaultBranch": "預設分支",
    "common.runtimeBuild": "執行環境與建置",
    "common.runtimeBuildHelp": "從儲存庫檔案中偵測得到。儲存庫發生變化前，這些值為唯讀。",
    "common.language": "語言",
    "common.java": "Java",
    "common.node": "Node",
    "common.buildTools": "建置工具",
    "common.notDetected": "未偵測到",
    "common.automationPermissions": "自動化權限",
    "common.frontendDeliveryDisabled": "前端交付在全域策略中保持關閉，無法在這裡啟用。",
    "common.autoScanFixes": "Auto Scan 修復",
    "common.autoScanFixesHelp": "允許高信心度的 Scan 修復及其設定的發布流程。",
    "common.deliveryPermission": "Auto Delivery",
    "common.deliveryPermissionHelp": "允許此儲存庫執行已批准的技術交付工作。",
    "common.patchPermission": "Auto Patch",
    "common.patchPermissionHelp": "允許針對 Jira 驅動的修復並發布。",
    "common.deliveryVerification": "交付驗證",
    "common.deliveryVerificationHelp": "選擇實作完成後 Lumon 應為此儲存庫執行哪些驗證。",
    "common.policy": "策略",
    "common.runVerification": "執行驗證",
    "common.runVerificationHelp": "使用自動設定或你自訂的指令。",
    "common.skipVerification": "跳過驗證",
    "common.skipVerificationHelp": "不執行編譯、靜態檢查或測試。",
    "common.executionSource": "執行來源",
    "common.automaticProfile": "自動設定",
    "common.automaticProfileHelp": "執行時從儲存庫檔案中偵測指令。",
    "common.customCommands": "自訂指令",
    "common.customCommandsHelp": "只執行下面輸入的指令。",
    "common.checksToRun": "要執行的檢查",
    "common.compileChecks": "編譯與靜態檢查",
    "common.compileChecksHelp": "編譯、語法、型別檢查、Lint 或 PMD 檢查。",
    "common.tests": "測試",
    "common.testsHelp": "單元測試、整合測試和測試套件指令。",
    "common.commands": "指令",
    "common.useSuggestedCommands": "使用 {{count}} 條建議指令{{suffix}}",
    "common.oneCommandPerLine": "每行一條指令。",
    "common.cloneUrl": "複製 URL",
    "common.cloneInspect": "複製並檢查",
    "common.addRepositoryDescription": "Lumon 會複製 Git URL、偵測分支和工具，啟用現有的 Scan 與 Delivery 行為，並預設授權 Auto Patch。",
    "common.settingsSections": "設定區段",
    "common.schedules": "排程",
    "common.agentConversations": "Agent 對話",
    "common.integrations": "整合",
    "common.configuredKeys": "個已設定金鑰",
    "settings.automation": "自動化",
    "settings.automationDescription": "決定工作何時可以推進的排程和執行策略。",
    "settings.agentTeam": "Agent 團隊",
    "settings.agentTeamDescription": "誰與人溝通、各角色負責什麼，以及哪些對話可以修改狀態。",
    "settings.projectOutput": "專案產出",
    "settings.projectOutputDescription": "Mark 和 Milchick 將請求轉成可測試 Story 時使用的預設設定。",
    "settings.runtime": "執行環境與整合",
    "settings.runtimeDescription": "模型選擇、發布行為、通知和本地金鑰值。",
    "settings.nextAgentTeam": "下一步：Agent 團隊",
    "settings.nextProjectOutput": "下一步：專案產出",
    "settings.nextRuntime": "下一步：執行環境與整合",
    "settings.backAutomation": "返回自動化",
    "settings.localConfiguration": "本地設定",
    "settings.controlPlane": "01 · 控制面",
    "settings.humanAgents": "02 · 面向人的 Agent",
    "settings.businessOutput": "03 · 業務產出",
    "settings.operatingDetails": "04 · 執行細節",
    "settings.globalFeishuAgents": "全域飛書 Agent",
    "settings.defaultReplyLanguage": "Agent 預設回覆語言",
    "settings.defaultReplyLanguageDescription": "當使用者沒有明確建立語言時使用。它與 Dashboard 介面語言彼此獨立。",
    "settings.accessControl": "存取控制",
    "settings.accessControlDescription": "群組按整個群組授權，私聊則需要逐一授權。系統會從每個已設定的 Agent 應用發現它加入的群組。",
    "settings.accessPerson": "使用者",
    "settings.accessChat": "群組聊天",
    "settings.selectPerson": "選擇使用者",
    "settings.selectChat": "選擇群組聊天",
    "settings.identityRoles": "此身分的存取權限",
    "settings.selectIdentityHelp": "選擇一個身分，然後編輯下方的三項存取權限。",
    "settings.canTalk": "可以與 Agent 對話",
    "settings.canMutate": "可以執行變更操作",
    "settings.canAdmin": "可以管理 Agent",
    "settings.accessSummary": "已設定身分",
    "settings.identityCount": "{{count}} 個身分記錄",
    "settings.pendingAccess": "待授權",
    "settings.rolesApplied": "項權限",
    "settings.agentCoreDescription": "這裡只編輯核心控制項。角色歸屬、安全邊界和 SOUL 檔案仍由 Agent 登錄表管理。",
    "settings.responsibility": "職責",
    "settings.legacyWarning": "舊版 allow 模式對本地 Agent 不安全。建議使用按 Agent 設定的 Access & Exposure，並將 default_policy 設為 deny。",
    "settings.recentPeople": "最近聯絡人",
    "settings.recentChats": "最近群組聊天",
    "settings.groupChats": "已授權群組",
    "settings.groupChatsDescription": "允許群組後，群內所有人都可以與 Agent 溝通，不需要逐一授權。",
    "settings.privateContacts": "私聊聯絡人",
    "settings.privateContactsDescription": "私聊按人員逐一授權。請確認顯示名稱和飛書 ID 後再開啟權限。",
    "settings.noGroupChats": "暫時沒有發現飛書群組。",
    "settings.noPrivateContacts": "暫時沒有發現私聊聯絡人。",
    "settings.agentMembership": "Agents：{{value}}",
    "settings.addMutationUser": "點擊新增為可變更使用者",
    "settings.allowChat": "點擊允許此聊天",
    "settings.noRecentPeople": "目前沒有最近的飛書聯絡人。先向 Dylan 或 Mark 傳送一則訊息，再重新整理設定。",
    "settings.generationLanguage": "生成語言",
    "settings.generationDescription": "控制 Mark 為此專案寫入飛書試算表的語言。mbpass 預設使用繁體中文。",
    "settings.afterGeneration": "修改語言或試算表後，請讓 Milchick/Mark 重新生成 Story，使新列使用選定的試算表。",
    "settings.executionDescription": "選擇提供者和模型 ID。Lumon 會透過所選提供者發送 API 請求，不會驗證模型是否可用。",
    "settings.modelCenter": "模型中心",
    "settings.modelCenterDescription": "在同一個地方配置所有對話 Agent 與自動化模型。",
    "settings.globalModelConfig": "全域 AI 設定",
    "settings.globalModelScope": "套用於四個對話 Agent 與三個自動化工作流。",
    "settings.inheritsGlobalModel": "繼承全域設定",
    "settings.conversationModels": "對話 Agent",
    "settings.conversationModelsDescription": "所有飛書 Agent 都使用上方的全域提供者與模型。",
    "settings.workflowModels": "自動化工作流",
    "settings.workflowModelsDescription": "自動掃描、自動交付和自動修復使用同一組全域提供者與模型。",
    "settings.workflowRuntimeLabel": "套用於所有 Agent 與工作流",
    "settings.openCodeHarness": "OpenCode Harness",
    "settings.openCodeHarnessDescription": "透過 OpenCode 呼叫已設定的模型，由 OpenCode 管理工作區工具與持久會話。",
    "settings.codexHarness": "Codex CLI",
    "settings.codexHarnessDescription": "Codex CLI 使用選定的本機 ChatGPT 帳號、完整主機與網路存取和持久會話。",
    "settings.openCodeRuntime": "Agent 執行環境",
    "settings.openCodeRuntimeDescription": "這裡顯示對話 Agent 與自動化工作流實際使用的 Harness 狀態。",
    "settings.harness": "Harness",
    "settings.runtimeModel": "模型",
    "settings.cliVersion": "CLI 版本",
    "settings.sessionMode": "會話",
    "settings.permissionProfile": "權限",
    "settings.harnessStatus": "Harness 就緒狀態",
    "settings.harnessStatusDescription": "Provider 可以使用原生工具與規範工作區；飛書信任門與審計仍由 Host 基礎設施負責。",
    "settings.harnessMode": "模式",
    "settings.harnessCapabilities": "能力",
    "settings.harnessSecurity": "安全邊界",
    "settings.harnessWarnings": "警告",
    "settings.harnessReady": "已就緒",
    "settings.harnessBlocked": "已阻斷",
    "settings.actionCatalog": "Action 清單",
    "settings.deepSeekCredential": "模型憑證",
    "settings.runtimeAccount": "Codex 帳號",
    "settings.reasoningEffort": "推理強度",
    "settings.deepSeekCredentialConfigured": "已設定於 ~/.lumon/.env.local",
    "settings.deepSeekCredentialMissing": "未設定（本機模型無需金鑰）",
    "settings.automationOutcome": "自動化結果",
    "settings.notificationsDescription": "控制 Scan 和 Delivery 是否向已設定的飛書 Webhook 發布卡片。Webhook URL 仍位於變數金鑰中。",
    "settings.storedWorkspace": "儲存在此工作區",
    "settings.storedWorkspaceOrLumon": "工作區 + Lumon 本機",
    "settings.storedLumon": "儲存在 Lumon 本機",
    "settings.availableKeys": "可用金鑰",
    "settings.availableKeysDescription": "顯示值以檢查，或直接輸入替換值。儲存時不會包含顯示引號。",
    "settings.revealReplacement": "顯示或輸入替換值",
    "settings.unsavedChanges": "有未儲存的變更",
    "settings.allSaved": "所有變更已儲存",
    "settings.deliveryPaused": "交付輪詢已暫停。",
    "settings.patchPaused": "Auto Patch 輪詢已暫停。",
    "settings.deliveryStatusHelp": "選擇所有可以啟動 Auto Delivery 的 Jira 狀態。Story 還必須處於 Business Ready、Technical Approved 且未在執行。",
    "settings.deliveryStatusNote": "選擇 To Do、Backlog、In Progress 或其他符合條件的 Jira 狀態。失敗時，Lumon 會將 Jira 卡片轉換到選定的 Block 狀態，並新增需要關注的評論。",
    "settings.patchStatusNote": "只捕獲 Task 和 Bug 卡片。阻塞卡片會在收到新的外部 Jira 評論後重試。",
    "settings.scanDefaultDescription": "尚未設定週期性掃描。",
    "settings.direct": "直接推送",
    "settings.merge": "合併",
    "settings.pullRequest": "PR",
    "settings.openPullRequest": "開啟 Pull Request",
    "settings.mergeAfterPullRequest": "在 Pull Request 後合併",
    "settings.pushDirectly": "直接推送到 main 分支",
    "settings.feishuNotifications": "飛書通知",
    "settings.allowedChatIds": "允許的群組聊天 ID",
    "settings.allowedUserIds": "允許的使用者 ID",
    "settings.mutationUserIds": "可變更使用者 ID",
    "settings.adminUserIds": "管理員使用者 ID",
    "settings.allowedChatHelp": "將群組按整個群組加入白名單。私聊仍需逐一授權；在群組中仍必須 @提及。",
    "settings.allowedUserHelp": "為空表示所有使用者都可以詢問唯讀問題。",
    "settings.mutationUserHelp": "解決問題、更新排程和啟動交付時必需。為空時預設拒絕。",
    "settings.adminUserHelp": "管理員也可以執行變更操作。",
    "settings.appSecretRequired": "飛書客戶端登入必需。",
    "settings.keepSecret": "留空以保留目前金鑰",
    "settings.enterSecret": "輸入 App Secret",
    "settings.runtimeIdentityHelp": "執行環境身分由 Agent 登錄表管理。",
    "settings.workflowOwnershipHelp": "工作流歸屬由 Agent 登錄表管理。",
    "settings.publishDescription": "直接推送使用已設定的 Git 儲存庫憑證；PR 和合併使用 GitHub CLI。Auto Scan 保留 PR 審查閘門，不支援直接推送。",
    "settings.deploymentTracking": "部署狀態追蹤",
    "settings.deploymentTrackingDescription": "發布後追蹤已設定的 CI/CD 執行，只有部署真正完成後才回報結果。憑證保留在本機環境變數中。",
    "settings.deploymentProvider": "提供者",
    "settings.deploymentDisabled": "未啟用",
    "settings.jenkins": "Jenkins",
    "settings.githubActions": "GitHub Actions",
    "settings.pollInterval": "輪詢間隔（秒）",
    "settings.deploymentTimeout": "逾時（秒）",
    "settings.deploymentProviderHelp": "發布後要觀察哪個 CI/CD 系統的部署執行。",
    "settings.deploymentOwner": "追蹤負責人",
    "settings.deploymentOwnerValue": "Milchick · 工程營運經理",
    "settings.deploymentOwnerHelp": "Milchick 負責判斷後續歸屬：原始碼或交付失敗交給 Mark，Jira 修復交給 Irving，基礎設施或無法判斷的問題回報人工決策。",
    "settings.deploymentFailureHandling": "背景 worker 負責輪詢提供者；Milchick 接收最終證據並決定下一位負責人，不再把所有失敗硬編碼交給 Mark。",
    "settings.credentials": "憑證",
    "settings.configured": "已設定",
    "settings.notConfigured": "未設定",
    "settings.localGhLogin": "本機 gh 登入",
    "settings.jenkinsPipeline": "Jenkins 部署流水線",
    "settings.jenkinsPipelineHelp": "用於定位要觀察的 Jenkins 流水線。例如：folder/job-name。Lumon 不會用此欄位執行程式碼。",
    "settings.jenkinsCredentials": "請在變數金鑰中設定 JENKINS_URL 和 JENKINS_AUTH。值保留在工作區環境中，不會寫入 delivery.json。",
    "settings.githubCredentials": "GitHub Actions 使用工作區執行器的本機 gh 登入狀態。這裡不輸入也不儲存 Token。",
    "settings.githubRepository": "GitHub 儲存庫",
    "settings.githubWorkflow": "Workflow（可選）",
    "label.deployment": "部署",
    "label.provider": "提供者",
    "label.lastChecked": "上次檢查",
    "action.openDeployment": "開啟部署",
    "editor.heading": "標題",
    "editor.editLink": "編輯連結 URL",
    "editor.linkUrl": "連結 URL",
    "editor.bold": "粗體",
    "editor.italic": "斜體",
    "editor.link": "連結 — Shift+點擊連結可定位游標，然後編輯",
    "editor.list": "清單",
    "editor.code": "程式碼",
    "prompt.original": "原始 Markdown",
    "prompt.preview": "預覽",
    "customModel.enter": "輸入自訂模型",
    "customModel.id": "模型 ID",
    "customModel.placeholder": "例如：deepseek-v4-flash",
    "customModel.copy": "Lumon 不會驗證模型是否可用，該值將在下一次執行時使用。",
    "customModel.edit": "編輯自訂模型",
    "customModel.option": "自訂模型 ID…",
    "customModel.badge": "自訂",
    "customModel.help": "使用所選提供者支援的模型 ID。",
    "status.completed": "已完成",
    "status.passed": "通過",
    "status.failed": "失敗",
    "status.skipped": "已略過",
    "status.open": "開放",
    "status.inProgress": "進行中",
    "status.awaitingDeploy": "等待部署",
    "status.running": "執行中",
    "status.active": "使用中",
    "status.notSet": "未設定",
    "status.notConfigured": "未設定",
    "status.resolved": "已解決",
    "status.reopened": "已重新開啟",
    "status.synced": "已同步",
    "status.ignored": "已忽略",
    "status.blocked": "已阻塞",
    "status.pending": "待處理",
    "status.prOpen": "PR 已開啟",
    "status.notStarted": "未開始",
    "status.devDone": "開發完成",
    "status.approved": "已核准",
    "status.ready": "就緒",
    "status.draft": "草稿",
    "status.done": "完成",
    "status.clarifying": "釐清中",
    "status.changed": "已變更",
    "label.business": "業務",
    "label.technical": "技術",
    "workflow.auto_scan.feature": "自動掃描",
    "workflow.auto_scan.mission": "發現反覆出現的工程風險，並整理成可供評審的證據。",
    "workflow.auto_scan.input": "程式碼儲存庫、掃描視窗、風險訊號",
    "workflow.auto_scan.output": "問題、嚴重程度、連結和後續問題",
    "workflow.auto_delivery.feature": "自動交付",
    "workflow.auto_delivery.mission": "推動已核准的 Story 完成實作、驗證和交付。",
    "workflow.auto_delivery.input": "就緒 Story、已核准方案、交付策略",
    "workflow.auto_delivery.output": "提交、檢查、PR/合併結果，或明確的阻塞原因",
    "workflow.auto_patch.feature": "自動修復",
    "workflow.auto_patch.mission": "接手 Jira Task/Bug，完成聚焦修復並安全交接。",
    "workflow.auto_patch.input": "符合條件的 Jira 卡片、儲存庫邊界",
    "workflow.auto_patch.output": "修復證據、驗證結果和 PR/直接推送結果",
    "workflow.manager.feature": "Manager",
    "workflow.manager.mission": "釐清意圖、建立合適的工作項目，並協調三個能力負責人。",
    "workflow.manager.input": "業務請求、待決策事項、Loop 狀態",
    "workflow.manager.output": "一個問題、一張工作卡，或一項路由後的執行請求",
    "label.autoScan": "自動掃描",
    "label.autoDelivery": "自動交付",
    "label.autoPatch": "自動修復",
    "label.manager": "Manager",
    "label.entryPoint": "入口",
    "label.feishuEntry": "使用者 / 飛書入口",
    "label.managerLayer": "協調層",
    "label.capabilityOwners": "能力負責人",
    "label.role": "角色",
    "label.input": "輸入",
    "label.output": "輸出",
    "label.owns": "負責",
    "label.receives": "接收",
    "label.returns": "產出",
    "label.gateway": "閘道",
    "label.agentDefaultLanguage": "回覆語言",
    "label.agentsReady": "就緒 Agent",
    "label.workflowsActive": "執行中工作流",
    "label.questionsWaiting": "待回答問題",
    "label.agentRoles": "Agent 角色",
    "label.recordedTurns": "已記錄對話",
    "label.processedQuestions": "已處理問題",
    "label.averageDuration": "平均耗時",
    "label.needsAttention": "需要關注",
    "label.rolesSeen": "涉及角色",
    "label.businessReadyCapabilities": "三個真人負責的能力",
    "label.conversationClear": "對話清晰",
    "label.unanswered": "{{count}} 個未回答",
    "label.sharedRuntime": "{{count}} 個角色 · 共用執行時",
    "label.currentStory": "目前 Story",
    "label.status": "狀態",
    "label.elapsed": "耗時",
    "label.finished": "結束時間",
    "label.jiraCard": "Jira 卡片",
    "label.branch": "分支",
    "label.repositories": "程式碼儲存庫",
    "label.started": "開始時間",
    "label.issues": "問題",
    "label.duration": "時長",
    "label.artifacts": "產物",
    "label.story": "Story",
    "label.pullRequests": "Pull Request",
    "label.checks": "檢查",
    "label.operation": "操作",
    "label.finishedAt": "結束時間",
    "label.log": "日誌",
    "label.summary": "摘要",
    "label.jira": "Jira",
    "label.trace": "Trace",
    "label.repository": "程式碼儲存庫",
    "label.localCommit": "本地提交",
    "label.roleId": "角色 ID",
    "label.workflow": "工作流",
    "label.prompt": "提示詞",
    "label.conversation": "對話",
    "label.typingReaction": "輸入回饋",
    "label.lookbackDays": "回溯天數",
    "label.cron": "五欄位 Cron",
    "label.intervalMinutes": "間隔（分鐘）",
    "label.eligibleStatuses": "符合條件的 Jira 狀態",
    "label.moveStarted": "開始時流轉到",
    "label.moveCompleted": "完成時流轉到",
    "label.moveFailed": "失敗時流轉到",
    "label.moveBlocked": "阻塞時流轉到",
    "label.outputLanguage": "輸出語言",
    "label.languageGeneration": "生成語言",
    "label.spreadsheetTab": "試算表分頁名稱",
    "label.spreadsheetToken": "試算表 Token / URL",
    "label.cursorModel": "執行模型",
    "label.modelProvider": "模型提供者",
    "label.apiBaseUrl": "API 基礎 URL",
    "label.apiKeyEnv": "API Key 環境變數",
    "label.softTimeout": "軟逾時（秒）",
    "label.hardTimeout": "硬逾時（秒）",
    "label.maxJobs": "最大並行工作數",
    "label.soulVersion": "SOUL 版本",
    "label.feishuAppId": "飛書 App ID",
    "label.feishuAppSecret": "飛書 App Secret",
    "label.completed": "已完成",
    "label.openFindings": "開放問題",
    "label.successfulScan": "成功掃描 · 7 天",
    "label.failed7d": "失敗 · 7 天",
    "label.lookbackWindow": "回溯視窗",
    "label.conversationAndActions": "對話和操作均可用",
    "label.conversationPaused": "對話已在設定中暫停",
    "label.credentialsRequired": "需要設定憑證",
    "label.requestResult": "請求 + 結果",
    "label.resultCaptured": "已記錄結果 · 請求來自未記錄轉錄的舊版本",
    "label.traceOnly": "僅 Trace",
    "label.executionTrail": "執行軌跡",
    "label.debugDetails": "除錯詳情",
    "label.promptNotCaptured": "目前執行時沒有記錄原始提示詞。",
    "label.olderTrace": "這條舊 Trace 有結果，但當時的執行時沒有記錄收到的訊息。",
    "label.noFinalResponse": "沒有保留最終回應文字；如需更多證據，請開啟 Agent 日誌中的源 Trace。",
    "label.activityRetention": "這裡只顯示有邊界的本地請求/結果文字。Trace ID 和原始執行證據仍保存在本地 Agent 儲存中。",
    "label.high": "高",
    "label.medium": "中",
    "label.low": "低",
    "label.untitledFinding": "未命名問題",
    "label.unknownRepository": "未知程式碼儲存庫",
    "label.reasonOptional": "原因（可選）",
    "label.ignoreQuestion": "要將此問題標記為忽略嗎？",
    "label.ignorePlaceholder": "為什麼可以安全忽略？",
    "label.noSnippet": "此歷史問題沒有記錄程式碼片段。",
    "label.notRecorded": "未記錄。",
    "label.notStarted": "等待交付觸發",
    "label.running": "執行中",
    "label.pending": "待處理",
    "label.stopped": "已停止",
    "label.needsAttentionState": "需要關注",
    "label.startedAt": "開始於 {{value}}",
    "label.finishedAtValue": "結束於 {{value}}",
    "label.requested": "請求",
    "label.result": "結果",
    "label.noLog": "沒有記錄日誌內容。",
    "label.noSchedulerLog": "沒有記錄排程輸出。",
    "label.noSummary": "沒有記錄摘要。",
    "label.recentRawOutput": "最近的原始輸出",
    "label.close": "關閉",
    "label.checksPassed": "{{count}} 個通過",
    "label.checksFailed": "{{count}} 個失敗",
    "label.checksSkipped": "{{count}} 個略過",
    "label.verification": "驗證",
    "label.checksTitle": "檢查",
    "heading.managerOverview": "Manager 總覽",
    "heading.agentActivity": "Agent 活動",
    "heading.conversationRecords": "對話記錄",
    "heading.agentRoster": "Agent 陣容",
    "heading.agentTeam": "Agent 陣容與工作流",
    "heading.agentArchitecture": "Agent 架構",
    "heading.workflowControl": "工作流控制",
    "heading.questionsWaiting": "等待你的問題",
    "heading.scanHistory": "掃描歷史",
    "heading.trackedFindings": "追蹤中的問題",
    "heading.currentProgress": "目前進度",
    "heading.deliveryHistory": "交付歷史",
    "heading.schedulerActivity": "排程活動",
    "heading.patchHistory": "修復歷史",
    "heading.stories": "Stories",
    "heading.workspaceSettings": "工作區設定",
    "heading.agentRoles": "Agent 角色",
    "heading.automationSchedules": "自動化排程",
    "heading.executionModels": "執行模型",
    "heading.publishPolicy": "發布策略",
    "heading.notifications": "通知",
    "heading.variableKeys": "變數金鑰",
    "heading.testCases": "測試案例",
    "heading.workflow": "{{feature}} 工作流",
    "action.openSettings": "開啟設定",
    "action.configureAgent": "設定 Agent",
    "action.manageCapture": "管理記錄",
    "action.viewActivity": "查看活動",
    "action.inspect": "查看 {{feature}}",
    "action.startScan": "開始掃描",
    "action.runCycle": "執行一輪",
    "action.viewRawLog": "查看原始日誌",
    "action.openLog": "開啟失敗日誌",
    "action.markIgnored": "標記為忽略",
    "action.viewDetail": "查看詳情",
    "action.hideDetail": "隱藏詳情",
    "action.pullRequest": "Pull Request",
    "action.startDelivery": "開始交付",
    "action.saveChanges": "儲存變更",
    "action.savePrompt": "儲存提示詞",
    "action.searchStories": "搜尋 Story",
    "action.filterStories": "篩選 Story",
    "action.showingReadyStories": "正在顯示業務就緒的 Story",
    "action.filterReadyStories": "篩選業務就緒的 Story",
    "action.exitFullscreen": "退出全螢幕",
    "action.viewFullscreen": "查看全螢幕",
    "action.start": "開始",
    "action.save": "儲存",
    "action.runScan": "開始掃描嗎？",
    "action.confirmScan": "確認開始掃描",
    "action.scanBody": "這將為 {{project}} 啟動自動掃描。",
    "action.scanConfirmBody": "確定現在為 {{project}} 啟動掃描嗎？掃描 Agent 將針對已設定的程式碼儲存庫執行。",
  },
};

let currentDashboardLocale: Locale = "en";
const DashboardI18nContext = createContext<{ locale: Locale; setLocale: (locale: Locale) => void; t: Translate } | null>(null);

function interpolate(value: string, variables: Record<string, unknown> = {}) {
  return value.replace(/{{(\w+)}}/g, (_, key) => String(variables[key] ?? ""));
}

function translateKey(locale: Locale, key: string, variables?: Record<string, unknown>) {
  return interpolate(translations[locale][key] ?? translations.en[key] ?? key, variables);
}

function useI18n() {
  const context = useContext(DashboardI18nContext);
  if (!context) throw new Error("DashboardI18nContext is missing");
  return context;
}

function DashboardI18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const stored = window.localStorage.getItem(localeStorageKey) || window.localStorage.getItem(legacyLocaleStorageKey);
    return localeOptions.some((option) => option.value === stored) ? stored as Locale : "en";
  });
  currentDashboardLocale = locale;
  const setLocale = (next: Locale) => { currentDashboardLocale = next; setLocaleState(next); window.localStorage.setItem(localeStorageKey, next); };
  const t = useCallback<Translate>((key, variables) => translateKey(locale, key, variables), [locale]);
  useEffect(() => { document.documentElement.lang = locale === "zh-Hans" ? "zh-CN" : locale === "zh-Hant" ? "zh-TW" : "en"; }, [locale]);
  return <DashboardI18nContext.Provider value={{ locale, setLocale, t }}>{children}</DashboardI18nContext.Provider>;
}

declare global {
  interface Window { DASHBOARD_DATA?: DashboardData }
}

interface AgentSettings {
  id: string;
  display_name: string;
  title: string;
  role: string;
  workflow: string;
  conversation_enabled: boolean;
  mode: string;
  provider: string;
  base_url?: string;
  api_key_env?: string;
  model_configured?: boolean;
  model: string;
  soft_timeout_seconds: number;
  hard_timeout_seconds: number;
  reaction_enabled: boolean;
  max_concurrent_jobs: number;
  soul_version: string;
  soul: string;
  soul_source: string;
  soul_override_path: string;
  app_id?: string;
  app_id_masked?: string;
  app_secret?: string;
  app_secret_configured?: boolean;
  app_secret_masked?: string;
  credentials_path?: string;
  security?: {
    filesystem?: string;
    mutations?: string;
    network?: string;
    sandbox?: string;
    secrets?: string;
    runner?: string;
    host_visibility?: string;
    workspace_isolation_v2?: boolean;
    agent_security_mode?: string;
    exposure_mode?: string;
    dm_only?: boolean;
    host_read?: string;
    default_policy?: string;
    policy_source?: string;
    actions?: string[];
  };
}

interface AgentsAccessSettings {
  default_policy?: string;
  owners?: string[];
  admins?: string[];
  allowed_chat_ids?: string[];
  allowed_user_ids?: string[];
  mutation_allowed_user_ids?: string[];
  admin_user_ids?: string[];
  legacy_warning?: boolean;
}

interface FeishuIdentityItem {
  id?: string;
  name?: string;
  kind?: string;
  chat_mode?: string;
  context_type?: string;
  union_id?: string;
  pending?: boolean;
  agents?: string[];
}

interface TestCaseSettings {
  project?: string;
  language?: string;
  table_name?: string;
  view_strategy?: string;
  base_app_token_env?: string;
  base_app_token_configured?: boolean;
  base_app_token_masked?: string;
}

interface AgentsSettingsPayload {
  enabled?: boolean;
  home?: string;
  config_path?: string;
  conversation?: { version?: string; default_language?: string };
  access?: AgentsAccessSettings;
  recent_feishu?: {
    user_ids?: string[];
    chat_ids?: string[];
    direct_chat_ids?: string[];
    private_user_ids?: string[];
    group_chat_ids?: string[];
    users?: FeishuIdentityItem[];
    chats?: FeishuIdentityItem[];
    private_users?: FeishuIdentityItem[];
    group_chats?: FeishuIdentityItem[];
    names?: Record<string, string>;
  };
  pending_questions?: Array<{ question_id?: string; agent_id?: string; action?: string; question?: string; missing?: string[]; created_at?: string; expires_at?: string }>;
  agents?: AgentSettings[];
  test_case?: TestCaseSettings;
}

interface DashboardData extends RecordValue {
  activity?: { available?: boolean; detail?: string; count?: number; total?: number; items?: RecordValue[] };
  interactive?: {
    enabled?: boolean;
    project?: string;
    projects?: Array<{ name: string; slug: string }>;
    prompts?: Array<{ mode: "scan" | "delivery" | "patch"; path: string }>;
    schedules?: { scan?: RecordValue | null; delivery?: RecordValue | null; patch?: RecordValue | null };
    workspace?: RecordValue;
    agents?: AgentsSettingsPayload;
  };
  delivery?: { current?: RecordValue; runs?: RecordValue[]; available_stories?: RecordValue[]; scheduler_activity?: RecordValue[]; scheduler_log_available?: boolean; config?: RecordValue };
  patch?: { current?: RecordValue; runs?: RecordValue[]; scheduler_activity?: RecordValue[]; scheduler_log_available?: boolean; config?: RecordValue };
}

const tabItems: Array<{ id: Tab; labelKey: string; icon: typeof ScanSearch }> = [
  { id: "overview", labelKey: "nav.overview", icon: LayoutDashboard },
  { id: "activity", labelKey: "nav.activity", icon: Activity },
  { id: "scan", labelKey: "nav.scan", icon: ScanSearch },
  { id: "delivery", labelKey: "nav.delivery", icon: Truck },
  { id: "patch", labelKey: "nav.patch", icon: Code2 },
  { id: "observatory", labelKey: "nav.observatory", icon: Eye },
  { id: "repositories", labelKey: "nav.repositories", icon: FolderGit2 },
  { id: "prompts", labelKey: "nav.prompts", icon: Workflow },
  { id: "settings", labelKey: "nav.settings", icon: Settings2 }
];

const tabContext: Record<Tab, { titleKey: string; descriptionKey: string }> = {
  overview: { titleKey: "context.overview.title", descriptionKey: "context.overview.description" },
  activity: { titleKey: "context.activity.title", descriptionKey: "context.activity.description" },
  scan: { titleKey: "context.scan.title", descriptionKey: "context.scan.description" },
  delivery: { titleKey: "context.delivery.title", descriptionKey: "context.delivery.description" },
  patch: { titleKey: "context.patch.title", descriptionKey: "context.patch.description" },
  observatory: { titleKey: "context.observatory.title", descriptionKey: "context.observatory.description" },
  repositories: { titleKey: "context.repositories.title", descriptionKey: "context.repositories.description" },
  prompts: { titleKey: "context.prompts.title", descriptionKey: "context.prompts.description" },
  settings: { titleKey: "context.settings.title", descriptionKey: "context.settings.description" }
};

const workflowProfiles = [
  {
    workflow: "auto_scan",
    tab: "scan" as Tab,
    feature: "Auto Scan",
    agent: "Dylan",
    mission: "Find recurring engineering risk and turn it into review-ready evidence.",
    input: "Repositories, scan window, risk signals",
    output: "Findings, severity, links, and next questions",
  },
  {
    workflow: "auto_delivery",
    tab: "delivery" as Tab,
    feature: "Auto Delivery",
    agent: "Mark",
    mission: "Move an approved Story through implementation, verification, and delivery.",
    input: "Ready Story, approved plan, delivery policy",
    output: "Commits, checks, PR/merge result, or a clear blocker",
  },
  {
    workflow: "auto_patch",
    tab: "patch" as Tab,
    feature: "Auto Patch",
    agent: "Irving",
    mission: "Pick up Jira Task/Bug work, apply a focused fix, and hand it off safely.",
    input: "Eligible Jira card, repository guardrails",
    output: "Patch evidence, verification, and PR/direct-push result",
  },
];

const managerProfile = {
  workflow: "manager",
  feature: "Manager",
  agent: "Milchick",
  mission: "Clarify intent, create the right work item, and coordinate the three capability owners.",
  input: "Business request, missing decisions, loop state",
  output: "A question, a work card, or a routed execution request",
};

function workflowProfile(workflow: string) {
  return workflowProfiles.find((profile) => profile.workflow === workflow) || (workflow === "manager" ? managerProfile : null);
}

const agentAvatarSources: Record<string, string> = {
  dylan: "assets/avatars/dylan.png",
  mark: "assets/avatars/mark.png",
  irving: "assets/avatars/irving.png",
  milchick: "assets/avatars/milchick.png",
};

const agentAvatarByWorkflow: Record<string, string> = {
  auto_scan: "dylan",
  auto_delivery: "mark",
  auto_patch: "irving",
  manager: "milchick",
};

function AgentAvatar({ agentId, displayName, size }: { agentId?: unknown; displayName?: unknown; size: "card" | "guide" | "record" }) {
  const id = String(agentId || "").trim().toLowerCase();
  const src = agentAvatarSources[id];
  if (src) return <img className={`agent-avatar agent-avatar-${size}`} src={src} alt="" aria-hidden="true" />;
  const initial = String(displayName || agentId || "A").trim().slice(0, 1).toUpperCase();
  return <span className={`activity-avatar activity-avatar-${id || "agent"}`} aria-hidden="true">{initial}</span>;
}

function localizedWorkflowProfile<T extends { workflow: string; feature: string; mission: string; input: string; output: string }>(profile: T, t: Translate) {
  return {
    ...profile,
    feature: t(`workflow.${profile.workflow}.feature`),
    mission: t(`workflow.${profile.workflow}.mission`),
    input: t(`workflow.${profile.workflow}.input`),
    output: t(`workflow.${profile.workflow}.output`),
  };
}

const cursorModelOptions = [
  { label: "Auto", value: "auto" },
  { label: "Composer 2.5", value: "composer-2.5" },
  { label: "Cursor Grok 4.5 Medium", value: "cursor-grok-4.5-medium" },
  { label: "Sonnet 4.5", value: "sonnet-4.5" },
  { label: "GPT-5.1 Codex", value: "gpt-5.1-codex" }
];
const opencodeModelOptions = [
  { label: "DeepSeek V4 Flash", value: "deepseek-v4-flash" }
];
const codexModelOptions = [
  { label: "GPT-5.6 Luna", value: "gpt-5.6-luna" }
];
const codexAccountEmail = "kuoyio0820@gmail.com";
const codexReasoningEffortOptions = [
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
  { label: "xHigh", value: "xhigh" },
  { label: "Max", value: "max" },
];
const customModelOption = "__custom__";

function text(value: unknown, fallback = "—") { return value === undefined || value === null || value === "" ? fallback : String(value); }
function modelValue(value: unknown, fallback = "cursor-grok-4.5-medium") {
  const normalized = String(value ?? "").trim();
  return normalized || fallback;
}
function workflowModelConfig(workspace: RecordValue, key: string, fallback = "cursor-grok-4.5-medium") {
  const configs = workspace.model_configs && typeof workspace.model_configs === "object" ? workspace.model_configs : {};
  const globalConfig = workspace.model_config && typeof workspace.model_config === "object" ? workspace.model_config : {};
  const legacyConfig = configs[key] && typeof configs[key] === "object" ? configs[key] : {};
  const config = globalConfig.provider || globalConfig.model ? globalConfig : legacyConfig;
  const rawProvider = String(config.provider || "cursor_cli").trim().toLowerCase();
  const provider = rawProvider === "deepseek" || rawProvider === "deepseek_api" || rawProvider === "opencode_deepseek" ? "opencode" : rawProvider === "codex_cli" || rawProvider === "codex-cli" ? "codex" : rawProvider === "cursor" || rawProvider === "cursor-cli" ? "cursor_cli" : rawProvider === "openai" || rawProvider === "openai-compatible" ? "openai_compatible" : rawProvider;
  const defaultModel = provider === "codex" ? "gpt-5.6-luna" : provider === "opencode" ? "deepseek-v4-flash" : provider === "openai_compatible" ? "gpt-4o-mini" : fallback;
  return {
    provider,
    model: modelValue(config.model || workspace.models?.[key], defaultModel),
    base_url: String(config.base_url || ""),
    api_key_env: String(config.api_key_env || ""),
    reasoning_effort: String(config.reasoning_effort || (provider === "codex" ? "xhigh" : "")),
    account_email: String(config.account_email || (provider === "codex" ? codexAccountEmail : "")),
  };
}
function trimmedModelValue(value: unknown) { return String(value ?? "").trim(); }
function when(value: unknown) {
  if (!value) return "—";
  const date = new Date(String(value));
  const locale = currentDashboardLocale === "zh-Hans" ? "zh-CN" : currentDashboardLocale === "zh-Hant" ? "zh-TW" : undefined;
  return Number.isNaN(date.valueOf()) ? String(value) : new Intl.DateTimeFormat(locale, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).format(date);
}
function elapsed(start?: string, end?: string) {
  if (!start || !end) return "—";
  const seconds = Math.round((new Date(end).valueOf() - new Date(start).valueOf()) / 1000);
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const minutes = Math.floor(seconds / 60);
  const remainder = String(seconds % 60).padStart(2, "0");
  return currentDashboardLocale === "en" ? `${minutes}m ${remainder}s` : `${minutes}${currentDashboardLocale === "zh-Hans" ? "分" : "分"}${remainder}${currentDashboardLocale === "zh-Hans" ? "秒" : "秒"}`;
}
function durationMs(value: unknown) {
  if (value === undefined || value === null || value === "") return "—";
  const milliseconds = Number(value);
  if (!Number.isFinite(milliseconds)) return "—";
  if (milliseconds < 1000) return currentDashboardLocale === "en" ? `${Math.round(milliseconds)}ms` : `${Math.round(milliseconds)}毫秒`;
  const seconds = Math.round(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainder = String(seconds % 60).padStart(2, "0");
  return currentDashboardLocale === "en" ? `${minutes}m ${remainder}s` : `${minutes}分${remainder}秒`;
}
function statusTone(value: unknown) {
  const normalized = String(value || "unknown").toLowerCase().replaceAll("_", " ");
  if (normalized === "open" || normalized === "reopened" || /(failed|blocked)/.test(normalized)) return "danger";
  if (/(completed|succeeded|clean|passed|resolved|synced|configured|included|available|approved|ready|done|pr open)/.test(normalized)) return "success";
  if (/(progress|running|active|partial|draft|not started|awaiting deployment)/.test(normalized)) return "info";
  return "neutral";
}
function titleStatus(value: unknown) {
  const raw = text(value, "unknown").toLowerCase().replaceAll("_", " ");
  const labels: Record<string, string> = {
    "completed with findings": "status.completed", completed: "status.completed", clean: "status.completed",
    passed: "status.passed", failed: "status.failed", skipped: "status.skipped", open: "status.open",
    "in progress": "status.inProgress", "awaiting deploy": "status.awaitingDeploy", running: "status.running", configured: "status.active",
    "not configured": "status.notConfigured", setup: "status.notConfigured", resolved: "status.resolved", reopened: "status.reopened", synced: "status.synced",
    ignored: "status.ignored", blocked: "status.blocked", pending: "status.pending", active: "status.active",
    "pr open": "status.prOpen", "not started": "status.notStarted", "dev done": "status.devDone",
    approved: "status.approved", ready: "status.ready", draft: "status.draft", done: "status.done", clarifying: "status.clarifying", changed: "status.changed"
  };
  return labels[raw] ? translateKey(currentDashboardLocale, labels[raw]) : raw.replace(/\b\w/g, (letter) => letter.toUpperCase());
}
async function request(path: string, project: string, init: RequestInit & { json?: RecordValue } = {}) {
  const url = new URL(path, window.location.origin);
  if (!init.method || init.method === "GET") url.searchParams.set("project", project);
  const headers = new Headers(init.headers);
  let body = init.body;
  if (init.json) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify({ ...init.json, project });
  }
  const response = await fetch(url, { ...init, headers, body });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}

function Badge({ value }: { value: unknown }) {
  return <span className={`badge ${statusTone(value)}`}>{titleStatus(value)}</span>;
}

function StoryStatusMeta({ business, technical, compact = false }: { business: string; technical: string; compact?: boolean }) {
  const { t } = useI18n();
  return <div className={`observatory-meta${compact ? " compact" : ""}`}>
    <span className="observatory-meta-item"><em>{t("label.business")}</em><Badge value={business || "draft"} /></span>
    <span className="observatory-meta-item"><em>{t("label.technical")}</em><Badge value={technical || "draft"} /></span>
  </div>;
}

function storyDateLabel(value: string) {
  const day = String(value || "").trim().slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : "";
}

function StoryListMeta({ date, assignee }: { date: string; assignee: string }) {
  const day = storyDateLabel(date);
  const person = String(assignee || "").trim();
  if (!day && !person) return null;
  return <div className="observatory-story-meta">
    {day ? <span className="observatory-story-meta-item"><Calendar size={11} aria-hidden="true" />{day}</span> : null}
    {person ? <span className="observatory-story-meta-item"><User size={11} aria-hidden="true" />{person}</span> : null}
  </div>;
}

function StoryListStatus({ business, technical }: { business: string; technical: string }) {
  const { t } = useI18n();
  const businessTone = statusTone(business || "draft");
  const technicalTone = statusTone(technical || "draft");
  const icon = (tone: string) => tone === "success" ? <i className="observatory-status-dot" /> : <CircleDot size={11} />;
  return <div className="observatory-story-status">
    <span className={`observatory-story-status-item ${businessTone}`}>
      {icon(businessTone)}
      {t("label.business")} {titleStatus(business || "draft")}
    </span>
    <span className={`observatory-story-status-item ${technicalTone}`}>
      {icon(technicalTone)}
      {t("label.technical")} {titleStatus(technical || "draft")}
    </span>
  </div>;
}

function FullscreenMedia({ label, onClose, children }: { label: string; onClose: () => void; children: React.ReactNode }) {
  const { t } = useI18n();
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{ x: number; y: number } | null>(null);
  const clampZoom = (value: number) => Math.min(FULLSCREEN_ZOOM_MAX, Math.max(FULLSCREEN_ZOOM_MIN, Number(value.toFixed(2))));
  const resetView = () => { setZoom(1); setPan({ x: 0, y: 0 }); };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "+" || event.key === "=") setZoom((value) => clampZoom(value + FULLSCREEN_ZOOM_STEP));
      if (event.key === "-" || event.key === "_") setZoom((value) => clampZoom(value - FULLSCREEN_ZOOM_STEP));
      if (event.key === "0") resetView();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    dragRef.current = { x: event.clientX, y: event.clientY };
    setDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const origin = dragRef.current;
    if (!origin) return;
    const dx = event.clientX - origin.x;
    const dy = event.clientY - origin.y;
    dragRef.current = { x: event.clientX, y: event.clientY };
    setPan((value) => ({ x: value.x + dx, y: value.y + dy }));
  };
  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    dragRef.current = null;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  };
  return <div className="media-fullscreen" role="dialog" aria-modal="true" aria-label={label}>
    <header>
      <span>{label}</span>
      <div className="media-fullscreen-actions">
        <button type="button" className="button secondary" title={t("common.zoomOut")} aria-label={t("common.zoomOut")} onClick={() => setZoom((value) => clampZoom(value - FULLSCREEN_ZOOM_STEP))}><ZoomOut size={14} /></button>
        <button type="button" className="button secondary media-fullscreen-zoom-label" title={t("common.resetView")} aria-label={t("common.resetView")} onClick={resetView}>{Math.round(zoom * 100)}%</button>
        <button type="button" className="button secondary" title={t("common.zoomIn")} aria-label={t("common.zoomIn")} onClick={() => setZoom((value) => clampZoom(value + FULLSCREEN_ZOOM_STEP))}><ZoomIn size={14} /></button>
        <button type="button" className="button secondary" onClick={onClose} aria-label={t("common.closeFullscreen")}><X size={14} /></button>
      </div>
    </header>
    <div
      className={`media-fullscreen-stage${dragging ? " is-dragging" : ""}`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <div className="media-fullscreen-canvas" style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}>{children}</div>
    </div>
  </div>;
}

async function renderMermaidSvg(chart: string) {
  const cached = mermaidSvgCache.get(chart);
  if (cached) return cached;
  const id = `mmd-${++mermaidPaintSeq}`;
  const { svg } = await mermaid.render(id, chart);
  mermaidSvgCache.set(chart, svg);
  return svg;
}

const MermaidBlock = memo(function MermaidBlock({ chart }: { chart: string }) {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);
  const [fullscreen, setFullscreen] = useState(false);
  useEffect(() => {
    const host = ref.current;
    if (!host) return;
    const cached = mermaidSvgCache.get(chart);
    if (cached) {
      host.innerHTML = cached;
      return;
    }
    let cancelled = false;
    void renderMermaidSvg(chart).then((svg) => {
      if (!cancelled && ref.current) ref.current.innerHTML = svg;
    }).catch((err) => {
      if (!cancelled && ref.current) ref.current.innerHTML = `<pre class="mermaid-error">${String(err)}</pre>`;
    });
    return () => { cancelled = true; };
  }, [chart]);
  return <>
    <div className="mermaid-wrap">
      <button type="button" className="mermaid-fullscreen-btn" title={t("common.showFullscreen")} aria-label={t("common.showFullscreen")} onClick={() => setFullscreen(true)}><Maximize2 size={14} /></button>
      <div className="mermaid-block" ref={ref} />
    </div>
    {fullscreen && <FullscreenMedia label={t("common.diagram")} onClose={() => setFullscreen(false)}>
      <div className="mermaid-block mermaid-block-fullscreen" dangerouslySetInnerHTML={{ __html: mermaidSvgCache.get(chart) || ref.current?.innerHTML || "" }} />
    </FullscreenMedia>}
  </>;
});

function MarkdownImage({ src, alt }: { src?: string; alt?: string }) {
  const { t } = useI18n();
  const [fullscreen, setFullscreen] = useState(false);
  if (!src) return null;
  return <>
    <span className="markdown-image-wrap">
      <button type="button" className="mermaid-fullscreen-btn" title={t("common.showFullscreen")} aria-label={t("common.showFullscreen")} onClick={() => setFullscreen(true)}><Maximize2 size={14} /></button>
      <img src={src} alt={alt || ""} />
    </span>
    {fullscreen && <FullscreenMedia label={alt || t("common.image")} onClose={() => setFullscreen(false)}>
      <img src={src} alt={alt || ""} />
    </FullscreenMedia>}
  </>;
}

function CodeFence({ className, children }: { className?: string; children?: React.ReactNode }) {
  const { t } = useI18n();
  const value = String(children).replace(/\n$/, "");
  const [copied, setCopied] = useState(false);
  if (/language-mermaid/.test(className || "")) return <MermaidBlock chart={value} />;
  if (!value.includes("\n") && !className) return <code className={className}>{children}</code>;
  const lang = (className || "").replace(/^language-/, "") || "code";
  return <div className="md-code-block">
    <div className="md-code-toolbar">
      <span className="md-code-lang">{lang}</span>
      <button
        type="button"
        className="md-code-copy"
        title={t("common.copyCode")}
        aria-label={t("common.copyCode")}
        data-copied={copied ? "true" : undefined}
        onClick={() => {
          void navigator.clipboard.writeText(value).then(() => {
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1200);
          });
        }}
      ><Copy size={14} /></button>
    </div>
    <pre><code className={className}>{value}</code></pre>
  </div>;
}

const markdownComponents = {
  a({ href, children }: { href?: string; children?: React.ReactNode }) {
    return <a href={href} target="_blank" rel="noreferrer noopener">{children}</a>;
  },
  img({ src, alt }: { src?: string; alt?: string }) {
    return <MarkdownImage src={src} alt={alt} />;
  },
  code({ className, children }: { className?: string; children?: React.ReactNode }) {
    return <CodeFence className={className}>{children}</CodeFence>;
  },
};

function MarkdownBody({ content }: { content: string }) {
  return <div className="markdown-content">
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{content}</ReactMarkdown>
  </div>;
}

function splitFrontmatter(markdown: string) {
  const match = markdown.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) return { frontmatter: "", body: markdown };
  return { frontmatter: match[1], body: match[2] };
}

function joinFrontmatter(frontmatter: string, body: string) {
  if (!frontmatter) return body;
  return `---\n${frontmatter}\n---\n${body.startsWith("\n") ? body : `\n${body}`}`;
}

const COPY_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16V4a2 2 0 0 1 2-2h12"/></svg>`;

function decorateCodeBlocks(root: HTMLElement) {
  for (const pre of Array.from(root.querySelectorAll("pre"))) {
    if (pre.closest(".md-code-block, .mermaid-wrap") || pre.classList.contains("mermaid-error")) continue;
    const code = pre.querySelector("code");
    const lang = ((code?.className || "").match(/language-([\w-]+)/) || [])[1] || "code";
    const wrap = document.createElement("div");
    wrap.className = "md-code-block";
    const toolbar = document.createElement("div");
    toolbar.className = "md-code-toolbar";
    toolbar.contentEditable = "false";
    const langEl = document.createElement("span");
    langEl.className = "md-code-lang";
    langEl.textContent = lang;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "md-code-copy";
    button.title = translateKey(currentDashboardLocale, "common.copyCode");
    button.setAttribute("aria-label", translateKey(currentDashboardLocale, "common.copyCode"));
    button.innerHTML = COPY_ICON;
    button.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      const text = code?.textContent || pre.textContent || "";
      void navigator.clipboard.writeText(text).then(() => {
        button.dataset.copied = "true";
        window.setTimeout(() => { delete button.dataset.copied; }, 1200);
      });
    };
    toolbar.append(langEl, button);
    pre.replaceWith(wrap);
    wrap.append(toolbar, pre);
  }
}

function markdownToEditableHtml(markdown: string) {
  const rewritten = markdown.replace(/```mermaid\r?\n([\s\S]*?)```/g, (_, chart: string) => {
    const id = `mm-${++mermaidPaintSeq}`;
    mermaidChartById.set(id, chart.trim());
    const label = translateKey(currentDashboardLocale, "common.showFullscreen");
    return `\n\n<div class="mermaid-wrap" contenteditable="false" data-mm-id="${id}"><button type="button" class="mermaid-fullscreen-btn" data-mm-fullscreen title="${label}" aria-label="${label}"></button><div class="mermaid-block" data-mm-host></div></div>\n\n`;
  });
  return String(marked.parse(rewritten, { async: false }));
}

function createObservatoryTurndown() {
  const turndown = new TurndownService({ headingStyle: "atx", codeBlockStyle: "fenced", bulletListMarker: "-" });
  turndown.addRule("fullscreenBtn", {
    filter: (node) => node instanceof HTMLElement && node.classList.contains("mermaid-fullscreen-btn"),
    replacement: () => "",
  });
  turndown.addRule("codeToolbar", {
    filter: (node) => node instanceof HTMLElement && node.classList.contains("md-code-toolbar"),
    replacement: () => "",
  });
  turndown.addRule("codeBlockShell", {
    filter: (node) => node instanceof HTMLElement && node.classList.contains("md-code-block"),
    replacement: (_content, node) => {
      const code = (node as HTMLElement).querySelector("code");
      const pre = (node as HTMLElement).querySelector("pre");
      const lang = ((code?.className || "").match(/language-([\w-]+)/) || [])[1] || "";
      const text = (code?.textContent || pre?.textContent || "").replace(/\n$/, "");
      return `\n\n\`\`\`${lang}\n${text}\n\`\`\`\n\n`;
    },
  });
  turndown.addRule("mermaidIsland", {
    filter: (node) => node instanceof HTMLElement && node.classList.contains("mermaid-wrap") && Boolean(node.getAttribute("data-mm-id")),
    replacement: (_content, node) => {
      const id = (node as HTMLElement).getAttribute("data-mm-id") || "";
      const chart = mermaidChartById.get(id) || "";
      return `\n\n\`\`\`mermaid\n${chart}\n\`\`\`\n\n`;
    },
  });
  turndown.addRule("imageWrap", {
    filter: (node) => node instanceof HTMLElement && node.classList.contains("markdown-image-wrap"),
    replacement: (_content, node) => {
      const img = (node as HTMLElement).querySelector("img");
      if (!img) return "";
      return `![${img.getAttribute("alt") || ""}](${img.getAttribute("src") || ""})`;
    },
  });
  return turndown;
}

async function hydrateMermaidHosts(root: HTMLElement) {
  const hosts = Array.from(root.querySelectorAll<HTMLElement>("[data-mm-host]"));
  await Promise.all(hosts.map(async (host) => {
    const wrap = host.closest<HTMLElement>(".mermaid-wrap");
    const id = wrap?.getAttribute("data-mm-id") || "";
    const chart = mermaidChartById.get(id);
    if (!chart) return;
    try {
      host.innerHTML = await renderMermaidSvg(chart);
    } catch (err) {
      host.innerHTML = `<pre class="mermaid-error">${String(err)}</pre>`;
    }
  }));
}

function shouldCommitEditorSync(edited: boolean, nextBody: string, currentBody: string) {
  return edited && nextBody !== currentBody;
}

function linkElementFromSelection(root: HTMLElement | null): HTMLAnchorElement | null {
  const selection = window.getSelection();
  if (!root || !selection?.anchorNode) return null;
  const node = selection.anchorNode;
  const element = node instanceof Element ? node : node.parentElement;
  const anchor = element?.closest("a");
  if (!(anchor instanceof HTMLAnchorElement) || !root.contains(anchor)) return null;
  return anchor;
}

function shouldOpenMarkdownLink(event: { shiftKey?: boolean; metaKey?: boolean; altKey?: boolean; button?: number }) {
  return !event.shiftKey && !event.metaKey && !event.altKey && (event.button === undefined || event.button === 0);
}

function ObservatoryDocEditor({ value, onChange }: { value: string; onChange: (next: string) => void }) {
  const { t } = useI18n();
  const { frontmatter, body } = splitFrontmatter(value);
  const editorRef = useRef<HTMLDivElement>(null);
  const focusedRef = useRef(false);
  const editedRef = useRef(false);
  const bodyRef = useRef(body);
  const turndownRef = useRef(createObservatoryTurndown());
  const [fullscreen, setFullscreen] = useState<{ kind: "html" | "img"; value: string; alt?: string } | null>(null);
  const [docFullscreen, setDocFullscreen] = useState(false);
  bodyRef.current = body;
  const setBody = (nextBody: string) => onChange(joinFrontmatter(frontmatter, nextBody));
  const syncFromDom = () => {
    const root = editorRef.current;
    if (!root) return;
    const nextBody = turndownRef.current.turndown(root);
    if (!shouldCommitEditorSync(editedRef.current, nextBody, bodyRef.current)) return;
    setBody(nextBody);
  };
  const markAnchors = (root: HTMLElement) => {
    root.querySelectorAll("a[href]").forEach((anchor) => {
      anchor.setAttribute("target", "_blank");
      anchor.setAttribute("rel", "noreferrer noopener");
    });
  };
  const paint = useCallback(async (markdown: string) => {
    const root = editorRef.current;
    if (!root) return;
    editedRef.current = false;
    root.innerHTML = markdownToEditableHtml(markdown);
    decorateCodeBlocks(root);
    markAnchors(root);
    const maximizeIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/><path d="M9 21H3v-6"/></svg>`;
    root.querySelectorAll<HTMLButtonElement>("[data-mm-fullscreen]").forEach((button) => {
      button.innerHTML = maximizeIcon;
      button.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        const host = button.parentElement?.querySelector("[data-mm-host]");
        setFullscreen({ kind: "html", value: host?.innerHTML || "" });
      };
    });
    root.querySelectorAll("img").forEach((image) => {
      if (image.closest(".markdown-image-wrap")) return;
      const wrap = document.createElement("span");
      wrap.className = "markdown-image-wrap";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "mermaid-fullscreen-btn";
      button.title = t("common.showFullscreen");
      button.setAttribute("aria-label", t("common.showFullscreen"));
      button.innerHTML = maximizeIcon;
      const src = image.getAttribute("src") || "";
      const alt = image.getAttribute("alt") || "";
      button.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        setFullscreen({ kind: "img", value: src, alt });
      };
      image.replaceWith(wrap);
      wrap.append(button, image);
    });
    await hydrateMermaidHosts(root);
  }, [t]);
  useEffect(() => {
    if (focusedRef.current) return;
    void paint(body);
  }, [body, paint]);
  useEffect(() => {
    if (!docFullscreen) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setDocFullscreen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [docFullscreen]);
  const run = (command: string, commandValue?: string) => {
    editorRef.current?.focus();
    document.execCommand(command, false, commandValue);
    editedRef.current = true;
    syncFromDom();
    if (editorRef.current) markAnchors(editorRef.current);
  };
  const editOrCreateLink = () => {
    const root = editorRef.current;
    root?.focus();
    const existing = linkElementFromSelection(root);
    const current = existing?.getAttribute("href") || "https://";
    const href = window.prompt(existing ? t("editor.editLink") : t("editor.linkUrl"), current);
    if (href === null) return;
    const next = href.trim();
    if (existing) {
      if (!next) {
        run("unlink");
        return;
      }
      existing.setAttribute("href", next);
      existing.setAttribute("target", "_blank");
      existing.setAttribute("rel", "noreferrer noopener");
      editedRef.current = true;
      syncFromDom();
      return;
    }
    if (next) run("createLink", next);
  };
  return <div className={`observatory-doc${docFullscreen ? " observatory-doc-fullscreen" : ""}`}>
    <div className="observatory-toolbar" role="toolbar" aria-label={t("common.formattingTools")}>
      <button type="button" title={t("editor.heading")} onMouseDown={(event) => event.preventDefault()} onClick={() => run("formatBlock", "h2")}><Heading2 size={14} /></button>
      <button type="button" title={t("editor.bold")} onMouseDown={(event) => event.preventDefault()} onClick={() => run("bold")}><Bold size={14} /></button>
      <button type="button" title={t("editor.italic")} onMouseDown={(event) => event.preventDefault()} onClick={() => run("italic")}><Italic size={14} /></button>
      <button type="button" title={t("editor.link")} onMouseDown={(event) => event.preventDefault()} onClick={editOrCreateLink}><Link2 size={14} /></button>
      <button type="button" title={t("editor.list")} onMouseDown={(event) => event.preventDefault()} onClick={() => run("insertUnorderedList")}><List size={14} /></button>
      <button type="button" title={t("editor.code")} onMouseDown={(event) => event.preventDefault()} onClick={() => run("formatBlock", "pre")}><Code2 size={14} /></button>
    </div>
    <div className="observatory-doc-preview-wrap">
      <button
        type="button"
        className="observatory-doc-fullscreen-btn"
        title={docFullscreen ? t("common.closeFullscreen") : t("common.showFullscreen")}
        aria-label={docFullscreen ? t("common.closeFullscreen") : t("common.showFullscreen")}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => setDocFullscreen((value) => !value)}
      >{docFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}</button>
      <div
        ref={editorRef}
        className="observatory-doc-preview markdown-content"
        contentEditable
        suppressContentEditableWarning
        spellCheck={false}
        role="textbox"
        aria-multiline="true"
        aria-label={t("common.documentBody")}
        onFocus={() => { focusedRef.current = true; }}
        onBlur={() => { focusedRef.current = false; syncFromDom(); }}
        onInput={() => { editedRef.current = true; syncFromDom(); }}
        onClick={(event) => {
          const target = event.target as HTMLElement | null;
          if (!target || target.closest("button")) return;
          const anchor = target.closest("a[href]");
          if (!(anchor instanceof HTMLAnchorElement) || !editorRef.current?.contains(anchor)) return;
          if (!shouldOpenMarkdownLink(event)) return;
          event.preventDefault();
          event.stopPropagation();
          const href = anchor.getAttribute("href");
          if (href) window.open(href, "_blank", "noopener,noreferrer");
        }}
      />
    </div>
    {fullscreen && <FullscreenMedia label={fullscreen.kind === "img" ? (fullscreen.alt || t("common.image")) : t("common.diagram")} onClose={() => setFullscreen(null)}>
      {fullscreen.kind === "img"
        ? <img src={fullscreen.value} alt={fullscreen.alt || ""} />
        : <div className="mermaid-block mermaid-block-fullscreen" dangerouslySetInnerHTML={{ __html: fullscreen.value }} />}
    </FullscreenMedia>}
  </div>;
}

function IconButton({ label, children, onClick, danger = false, disabled = false, className = "" }: { label: string; children: React.ReactNode; onClick: () => void; danger?: boolean; disabled?: boolean; className?: string }) {
  return <button className={`icon-button ${danger ? "danger" : ""} ${className}`} title={label} aria-label={label} disabled={disabled} onClick={onClick}>{children}</button>;
}

function Panel({ title, action, children, className = "" }: { title: string; action?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><header className="panel-header"><h3>{title}</h3>{action}</header>{children}</section>;
}

function App() {
  const { locale, setLocale, t } = useI18n();
  const initialProject = new URLSearchParams(window.location.search).get("project") || window.DASHBOARD_DATA?.interactive?.project || "";
  const [project, setProject] = useState(initialProject);
  const [data, setData] = useState<DashboardData | null>(null);
  const pathTab = (tabItems.find((item) => `/${item.id}` === window.location.pathname)?.id || "overview") as Tab;
  const [activeTab, setActiveTab] = useState<Tab>(pathTab);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.localStorage.getItem("lumon-sidebar-collapsed") === "true" || window.localStorage.getItem("lumen-sidebar-collapsed") === "true");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [observatoryDirty, setObservatoryDirty] = useState(false);
  const [gitConflict, setGitConflict] = useState<RecordValue | null>(null);
  const loadSequence = useRef(0);
  const dataRef = useRef(false);
  const notify = useCallback<Notify>((message, tone = "info") => setNotice({ message, tone }), []);

  const load = async () => {
    const sequence = ++loadSequence.current;
    if (!dataRef.current) setLoading(true);
    try {
      const next = await request("/api/state", project);
      if (sequence !== loadSequence.current) return;
      dataRef.current = true;
      setData(next);
      const conflict = next.interactive?.workspace?.git_sync_conflict;
      setGitConflict(conflict && typeof conflict === "object" && ["repo", "branch", "remote_oid", "local_oid"].every((key) => String(conflict[key] || "").trim()) ? conflict : null);
      setLastUpdated(new Date());
      if (!project && next.interactive?.project) setProject(next.interactive.project);
      setError("");
    } catch (err) {
      if (sequence !== loadSequence.current) return;
      const staticData = window.DASHBOARD_DATA;
      if (staticData) {
        dataRef.current = true;
        setData(staticData);
        setError(t("common.staticReport"));
      }
      else setError(err instanceof Error ? err.message : t("common.unableLoadState"));
    } finally { if (sequence === loadSequence.current) setLoading(false); }
  };

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    let inflight = false;
    const tick = async () => {
      if (cancelled || inflight) return;
      inflight = true;
      try { await load(); }
      finally {
        inflight = false;
        if (!cancelled) timer = window.setTimeout(() => { void tick(); }, 5_000);
      }
    };
    void tick();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [project]);
  useEffect(() => { if (!notice) return; const id = window.setTimeout(() => setNotice(null), 3200); return () => window.clearTimeout(id); }, [notice]);
  useEffect(() => { window.localStorage.setItem("lumon-sidebar-collapsed", String(sidebarCollapsed)); }, [sidebarCollapsed]);
  useEffect(() => { const onPopState = () => setActiveTab((tabItems.find((item) => `/${item.id}` === window.location.pathname)?.id || "scan") as Tab); window.addEventListener("popstate", onPopState); return () => window.removeEventListener("popstate", onPopState); }, []);

  const confirmLeaveUnsaved = () => {
    if (settingsDirty && !window.confirm(t("common.unsavedSettings"))) return false;
    if (observatoryDirty && !window.confirm(t("common.unsavedObservatory"))) return false;
    return true;
  };
  const changeProject = (slug: string) => {
    if (slug !== project && !confirmLeaveUnsaved()) return;
    const url = new URL(window.location.href);
    url.searchParams.set("project", slug);
    window.history.replaceState({}, "", `${window.location.pathname}${url.search}`);
    setProject(slug);
    dataRef.current = false;
    setSettingsDirty(false);
    setObservatoryDirty(false);
  };
  const changeTab = (tab: Tab) => {
    if (tab !== activeTab && !confirmLeaveUnsaved()) return;
    const url = new URL(window.location.href);
    url.pathname = `/${tab}`;
    window.history.pushState({}, "", url);
    setActiveTab(tab);
    if (tab !== "settings") setSettingsDirty(false);
    if (tab !== "observatory") setObservatoryDirty(false);
  };
  const interact = async (path: string, json: RecordValue, message: string): Promise<boolean> => {
    try { await request(path, project, { method: "POST", json }); notify(message, "success"); void load(); return true; }
    catch (err) { notify(err instanceof Error ? err.message : t("common.requestFailed"), "error"); return false; }
  };
  const projects = data?.interactive?.projects || [];
  const tagline = data?.product?.tagline || "Engineering, made legible.";
  const context = tabContext[activeTab];

  return <main className={`dashboard-layout ${sidebarCollapsed ? "sidebar-is-collapsed" : ""}`}>
    <aside className="sidebar" aria-label={t("common.navigation")}>
      <div className="sidebar-brand">
        <img src="assets/lumon-mark.png" className="brand-mark" alt="Lumon" />
        <div className="sidebar-brand-copy"><strong>Lumon</strong><span>{tagline}</span></div>
      </div>
      <nav className="side-nav" aria-label={t("common.dashboardSections")}>{tabItems.map((item) => { const Icon = item.icon; const label = t(item.labelKey); return <button title={label} className={activeTab === item.id ? "active" : ""} onClick={() => changeTab(item.id)} key={item.id}><Icon size={17} /><span>{label}</span></button>; })}</nav>
      <div className="sidebar-foot">
        {!sidebarCollapsed && <img src="assets/inspire-group-logo.png" className="company-mark" alt="INSPIRE GROUP" />}
        <small>{sidebarCollapsed ? `V${lumonVersion}` : t("common.version", { value: lumonVersion })}</small>
      </div>
    </aside>
    <button type="button" className="icon-button sidebar-toggle" title={sidebarCollapsed ? t("common.expandNavigation") : t("common.collapseNavigation")} aria-label={sidebarCollapsed ? t("common.expandNavigation") : t("common.collapseNavigation")} onPointerDown={(event) => { event.preventDefault(); event.stopPropagation(); setSidebarCollapsed((value) => !value); }}>{sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}</button>
    <section className="content-area">
      <header className="masthead">
        <div className="masthead-context"><strong>{t(context.titleKey)}</strong><span>{t(context.descriptionKey)}</span></div>
        <div className="masthead-actions"><span className="last-updated">{lastUpdated ? t("common.updated", { value: when(lastUpdated.toISOString()) }) : t("common.syncing")}</span><label className="locale-picker"><span className="sr-only">{t("language.label")}</span><select aria-label={t("language.label")} value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>{localeOptions.map((option) => <option value={option.value} key={option.value}>{option.value === "en" ? t("language.en") : option.value === "zh-Hans" ? t("language.zhHans") : t("language.zhHant")}</option>)}</select></label><label className="project-picker"><span>{t("common.project")}</span><select value={project} onChange={(event) => changeProject(event.target.value)}>{projects.map((item) => <option value={item.slug} key={item.slug}>{item.name}</option>)}</select><ChevronDown size={15} /></label></div>
      </header>
      <div className="page-content" key={activeTab}>
        {error && <div className="status-note"><Activity size={15} />{error}</div>}
        {!data && loading ? <div className="loading-state"><LoaderCircle size={22} className="spin" /> {t("common.loadingWorkspace")}</div> : null}
        {data && activeTab === "overview" && <OverviewView data={data} project={project} onNavigate={changeTab} />}
        {data && activeTab === "activity" && <ActivityView data={data} project={project} onNavigate={changeTab} />}
        {data && activeTab === "scan" && <ScanView data={data} project={project} notify={notify} reload={load} />}
        {data && activeTab === "delivery" && <DeliveryView data={data} project={project} notify={notify} reload={load} />}
        {data && activeTab === "patch" && <PatchView data={data} project={project} notify={notify} reload={load} />}
        {data && activeTab === "observatory" && <ObservatoryView project={project} notify={notify} onDirtyChange={setObservatoryDirty} />}
        {data && activeTab === "repositories" && <RepositoryView data={data} interact={interact} />}
        {data && activeTab === "prompts" && <PromptsView data={data} project={project} interact={interact} notify={notify} />}
        {data && activeTab === "settings" && <SettingsView data={data} project={project} notify={notify} onDirtyChange={setSettingsDirty} reload={load} />}
      </div>
    </section>
    {gitConflict && <GitSyncConflictDialog conflict={gitConflict} project={project} notify={notify} onClose={() => setGitConflict(null)} onResolved={load} />}
    {notice && <div className={`toast toast-${notice.tone}`} role="status">{notice.tone === "success" ? <CircleCheck size={16} /> : notice.tone === "error" ? <CircleAlert size={16} /> : <CircleDot size={16} />}<span>{notice.message}</span></div>}
  </main>;
}

function GitSyncConflictDialog({ conflict, project, notify, onClose, onResolved }: { conflict: RecordValue; project: string; notify: Notify; onClose: () => void; onResolved: () => Promise<void> }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const overwrite = async () => {
    setBusy(true); setError("");
    try {
      await request("/api/git-sync/force", project, { method: "POST", json: {} });
      notify("Remote branch overwritten with the local Lumon commit", "success");
      onClose();
      await onResolved();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to overwrite the remote branch";
      setError(message);
    } finally { setBusy(false); }
  };
  return <div className="modal-backdrop" role="presentation"><section className="modal git-sync-conflict-modal" role="dialog" aria-modal="true" aria-label={t("common.remoteDecision")}><div className="modal-body compact"><strong>{t("common.remoteDecision")}</strong><p className="modal-copy">{t("common.remoteConflictCopy").replace("remote branch", `remote ${conflict.branch || "branch"}`)}</p><div className="git-sync-conflict-details"><span>{t("label.repository")}</span><code>{conflict.repo || t("common.workspace")}</code><span>{t("label.localCommit")}</span><code>{conflict.local_oid || "—"}</code></div>{error && <p className="git-sync-error" role="alert">{error}</p>}</div><footer><button className="button" disabled={busy} onClick={onClose}>{t("common.later")}</button><button className="button danger" disabled={busy} onClick={() => void overwrite()}>{busy ? t("common.overwriting") : t("common.overwriteRemote")}</button></footer></section></div>;
}

function PageIntro({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-intro"><div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

function deliveryStoryOptions(availableStories: RecordValue[], current?: RecordValue) {
  const options: Array<{ value: string; label: string }> = [];
  const seen = new Set<string>();
  const push = (story: string, jiraKey: string, title: string) => {
    const value = (story || jiraKey).trim();
    if (!value) return;
    const aliases = [value, jiraKey, story].map((item) => item.trim().toLowerCase()).filter(Boolean);
    if (aliases.some((alias) => seen.has(alias))) return;
    for (const alias of aliases) seen.add(alias);
    const key = (jiraKey || story || value).trim();
    const name = title.trim();
    options.push({ value, label: name ? `${key} · ${name}` : key });
  };
  for (const item of availableStories) {
    push(String(item.story || ""), String(item.jira_key || ""), String(item.title || ""));
  }
  if (current && /failed|blocked|not_started/i.test(String(current.delivery_status || ""))) {
    push(String(current.story_id || ""), String(current.jira_key || ""), String(current.story_title || ""));
  }
  return options;
}

function isDeliveryReadyStory(item: RecordValue) {
  const business = String(item.businessStatus || "").toLowerCase();
  const technical = String(item.technicalStatus || "").toLowerCase();
  const delivery = String(item.deliveryStatus || "not_started").toLowerCase();
  return business === "ready" && technical === "approved" && ["", "not_started", "blocked"].includes(delivery);
}

function AgentTeamBoard({ agents, workflows, t, onNavigate }: { agents: AgentSettings[]; workflows: Array<RecordValue>; t: Translate; onNavigate: (tab: Tab) => void }) {
  const titles: Record<string, string> = {
    dylan: "Engineering Risk Analyst",
    mark: "Delivery Lead",
    irving: "Remediation Engineer",
    milchick: "Engineering Operations Manager",
  };
  const findAgent = (id: string, workflow?: string) => agents.find((agent) => agent.id === id) || (workflow ? agents.find((agent) => agent.workflow === workflow) : undefined);
  const state = (agent?: AgentSettings) => !agent ? "not configured" : !agent.app_id || !agent.app_secret_configured || agent.model_configured === false ? "setup" : !agent.conversation_enabled ? "paused" : "ready";
  const identity = (agent: AgentSettings | undefined, profile: RecordValue) => {
    const id = String(agent?.id || profile.agent).toLowerCase();
    return { id, name: text(agent?.display_name, profile.agent), title: text(agent?.title, titles[id]) };
  };
  const manager = findAgent("milchick");
  const managerProfileLocalized = localizedWorkflowProfile(managerProfile, t);
  const renderIdentity = (agent: AgentSettings | undefined, profile: RecordValue) => {
    const person = identity(agent, profile);
    return <button type="button" className="agent-team-identity" aria-label={`${t("action.configureAgent")}: ${person.name}`} onClick={() => onNavigate("settings")}>
      <AgentAvatar agentId={agent?.id || person.id} displayName={person.name} size="card" />
      <span><strong>{person.name}</strong><small>{person.title}</small></span>
    </button>;
  };
  const renderResponsibility = (profile: RecordValue) => <div className="agent-team-responsibility">
    <p className="agent-team-mission">{profile.mission}</p>
    <div className="agent-team-flow"><span>{profile.input}</span><ChevronRight size={13} aria-hidden="true" /><span>{profile.output}</span></div>
  </div>;
  const displayStatus = (agent: AgentSettings | undefined, workflow?: RecordValue) => {
    const live = String(workflow?.status || "").toLowerCase();
    return /running|progress|active|blocked|failed|awaiting/.test(live) ? (workflow?.status || state(agent)) : state(agent);
  };
  return <div className="agent-team-board">
    <div className="agent-team-entry"><span className="agent-team-entry-icon"><img src="assets/feishu-mark.svg" alt="Feishu" /></span><span><span className="overview-kicker">{t("label.entryPoint")}</span><strong>{t("label.feishuEntry")}</strong><small>{t("context.activity.description")}</small></span></div>
    <span className="agent-team-connector" aria-hidden="true" />
    <div className="agent-team-layer"><article className="agent-team-card agent-team-manager">
      <div className="agent-team-card-heading">{renderIdentity(manager, managerProfileLocalized)}<Badge value={state(manager)} /></div>
      {renderResponsibility(managerProfileLocalized)}
      <footer className="agent-team-card-footer"><button type="button" className="text-button" onClick={() => onNavigate("settings")}>{t("action.configureAgent")} <ChevronRight size={13} /></button></footer>
    </article></div>
    <span className="agent-team-connector" aria-hidden="true" />
    <div className="agent-team-capabilities"><div className="agent-team-cards">
      {workflows.map((workflow) => {
        const agent = findAgent(String(workflow.agent).toLowerCase(), workflow.workflow);
        const profile = workflow;
        return <article className="agent-team-card" key={workflow.workflow}>
          <div className="agent-team-card-heading">{renderIdentity(agent, profile)}<span className="agent-team-statuses"><Badge value={displayStatus(agent, workflow)} /></span></div>
          {renderResponsibility(profile)}
          <footer className="agent-team-card-footer"><button type="button" className="button secondary" onClick={() => onNavigate(workflow.tab as Tab)}>{t("action.inspect", { feature: profile.feature })} <ChevronRight size={13} /></button></footer>
        </article>;
      })}
    </div></div>
  </div>;
}

function OverviewView({ data, project, onNavigate }: { data: DashboardData; project: string; onNavigate: (tab: Tab) => void }) {
  const { t } = useI18n();
  const settings = data.interactive?.agents || {};
  const agents = settings.agents || [];
  const workflows = workflowProfiles.map((profile) => ({
    ...localizedWorkflowProfile(profile, t),
    status: profile.workflow === "auto_scan" ? data.runs?.[0]?.status || "not started" : profile.workflow === "auto_delivery" ? data.delivery?.current?.delivery_status || "not started" : data.patch?.current?.patch_status || "not started",
  }));
  const agentState = (agent: AgentSettings) => {
    if (!agent.app_id || !agent.app_secret_configured || agent.model_configured === false) return "setup";
    if (!agent.conversation_enabled) return "paused";
    return "ready";
  };
  const readyAgents = agents.filter((agent) => agentState(agent) === "ready").length;
  const activeWorkflows = workflows.filter((workflow) => /running|progress|active/i.test(String(workflow.status))).length;
  const stateLabel = (state: string) => state === "setup" ? "not configured" : state;
  return <div className="manager-overview">
    <PageIntro title={t("heading.managerOverview")} description={`${project || t("common.currentProject")} · ${t("context.overview.description")}`} />
    <div className="metrics">
      <Metric label={t("label.agentsReady")} value={`${readyAgents}/${agents.length}`} />
      <Metric label={t("label.workflowsActive")} value={activeWorkflows} />
      <Metric label={t("label.agentRoles")} value={agents.length} />
      <Metric label={t("label.gateway")} value={settings.enabled ? t("common.enabled") : t("common.paused")} />
    </div>
    <Panel title={t("heading.agentTeam")} action={<button className="text-button" onClick={() => onNavigate("settings")}>{t("action.openSettings")} <ChevronRight size={13} /></button>}>
      <AgentTeamBoard agents={agents} workflows={workflows} t={t} onNavigate={onNavigate} />
    </Panel>
  </div>;
}

function ActivityView({ data, project, onNavigate }: { data: DashboardData; project: string; onNavigate: (tab: Tab) => void }) {
  const { t } = useI18n();
  const records = data.activity?.items || [];
  const [agentFilter, setAgentFilter] = useState("all");
  const [activityPage, setActivityPage] = useState(0);
  const visible = records.filter((record) => agentFilter === "all" || String(record.agent_id || "") === agentFilter);
  const roles = Array.from(new Set(records.map((record) => String(record.agent_id || "")).filter(Boolean)));
  const completed = records.filter((record) => /completed|success|delegated/i.test(String(record.status || ""))).length;
  const attention = records.filter((record) => /failed|blocked|denied/i.test(String(record.status || ""))).length;
  const processedQuestions = Number(data.activity?.total ?? records.length);
  const durations = records.map((record) => Number(record.latency_ms)).filter((value) => Number.isFinite(value) && value >= 0);
  const averageDuration = durations.length ? durationMs(Math.round(durations.reduce((sum, value) => sum + value, 0) / durations.length)) : "—";
  const activityPageSize = 10;
  const activityPageCount = Math.max(1, Math.ceil(visible.length / activityPageSize));
  const pageRecords = visible.slice(activityPage * activityPageSize, (activityPage + 1) * activityPageSize);
  useEffect(() => { setActivityPage(0); }, [agentFilter]);
  useEffect(() => { setActivityPage((page) => Math.min(page, activityPageCount - 1)); }, [activityPageCount]);
  const profileFor = (record: RecordValue) => localizedWorkflowProfile(workflowProfile(String(record.workflow || "")) || _AGENT_ACTIVITY_UI_PROFILES[String(record.agent_id || "")] || managerProfile, t);
  return <div className="activity-page">
    <PageIntro title={t("heading.agentActivity")} description={`${project || t("common.currentProject")} · ${t("context.activity.description")}`} action={<button className="button secondary" onClick={() => onNavigate("settings")}><Settings2 size={14} />{t("action.manageCapture")}</button>} />
    <div className="activity-role-guide">
      {[...workflowProfiles, managerProfile].map((sourceProfile) => { const profile = localizedWorkflowProfile(sourceProfile, t); return <article key={profile.workflow}>
        <AgentAvatar agentId={agentAvatarByWorkflow[profile.workflow]} displayName={profile.agent} size="guide" />
        <div><strong>{profile.agent} · {profile.feature}</strong><p>{profile.mission}</p></div>
      </article>; })}
    </div>
    <div className="metrics activity-metrics">
      <Metric label={t("label.processedQuestions")} value={processedQuestions} />
      <Metric label={t("label.averageDuration")} value={averageDuration} />
      <Metric label={t("label.completed")} value={completed} />
      <Metric label={t("label.needsAttention")} value={attention} />
    </div>
    <Panel title={t("heading.conversationRecords")} action={<div className="activity-toolbar"><span className="muted">{t("common.showing", { count: visible.length })}</span><label><span>{t("label.role")}</span><select aria-label={`${t("label.role")} filter`} value={agentFilter} onChange={(event) => setAgentFilter(event.target.value)}><option value="all">{t("common.all")} {t("label.role")}s</option>{roles.map((agent) => <option value={agent} key={agent}>{String(records.find((record) => String(record.agent_id || "") === agent)?.display_name || agent)}</option>)}</select></label></div>}>
      {!data.activity?.available && <div className="activity-note"><Activity size={15} />{text(data.activity?.detail, t("common.noAgentHistory"))}</div>}
      {pageRecords.length ? <div className="activity-record-list">{pageRecords.map((record) => {
        const profile = profileFor(record);
        const workflow = workflowProfiles.find((item) => item.workflow === record.workflow);
        const requestText = String(record.request_text || "").trim();
        const responseText = String(record.response_text || "").trim();
        const promptText = String(record.prompt_text || "").trim();
        const sourceLabel = record.source === "conversation" ? t("label.requestResult") : record.source === "outcome" ? t("label.resultCaptured") : t("label.traceOnly");
        const timeline = Array.isArray(record.timeline) ? record.timeline : [];
        return <article className="activity-record" key={String(record.trace_id || `${record.agent_id}-${record.started_at}`)}>
          <header className="activity-record-header"><div className="activity-record-identity"><AgentAvatar agentId={record.agent_id} displayName={record.display_name || profile.agent} size="record" /><div><span className="overview-kicker">{profile.feature}</span><h4>{text(record.display_name, profile.agent)}</h4><p>{text(record.action, sourceLabel)}</p></div></div><div className="activity-record-status"><Badge value={text(record.status, "unknown")} /><time>{when(record.started_at)}</time></div></header>
          <div className="activity-thread">
            <div className="activity-message user"><span>{t("common.you")}</span><MarkdownBody content={requestText || t("label.olderTrace")} /></div>
            <div className="activity-message agent"><span>{text(record.display_name, profile.agent)}</span><MarkdownBody content={responseText || t("label.noFinalResponse")} /></div>
          </div>
          <footer className="activity-record-footer"><span>{sourceLabel}</span><span>{t("common.trace")} <code>{text(record.trace_id)}</code></span><span>{record.latency_ms !== undefined && record.latency_ms !== null ? durationMs(record.latency_ms) : `${record.event_count || 0} events`}</span>{workflow && <button className="text-button" onClick={() => onNavigate(workflow.tab)}>{t("common.open")} {localizedWorkflowProfile(workflow, t).feature} <ChevronRight size={13} /></button>}</footer>
          <details className="activity-debug"><summary>{t("label.debugDetails")}</summary><div className="activity-debug-grid"><div><span>{t("label.input")}</span><MarkdownBody content={requestText || t("label.olderTrace")} /></div><div><span>{t("label.output")}</span><MarkdownBody content={responseText || t("label.noFinalResponse")} /></div><div className="activity-debug-prompt"><span>{t("common.originalPrompt")}</span>{promptText ? <pre>{promptText}</pre> : <p>{t("label.promptNotCaptured")}</p>}</div></div></details>
          {timeline.length > 0 && <details className="activity-trail"><summary>{t("label.executionTrail")}</summary><div>{timeline.map((event: RecordValue, index: number) => <p key={`${event.event}-${index}`}><time>{when(event.at)}</time><strong>{text(event.event)}</strong>{event.detail && <span>{text(event.detail)}</span>}</p>)}</div></details>}
        </article>;
      })}</div> : <div className="activity-empty"><MessageCirclePlaceholder /><strong>{t("common.noConversationRecords")}</strong><span>{data.activity?.available ? t("common.askAgents") : t("common.activityStoreFirstTurn")}</span></div>}
      {visible.length > activityPageSize && <Pagination page={activityPage} pageCount={activityPageCount} onChange={setActivityPage} />}
    </Panel>
    <p className="activity-retention-note">{t("label.activityRetention")}</p>
  </div>;
}

const _AGENT_ACTIVITY_UI_PROFILES: Record<string, typeof managerProfile> = {
  dylan: { ...workflowProfiles[0] },
  mark: { ...workflowProfiles[1] },
  irving: { ...workflowProfiles[2] },
  milchick: managerProfile,
};

function MessageCirclePlaceholder() {
  return <span className="activity-empty-icon" aria-hidden="true"><Activity size={18} /></span>;
}

function ScanView({ data, project, notify, reload }: { data: DashboardData; project: string; notify: Notify; reload: () => Promise<void> }) {
  const { t } = useI18n();
  const stats = data.run_stats || {};
  const issues = data.issues || [];
  const runs = data.runs || [];
  const [ignoreCandidate, setIgnoreCandidate] = useState<RecordValue | null>(null);
  const [filter, setFilter] = useState("all");
  const [runPage, setRunPage] = useState(0);
  const [scanStep, setScanStep] = useState<0 | 1 | 2>(0);
  const [scanBusy, setScanBusy] = useState(false);
  const [scanError, setScanError] = useState("");
  const runPageSize = 10;
  const openIssues = issues.filter((issue: RecordValue) => ["open", "in_progress", "pr_open", "reopened"].includes(String(issue.status || "").toLowerCase()));
  const filteredIssues = issues.filter((issue: RecordValue) => filter === "all" || (filter === "open" ? ["open", "in_progress", "pr_open", "reopened"].includes(String(issue.status || "").toLowerCase()) : String(issue.status || "").toLowerCase() === filter));
  const counts = { all: issues.length, open: openIssues.length, ignored: issues.filter((item: RecordValue) => String(item.status || "").toLowerCase() === "ignored").length, resolved: issues.filter((item: RecordValue) => String(item.status || "").toLowerCase() === "resolved").length };
  const pageRuns = runs.slice(runPage * runPageSize, (runPage + 1) * runPageSize);
  const jumpToFindings = () => document.getElementById("tracked-findings")?.scrollIntoView({ behavior: "smooth", block: "start" });
  const startScan = async () => {
    setScanBusy(true);
    setScanError("");
    try {
      await request("/api/scan/start", project, { method: "POST", json: {} });
      setScanStep(0);
      notify(`Scan started for ${project}`, "success");
      await reload().catch(() => undefined);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to start scan";
      const detail = message === "Not found"
        ? `Dashboard is still running an older version. Run \`lumon dashboard stop --project ${project}\`, then open the dashboard again.`
        : message;
      setScanError(detail);
      notify(detail, "error");
    } finally {
      setScanBusy(false);
    }
  };
  return <>
    <section className="metrics"><Metric label={t("label.openFindings")} value={openIssues.length} onClick={jumpToFindings} /><Metric label={t("label.successfulScan")} value={stats.success_7d || 0} /><Metric label={t("label.failed7d")} value={stats.failed_7d || 0} /><Metric label={t("label.lookbackWindow")} value={`${data.scan_window_days || 7}d`} /></section>
    <Panel title={t("heading.scanHistory")} action={<span className="panel-actions"><button type="button" className="button secondary" disabled={scanBusy} onClick={() => { setScanError(""); setScanStep(1); }}><Play size={14} />{t("action.startScan")}</button><span className="muted">{t("common.runs", { count: runs.length })}</span></span>}><div className="table-scroll"><table><thead><tr><th>{t("label.started")}</th><th>{t("label.status")}</th><th>{t("label.issues")}</th><th>{t("label.duration")}</th><th>{t("label.artifacts")}</th></tr></thead><tbody>{pageRuns.map((run: RecordValue) => <tr key={run.id}><td>{when(run.started_at || run.finished_at)}</td><td><Badge value={run.status} /></td><td><SeverityBreakdown run={run} /></td><td>{text(run.duration)}</td><td><div className="artifact-links">{run.html && <a href={`${run.html}?project=${encodeURIComponent(project)}`} target="_blank">HTML</a>}{run.pdf && <a href={`${run.pdf}?project=${encodeURIComponent(project)}`} target="_blank">PDF</a>}{!run.html && !run.pdf && "—"}</div></td></tr>)}</tbody></table></div>{runs.length > runPageSize && <Pagination page={runPage} pageCount={Math.ceil(runs.length / runPageSize)} onChange={setRunPage} />}</Panel>
    <Panel title={t("heading.trackedFindings")} action={<span className="muted">{filteredIssues.length} / {issues.length} {t("label.issues")}</span>}><div className="finding-filters" role="tablist">{(["all", "open", "resolved", "ignored"] as const).map((value) => <button className={filter === value ? "active" : ""} onClick={() => setFilter(value)} key={value}>{value === "all" ? t("common.all") : titleStatus(value)} <span>{counts[value]}</span></button>)}</div><div id="tracked-findings" className="findings">{filteredIssues.length ? filteredIssues.map((issue: RecordValue) => <Finding issue={issue} onIgnore={() => setIgnoreCandidate(issue)} key={issue.id} />) : <Empty label={t("common.noFindings")} />}</div></Panel>
    {ignoreCandidate && <IgnoreDialog onClose={() => setIgnoreCandidate(null)} onConfirm={(reason) => { void interactIgnore(project, notify, reload, ignoreCandidate.id, reason); setIgnoreCandidate(null); }} />}
    {scanStep > 0 && <StartScanDialog project={project} step={scanStep === 1 ? 1 : 2} busy={scanBusy} error={scanError} onClose={() => { if (!scanBusy) setScanStep(0); }} onContinue={() => setScanStep(2)} onConfirm={() => void startScan()} />}
  </>;
}

async function interactIgnore(project: string, notify: Notify, reload: () => Promise<void>, issueId: unknown, reason: string) {
  try {
    await request("/api/issue/ignore", project, { method: "POST", json: { issue_id: issueId, reason } });
    notify("Finding ignored", "success");
    await reload();
  } catch (err) {
    notify(err instanceof Error ? err.message : "Request failed", "error");
  }
}

function StartScanDialog({ project, step, busy, error, onClose, onContinue, onConfirm }: { project: string; step: 1 | 2; busy: boolean; error: string; onClose: () => void; onContinue: () => void; onConfirm: () => void }) {
  const { t } = useI18n();
  const first = step === 1;
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={first ? t("action.startScan") : t("action.confirmScan")} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>{first ? t("action.runScan") : t("action.confirmScan")}</strong><p className="modal-copy">{first ? t("action.scanBody", { project }) : t("action.scanConfirmBody", { project })}</p>{error && <p className="status-note">{error}</p>}</div><footer><button className="button" disabled={busy} onClick={onClose}>{t("common.cancel")}</button>{first ? <button className="button primary" disabled={busy} onClick={onContinue}>{t("common.continue")}</button> : <button className="button primary" disabled={busy} onClick={onConfirm}><Play size={14} />{busy ? t("common.start") + "…" : t("action.startScan")}</button>}</footer></section></div>;
}

function Metric({ label, value, onClick }: { label: string; value: string | number; onClick?: () => void }) { return <div className={`metric ${onClick ? "metric-action" : ""}`} onClick={onClick} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined} onKeyDown={(event) => { if (onClick && (event.key === "Enter" || event.key === " ")) onClick(); }}><span>{label}</span><strong>{value}</strong></div>; }
function Empty({ label }: { label: string }) { return <div className="empty"><ShieldCheck size={20} />{label}</div>; }
function SeverityBreakdown({ run }: { run: RecordValue }) {
  const { t } = useI18n();
  const levels = [[t("label.high"), Number(run.high || 0), "high"], [t("label.medium"), Number(run.medium || 0), "medium"], [t("label.low"), Number(run.low || 0), "low"]] as const;
  const present = levels.filter(([, count]) => count > 0);
  return present.length ? <span className="severity-breakdown">{present.map(([label, count, tone]) => <b className={tone} key={label}>{label}: {count}</b>)}</span> : <>—</>;
}
function Pagination({ page, pageCount, onChange }: { page: number; pageCount: number; onChange: (page: number) => void }) { const { t } = useI18n(); return <footer className="pagination"><span>{t("common.pageOf", { page: page + 1, count: pageCount })}</span><div><button className="button secondary" disabled={page === 0} onClick={() => onChange(page - 1)}>{t("common.previous")}</button><button className="button secondary" disabled={page === pageCount - 1} onClick={() => onChange(page + 1)}>{t("common.next")}</button></div></footer>; }
function Finding({ issue, onIgnore }: { issue: RecordValue; onIgnore: () => void }) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const status = issue.status || issue.issue_status || "open";
  const statusKey = String(status).toLowerCase();
  const isIgnorable = !["ignored", "resolved"].includes(statusKey);
  const primaryId = text(issue.jira_key) || text(issue.id);
  return <article className="finding"><div className="finding-main"><div className="finding-copy"><div className="finding-heading"><h4>{text(issue.title, t("label.untitledFinding"))}</h4><Badge value={status} /></div><p className="finding-meta"><code className="finding-id">{primaryId}</code><i>|</i>{text(issue.repository, t("label.unknownRepository"))} <i>|</i> {when(issue.last_seen_at)}</p><div className="finding-links finding-row-links"><button className="finding-link" onClick={() => setExpanded(!expanded)}>{expanded ? t("action.hideDetail") : t("action.viewDetail")}</button>{issue.jira_key && issue.jira_url && <a className="finding-link" href={issue.jira_url} target="_blank" rel="noreferrer">{issue.jira_key}<ExternalLink size={12} /></a>}{issue.pr_url && <a className="finding-link" href={issue.pr_url} target="_blank" rel="noreferrer">{t("action.pullRequest")}<ExternalLink size={12} /></a>}</div></div><div className="finding-actions">{isIgnorable && <button className="button secondary" onClick={onIgnore}>{t("action.markIgnored")}</button>}</div></div>{expanded && <div className="finding-detail"><FindingDetail label={t("label.status")} value={titleStatus(status)} /><FindingDetail label="Resolution basis" value={issue.resolution_basis_label || issue.resolution_basis} /><FindingDetail label={t("label.verification")} value={issue.verification_label || issue.verification_status} /><FindingDetail label="Resolved by" value={issue.resolved_by} /><FindingDetail label="Resolved at" value={when(issue.resolved_at)} /><FindingDetail label="Last verification" value={when(issue.last_verified_at)} /><FindingDetail label="Impact" value={issue.impact} /><FindingDetail label="Trigger" value={issue.trigger} /><FindingDetail label="Root cause" value={issue.root_cause} /><FindingDetail label="Code" value={issue.code_snippet} code /><FindingDetail label="Recommended correction" value={issue.suggestion} /><FindingDetail label="Validation" value={issue.validation} /><FindingDetail label="Risk Finding ID" value={issue.risk_finding_id} /><FindingDetail label="Legacy Issue ID" value={issue.id} /><FindingDetail label="Status source" value={issue.status_source} /></div>}</article>;
}

function FindingDetail({ label, value, code = false }: { label: string; value: unknown; code?: boolean }) { return <section className="finding-detail-row"><h5>{label}</h5>{code ? <pre><code>{text(value, "No code snippet was captured for this historical finding.")}</code></pre> : <p>{text(value, "Not recorded.")}</p>}</section>; }
function IgnoreDialog({ onClose, onConfirm }: { onClose: () => void; onConfirm: (reason: string) => void }) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={t("action.markIgnored")} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>{t("label.ignoreQuestion")}</strong><Field label={t("label.reasonOptional")}><textarea className="ignore-reason" rows={2} autoFocus value={reason} onChange={(event) => setReason(event.target.value)} placeholder={t("label.ignorePlaceholder")} /></Field></div><footer><button className="button" onClick={onClose}>{t("common.cancel")}</button><button className="button primary" onClick={() => onConfirm(reason)}>{t("action.markIgnored")}</button></footer></section></div>;
}

function DeliveryView({ data, project, notify, reload }: { data: DashboardData; project: string; notify: Notify; reload: () => Promise<void> }) {
  const { t } = useI18n();
  const delivery = data.delivery || {};
  const current = delivery.current || {};
  const runs = delivery.runs || [];
  const stages = current.stages || [];
  const schedulerActivity = delivery.scheduler_activity || [];
  const availableStories = delivery.available_stories || [];
  const [selectedStage, setSelectedStage] = useState<RecordValue | null>(null);
  const [selectedChecks, setSelectedChecks] = useState<RecordValue[] | null>(null);
  const [logContent, setLogContent] = useState("");
  const [logError, setLogError] = useState("");
  const [loadingLog, setLoadingLog] = useState(false);
  const [schedulerLogOpen, setSchedulerLogOpen] = useState(false);
  const [retryOpen, setRetryOpen] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState("");
  const [startStep, setStartStep] = useState<0 | 1 | 2>(0);
  const [selectedStory, setSelectedStory] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [deleteCandidate, setDeleteCandidate] = useState<RecordValue | null>(null);
  const [deletingHistoryId, setDeletingHistoryId] = useState("");
  const [now, setNow] = useState(Date.now());
  const running = /in_progress|running|awaiting_deploy/i.test(String(current.delivery_status || ""));
  const deployment = current.deployment && typeof current.deployment === "object" ? current.deployment : null;
  const storyOptions = deliveryStoryOptions(availableStories, current);
  const loadDeliveryLog = useCallback(async (runId = current.run_id || "", refresh = false) => {
    if (!refresh) setLoadingLog(true);
    try { const response = await request(`/api/delivery/log?run_id=${encodeURIComponent(runId)}`, project); setLogContent(response.content || "No log content recorded."); setLogError(""); }
    catch (err) { setLogError(err instanceof Error ? err.message : "Unable to load delivery log"); }
    finally { setLoadingLog(false); }
  }, [current.run_id, project]);
  useEffect(() => { if (!running) return; const id = window.setInterval(() => setNow(Date.now()), 1_000); return () => window.clearInterval(id); }, [running]);
  const selectedLogIsLive = Boolean(selectedStage && running && selectedStage.run_id === current.run_id && /in_progress|running/i.test(String(selectedStage.status || "")));
  useEffect(() => { if (!selectedLogIsLive || !selectedStage) return; const id = window.setInterval(() => void loadDeliveryLog(selectedStage.run_id, true), 2_000); return () => window.clearInterval(id); }, [selectedStage, selectedLogIsLive, loadDeliveryLog]);
  const openStage = async (stage: RecordValue, runId = current.run_id || "") => {
    setSelectedStage({ ...stage, run_id: runId }); setLogContent(""); setLogError(""); await loadDeliveryLog(runId);
  };
  const openSchedulerLog = async () => {
    setSchedulerLogOpen(true); setLogContent(""); setLogError(""); setLoadingLog(true);
    try { const response = await request("/api/delivery/scheduler-log", project); setLogContent(response.content || "No scheduler output recorded."); }
    catch (err) { setLogError(err instanceof Error ? err.message : "Unable to load scheduler log"); }
    finally { setLoadingLog(false); }
  };
  const retry = async () => {
    setRetrying(true); setRetryError("");
    try { await request("/api/delivery/retry", project, { method: "POST", json: {} }); setRetryOpen(false); notify("Delivery retry started", "success"); await reload().catch(() => undefined); }
    catch (err) { const message = err instanceof Error ? err.message : "Unable to retry delivery"; setRetryError(message === "Not found" ? "Dashboard is still running an older version. Run `lumon dashboard stop --project …`, then open the dashboard again." : message); }
    finally { setRetrying(false); }
  };
  const openStart = () => {
    setActionError("");
    setSelectedStory(storyOptions[0]?.value || "");
    setStartStep(1);
  };
  const start = async () => {
    const story = selectedStory.trim();
    if (!story) {
      notify("Select a story to start", "error");
      return;
    }
    setActionBusy(true); setActionError("");
    try {
      await request("/api/delivery/start", project, { method: "POST", json: { story } });
      setStartStep(0);
      notify(`Delivery started for ${story}`, "success");
      await reload().catch(() => undefined);
    }
    catch (err) { const message = err instanceof Error ? err.message : "Unable to start delivery"; setActionError(message); notify(message, "error"); }
    finally { setActionBusy(false); }
  };
  const stop = async () => {
    if (!window.confirm("Stop this delivery and remove its worktrees?")) return;
    setActionBusy(true); setActionError("");
    try { await request("/api/delivery/stop", project, { method: "POST", json: {} }); notify("Delivery stopped", "success"); await reload(); }
    catch (err) { const message = err instanceof Error ? err.message : "Unable to stop delivery"; setActionError(message); notify(message, "error"); }
    finally { setActionBusy(false); }
  };
  const openTrace = async (runId: string) => {
    try { const response = await request(`/api/delivery/trace?run_id=${encodeURIComponent(runId)}`, project); setSelectedStage({ label: "Trace", duration: "Agent evidence", detail: "Redacted local execution evidence", run_id: runId }); setLogContent(JSON.stringify(response, null, 2)); setLogError(""); }
    catch (err) { setActionError(err instanceof Error ? err.message : "Unable to load trace"); }
  };
  const removeHistory = async () => {
    const runId = String(deleteCandidate?.run_id || "").trim();
    if (!runId) return;
    setDeletingHistoryId(runId); setActionError("");
    try {
      await request("/api/delivery/history/delete", project, { method: "POST", json: { run_id: runId } });
      setDeleteCandidate(null);
      notify("Delivery history deleted", "success");
      await reload().catch(() => undefined);
    } catch (err) { const message = err instanceof Error ? err.message : "Unable to delete delivery history"; setActionError(message); notify(message, "error"); }
    finally { setDeletingHistoryId(""); }
  };
  const canRetry = /failed|blocked/i.test(String(current.delivery_status || ""));
  const canStart = !running && storyOptions.length > 0;
  return <>
    <Panel title={t("heading.currentProgress")} className="delivery-summary" action={<span className="panel-actions">{canStart && <button className="button secondary" disabled={actionBusy} onClick={openStart}><Play size={14} />{t("common.start")}</button>}{running && <button className="button danger secondary" disabled={actionBusy} onClick={() => void stop()}>{t("common.stop")}</button>}{canRetry && <button className="button secondary" onClick={() => setRetryOpen(true)}><RotateCcw size={14} />{t("common.retry")}</button>}</span>}><div className="delivery-facts"><Fact label={t("label.currentStory")} value={<StoryReference jiraKey={current.jira_key || current.story_id} title={current.story_title} />} /><Fact label={t("label.status")} value={<Badge value={current.delivery_status || "not started"} />} /><Fact label={t("label.elapsed")} value={elapsed(current.started_at, current.finished_at || (running ? new Date(now).toISOString() : undefined))} /><Fact label={t("label.finished")} value={running ? t("status.running") : when(current.finished_at)} /></div>{deployment && <div className="deployment-tracking"><div><span>{t("label.deployment")}</span><strong><Badge value={deployment.status || "queued"} /></strong></div><div><span>{t("label.provider")}</span><strong>{text(String(deployment.provider || "").replaceAll("_", " "))}</strong></div><div><span>{t("label.lastChecked")}</span><strong>{when(deployment.last_checked_at)}</strong></div>{deployment.url && <a href={deployment.url} target="_blank" rel="noreferrer">{t("action.openDeployment")} <ExternalLink size={12} /></a>}<p>{text(deployment.detail, t("settings.deploymentTrackingDescription"))}</p></div>}{actionError && <div className="status-note">{actionError}</div>}<DeliveryFlow stages={stages} deliveryStatus={String(current.delivery_status || "")} currentStep={String(current.current_step || "")} startedAt={current.started_at} finishedAt={current.finished_at} remediation={current.remediation} now={now} onStageClick={openStage} /></Panel>
    <Panel title={t("heading.deliveryHistory")} className="history-panel" action={<span className="muted">{t("common.runs", { count: runs.length })}</span>}><div className="table-scroll"><table><thead><tr><th>{t("label.story")}</th><th>{t("label.finishedAt")}</th><th>{t("label.status")}</th><th>{t("label.pullRequests")}</th><th>{t("label.checks")}</th><th>{t("label.duration")}</th><th>{t("label.trace")}</th><th>{t("label.operation")}</th></tr></thead><tbody>{runs.length ? runs.map((run: RecordValue) => { const runChecks = run.verification || []; const failed = runChecks.filter((item: RecordValue) => item.status === "failed"); const canInspectStatus = failed.length || /failed|blocked/i.test(String(run.status)); return <tr key={run.run_id}><td><div className="history-story"><span className="history-story-line"><code>{text(run.jira_key || run.story || run.run_id)}</code>{run.story_title && <span className="history-story-title">{run.story_title}</span>}</span><small>{text(run.branch, "")}</small></div></td><td>{when(run.finished_at || run.started_at)}</td><td>{canInspectStatus ? <button className="status-badge-button" title={t("action.openLog")} onClick={() => void openStage({ label: "Delivery failure", duration: elapsed(run.started_at, run.finished_at), detail: failed.map((item: RecordValue) => item.summary || item.label).filter(Boolean).join(" · ") || "Open the delivery log for details." }, run.run_id)}><Badge value={run.status} /></button> : <Badge value={run.status} />}</td><td><PrLinks items={run.pull_requests || []} /></td><td><VerificationSummary checks={runChecks} onClick={() => setSelectedChecks(runChecks)} /></td><td>{elapsed(run.started_at, run.finished_at)}</td><td>{run.agent_trace && <button className="text-button" onClick={() => void openTrace(run.run_id)}>{t("common.viewTrace")}</button>}</td><td><IconButton label="Delete delivery record" danger disabled={deletingHistoryId === run.run_id} onClick={() => setDeleteCandidate(run)}><Trash2 size={15} /></IconButton></td></tr>; }) : <tr><td colSpan={8}><Empty label={t("common.noDeliveryHistory")} /></td></tr>}</tbody></table></div></Panel>
    <Panel title={t("heading.schedulerActivity")} action={<span className="panel-actions"><span className="muted">{t("common.recentEvents", { count: schedulerActivity.length })}</span>{delivery.scheduler_log_available && <button className="button secondary" onClick={() => void openSchedulerLog()}><Terminal size={14} />{t("action.viewRawLog")}</button>}</span>}><div className="scheduler-activity">{schedulerActivity.length ? schedulerActivity.map((event: RecordValue, index: number) => <article className="scheduler-event" key={`${event.at}-${index}`}><Badge value={event.outcome} /><div><strong>{text(event.story_id || event.jira_key, t("common.workspace"))}</strong><p>{text(event.message)}</p></div><time>{when(event.at)}</time></article>) : <Empty label={t("common.noDeliveryActivity")} />}</div></Panel>
    {selectedStage && <DeliveryLogDialog stage={selectedStage} content={logContent} error={logError} loading={loadingLog} live={selectedLogIsLive} onClose={() => setSelectedStage(null)} />}
    {schedulerLogOpen && <DeliveryLogDialog stage={{ label: "Scheduler log", duration: "Recent raw output", detail: "Launchd output is capped at 256 KiB; structured activity retains the latest 200 events." }} content={logContent} error={logError} loading={loadingLog} onClose={() => setSchedulerLogOpen(false)} />}
    {selectedChecks && <VerificationDialog checks={selectedChecks} onClose={() => setSelectedChecks(null)} />}
    {retryOpen && <RetryDeliveryDialog story={text(current.jira_key || current.story_id)} busy={retrying} error={retryError} onClose={() => setRetryOpen(false)} onConfirm={() => void retry()} />}
    {startStep > 0 && <StartDeliveryDialog stories={storyOptions} value={selectedStory} onChange={setSelectedStory} step={startStep === 1 ? 1 : 2} busy={actionBusy} error={actionError} onClose={() => { if (!actionBusy) setStartStep(0); }} onContinue={() => setStartStep(2)} onConfirm={() => void start()} />}
    {deleteCandidate && <DeleteHistoryDialog run={deleteCandidate} busy={Boolean(deletingHistoryId)} onClose={() => setDeleteCandidate(null)} onConfirm={() => void removeHistory()} />}
  </>;
}

function PatchView({ data, project, notify, reload }: { data: DashboardData; project: string; notify: Notify; reload: () => Promise<void> }) {
  const { t } = useI18n();
  const patch = data.patch || {};
  const current = patch.current || {};
  const runs = patch.runs || [];
  const activity = patch.scheduler_activity || [];
  const running = Boolean(current.active) || /in_progress|running/i.test(String(current.patch_status || ""));
  const [log, setLog] = useState("");
  const [logError, setLogError] = useState("");
  const [logOpen, setLogOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState<RecordValue | null>(null);
  const [deletingHistoryId, setDeletingHistoryId] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [candidateOpen, setCandidateOpen] = useState(false);
  const [candidateLoading, setCandidateLoading] = useState(false);
  const [candidateError, setCandidateError] = useState("");
  const [candidates, setCandidates] = useState<RecordValue[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const loadLog = async (runId = String(current.run_id || "")) => {
    setLogOpen(true); setLog(""); setLogError("");
    try { const response = await request(`/api/patch/log?run_id=${encodeURIComponent(runId)}`, project); setLog(response.content || "No log content recorded."); }
    catch (err) { setLogError(err instanceof Error ? err.message : "Unable to load Auto Patch log"); }
  };
  const openCandidates = async () => {
    setCandidateOpen(true); setCandidateLoading(true); setCandidateError(""); setCandidates([]); setSelectedCandidate("");
    try {
      const response = await request("/api/patch/candidates", project);
      const items = Array.isArray(response.candidates) ? response.candidates : [];
      setCandidates(items);
      setSelectedCandidate(String(items.find((item: RecordValue) => item.available)?.jira_key || ""));
    } catch (err) { setCandidateError(err instanceof Error ? err.message : "Unable to load Auto Patch candidates"); }
    finally { setCandidateLoading(false); }
  };
  const start = async (jiraKey = "") => {
    setBusy(true);
    try { await request("/api/patch/start", project, { method: "POST", json: { jira_key: jiraKey } }); setCandidateOpen(false); notify("Auto Patch started", "success"); await reload(); }
    catch (err) { notify(err instanceof Error ? err.message : "Unable to start Auto Patch", "error"); }
    finally { setBusy(false); }
  };
  const stop = async () => {
    setBusy(true);
    try { await request("/api/patch/stop", project, { method: "POST", json: {} }); notify("Auto Patch stopped", "success"); await reload(); }
    catch (err) { notify(err instanceof Error ? err.message : "Unable to stop Auto Patch", "error"); }
    finally { setBusy(false); }
  };
  const removeHistory = async () => {
    const runId = String(deleteCandidate?.run_id || "").trim();
    if (!runId) return;
    setDeletingHistoryId(runId); setHistoryError("");
    try {
      await request("/api/patch/history/delete", project, { method: "POST", json: { run_id: runId } });
      setDeleteCandidate(null);
      notify("Patch history deleted", "success");
      await reload().catch(() => undefined);
    } catch (err) { const message = err instanceof Error ? err.message : "Unable to delete Auto Patch history"; setHistoryError(message); notify(message, "error"); }
    finally { setDeletingHistoryId(""); }
  };
  return <>
    <Panel title={t("heading.currentProgress")} action={<span className="panel-actions">{running ? <button className="button danger secondary" disabled={busy} onClick={() => void stop()}>{t("common.stop")}</button> : <button className="button secondary" disabled={busy} onClick={() => void openCandidates()}><Play size={14} />{t("action.runCycle")}</button>}</span>}>
      <div className="delivery-facts"><Fact label={t("label.jiraCard")} value={<StoryReference jiraKey={current.jira_key} title={current.jira_summary} />} /><Fact label={t("label.status")} value={<Badge value={current.patch_status || "not started"} />} /><Fact label={t("label.branch")} value={<code>{text(current.branch)}</code>} /><Fact label={t("label.repositories")} value={Array.isArray(current.repositories) ? current.repositories.map((item: RecordValue) => item.name).filter(Boolean).join(", ") || "—" : "—"} /></div>
      {current.question && <div className="status-note"><CircleHelp size={15} />{current.question}</div>}
      <PatchFlow phases={Array.isArray(current.stages) ? current.stages : []} overallStatus={String(current.patch_status || "")} />
    </Panel>
    <Panel title={t("heading.patchHistory")} action={<span className="muted">{t("common.runs", { count: runs.length })}</span>}>{historyError && <div className="status-note">{historyError}</div>}<div className="table-scroll patch-history-scroll"><table className="patch-history-table"><thead><tr><th>{t("label.jira")}</th><th>{t("label.summary")}</th><th>{t("label.status")}</th><th>{t("label.repositories")}</th><th>{t("label.finishedAt")}</th><th>{t("label.log")}</th><th>{t("label.operation")}</th></tr></thead><tbody>{runs.length ? runs.map((run: RecordValue) => <tr key={run.run_id}><td><div className="patch-history-jira"><span className="patch-history-key">{text(run.jira_key)}</span>{run.jira_summary && <span className="patch-history-jira-title" title={text(run.jira_summary)}>{text(run.jira_summary)}</span>}</div></td><td><span className="patch-history-summary" title={text(run.summary)}>{text(run.summary)}</span></td><td><Badge value={run.status} /></td><td>{(run.repositories || []).map((item: RecordValue) => item.name).filter(Boolean).join(", ") || "—"}</td><td><span className="patch-history-finished">{when(run.finished_at)}</span></td><td><button className="text-button" onClick={() => void loadLog(run.run_id)}>{t("common.viewLog")}</button></td><td><IconButton label="Delete Auto Patch record" danger disabled={deletingHistoryId === run.run_id} onClick={() => setDeleteCandidate(run)}><Trash2 size={15} /></IconButton></td></tr>) : <tr><td colSpan={7}><Empty label={t("common.noPatchHistory")} /></td></tr>}</tbody></table></div></Panel>
    <Panel title={t("heading.schedulerActivity")}><div className="scheduler-activity">{activity.length ? activity.map((event: RecordValue, index: number) => <article className="scheduler-event" key={`${event.at}-${index}`}><Badge value={event.outcome} /><div><strong>{text(event.jira_key || event.card, t("common.workspace"))}</strong><p>{text(event.message)}</p></div><time>{when(event.at)}</time></article>) : <Empty label={t("common.noPatchActivity")} />}</div></Panel>
    {candidateOpen && <PatchCandidateDialog candidates={candidates} selected={selectedCandidate} loading={candidateLoading} error={candidateError} busy={busy} onChange={setSelectedCandidate} onClose={() => { if (!busy) setCandidateOpen(false); }} onConfirm={() => void start(selectedCandidate)} />}
    {logOpen && <DeliveryLogDialog stage={{ label: "Auto Patch log", detail: "Recent Auto Patch agent output" }} content={log} error={logError} loading={!log && !logError} onClose={() => setLogOpen(false)} />}
    {deleteCandidate && <DeleteHistoryDialog kind="patch" run={deleteCandidate} busy={Boolean(deletingHistoryId)} onClose={() => setDeleteCandidate(null)} onConfirm={() => void removeHistory()} />}
  </>;
}

function PatchCandidateDialog({ candidates, selected, loading, error, busy, onChange, onClose, onConfirm }: { candidates: RecordValue[]; selected: string; loading: boolean; error: string; busy: boolean; onChange: (value: string) => void; onClose: () => void; onConfirm: () => void }) {
  const { t } = useI18n();
  const available = candidates.filter((candidate) => candidate.available);
  const empty = !loading && !error && !candidates.length;
  const unavailable = !loading && Boolean(error);
  const title = loading ? `${t("label.autoPatch")} · ${t("common.loading")}` : unavailable ? `${t("label.autoPatch")} · ${t("status.notSet")}` : empty ? `${t("label.autoPatch")} · ${t("common.noData")}` : `${t("label.autoPatch")} · ${t("common.selectStory")}`;
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal patch-candidate-modal" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>{title}</strong><p className="modal-copy">{t("common.onlyTaskBugCards")}</p>{loading && <div className="patch-candidate-empty">{t("common.loading")}</div>}{unavailable && <div className="patch-candidate-error"><CircleAlert size={17} /><div><strong>{t("common.unableLoadState")}</strong><p>{error}</p></div></div>}{empty && <div className="patch-candidate-empty">{t("common.noPendingPatchCards")}</div>}{!loading && !error && candidates.length > 0 && <div className="patch-candidate-list">{candidates.map((candidate: RecordValue) => { const key = String(candidate.jira_key || ""); const disabled = !candidate.available; return <label className={`patch-candidate-option${selected === key ? " selected" : ""}${disabled ? " disabled" : ""}`} key={key}><input type="radio" name="patch-candidate" value={key} checked={selected === key} disabled={disabled || busy} onChange={() => onChange(key)} /><span><strong>{key} · {text(candidate.summary)}</strong><small>{text(candidate.issue_type, "Task")} · {text(candidate.status, "Unknown status")}{candidate.priority ? ` · Priority ${candidate.priority}` : ""}</small>{candidate.reason && <em>{candidate.reason}</em>}</span></label>; })}</div>}</div><footer><button className="button" disabled={busy} onClick={onClose}>{t("common.close")}</button>{!empty && !unavailable && <button className="button primary" disabled={busy || !selected || available.length === 0} onClick={onConfirm}><Play size={14} />{busy ? `${t("common.start")}…` : `${t("common.start")} ${t("label.autoPatch")}`}</button>}</footer></section></div>;
}

function PatchFlow({ phases, overallStatus }: { phases: RecordValue[]; overallStatus: string }) {
  const { t } = useI18n();
  const visiblePhases = phases.filter((phase) => !["screen", "context"].includes(String(phase.id || "").toLowerCase()));
  const skipped = String(overallStatus).toLowerCase() === "skipped";
  const completed = visiblePhases.filter((phase) => phase.status === "completed").length;
  const trackWidth = skipped
    ? visiblePhases.length > 1 ? Math.round(Math.max(completed - 1, 0) / (visiblePhases.length - 1) * 100) : 0
    : visiblePhases.length ? Math.round(completed / visiblePhases.length * 100) : 0;
  return <div className="delivery-flow patch-flow"><div className="flow-heading"><div><span className="flow-title">{t("label.autoPatch")} Flow</span></div><p>{t("common.patchFlow")}</p></div><div className="flow-track-wrap"><span className="flow-track"><i style={{ width: `${trackWidth}%` }} /></span><ol className="flow-steps" style={{ "--flow-count": Math.max(visiblePhases.length, 1) } as React.CSSProperties}>{visiblePhases.map((phase, index) => { const status = String(phase.status || "pending").toLowerCase(); const state = skipped && status !== "completed" ? "skipped" : status === "completed" ? "completed" : /in_progress|running/.test(status) ? "running" : /failed|blocked/.test(status) ? "failed" : "pending"; const detail = text(phase.detail || phase.status, t("label.pending")); const duration = phase.started_at ? elapsed(phase.started_at, phase.finished_at || new Date().toISOString()) : "—"; return <li className={`flow-step ${state}`} key={phase.id || index}><div className="flow-stage-button"><span className="flow-marker">{state === "completed" ? "✓" : state === "skipped" ? "–" : index + 1}</span><span className="flow-copy"><strong>{text(phase.label)}</strong><span className="flow-detail" title={detail}>{detail}</span><small className="flow-duration">{duration}</small></span></div></li>; })}</ol></div></div>;
}

function StartDeliveryDialog({ stories, value, onChange, step, busy, error, onClose, onContinue, onConfirm }: { stories: Array<{ value: string; label: string }>; value: string; onChange: (value: string) => void; step: 1 | 2; busy: boolean; error: string; onClose: () => void; onContinue: () => void; onConfirm: () => void }) {
  const { t } = useI18n();
  const first = step === 1;
  const selectedLabel = stories.find((item) => item.value === value)?.label || value;
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={first ? t("label.autoDelivery") : t("label.autoDelivery")} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>{first ? t("action.startDelivery") : `${t("action.startDelivery")} · ${t("common.confirm")}`}</strong><p className="modal-copy">{first ? "Choose a ready story to launch." : `Are you sure you want to start delivery for ${selectedLabel} now?`}</p>{first && <label className="field"><span>{t("label.story")}</span><select value={value} onChange={(event) => onChange(event.target.value)} disabled={busy || stories.length === 0}>{stories.length ? stories.map((item) => <option value={item.value} key={item.value} title={item.label}>{item.label}</option>) : <option value="">{t("common.noData")}</option>}</select></label>}{error && <p className="status-note">{error}</p>}</div><footer><button className="button" disabled={busy} onClick={onClose}>{t("common.cancel")}</button>{first ? <button className="button primary" disabled={busy || !value} onClick={onContinue}>{t("common.continue")}</button> : <button className="button primary" disabled={busy || !value} onClick={onConfirm}><Play size={14} />{busy ? `${t("common.start")}…` : t("action.startDelivery")}</button>}</footer></section></div>;
}

function RetryDeliveryDialog({ story, busy, error, onClose, onConfirm }: { story: string; busy: boolean; error: string; onClose: () => void; onConfirm: () => void }) {
  const { t } = useI18n();
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={`${t("common.retry")} ${t("label.autoDelivery")}`} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>{t("common.retry")} {story}?</strong><p>{t("common.retryDeliveryCopy")}</p>{error && <p className="status-note">{error}</p>}</div><footer><button className="button" disabled={busy} onClick={onClose}>{t("common.cancel")}</button><button className="button primary" disabled={busy} onClick={onConfirm}><RotateCcw size={14} />{busy ? `${t("common.start")}…` : t("common.retry")}</button></footer></section></div>;
}

function DeleteHistoryDialog({ kind = "delivery", run, busy, onClose, onConfirm }: { kind?: "delivery" | "patch"; run: RecordValue; busy: boolean; onClose: () => void; onConfirm: () => void }) {
  const { t } = useI18n();
  const patch = kind === "patch";
  const story = text(run.jira_key || run.story || run.run_id);
  const type = patch ? t("label.autoPatch") : t("label.autoDelivery");
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal delete-history-modal" role="dialog" aria-modal="true" aria-label={`${type} history`} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>Delete {type} history?</strong><p className="modal-copy">This removes the {story} record, log, and trace files. This action cannot be undone.</p></div><footer><button className="button" disabled={busy} onClick={onClose}>{t("common.cancel")}</button><button className="button danger delete-confirm" disabled={busy} onClick={onConfirm}><Trash2 size={14} />{busy ? "Deleting…" : "Delete record"}</button></footer></section></div>;
}

function ObservatoryView({ project, notify, onDirtyChange }: { project: string; notify: Notify; onDirtyChange: (dirty: boolean) => void }) {
  const { t } = useI18n();
  const initialStory = new URLSearchParams(window.location.search).get("story") || "";
  const [stories, setStories] = useState<RecordValue[]>([]);
  const [selected, setSelected] = useState(initialStory);
  const [title, setTitle] = useState("");
  const [jiraKey, setJiraKey] = useState("");
  const [jiraUrl, setJiraUrl] = useState("");
  const [businessStatus, setBusinessStatus] = useState("");
  const [technicalStatus, setTechnicalStatus] = useState("");
  const [storyMarkdown, setStoryMarkdown] = useState("");
  const [planMarkdown, setPlanMarkdown] = useState("");
  const [baseline, setBaseline] = useState({ story: "", plan: "" });
  const [docTab, setDocTab] = useState<"story" | "plan">("story");
  const [loadingList, setLoadingList] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [saving, setSaving] = useState(false);
  const [storyQuery, setStoryQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [readyOnly, setReadyOnly] = useState(false);
  const [startStep, setStartStep] = useState<0 | 1 | 2>(0);
  const [selectedStartStory, setSelectedStartStory] = useState("");
  const [startBusy, setStartBusy] = useState(false);
  const [startError, setStartError] = useState("");
  const dirty = storyMarkdown !== baseline.story || planMarkdown !== baseline.plan;
  const deliveryOptions = deliveryStoryOptions(stories.filter(isDeliveryReadyStory));
  const canStartDelivery = deliveryOptions.length > 0;
  useEffect(() => { onDirtyChange(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (!dirty) return; event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const loadStories = useCallback(async () => {
    setLoadingList(true);
    try {
      const response = await request("/api/stories", project);
      const items = Array.isArray(response.stories) ? response.stories : [];
      setStories(items);
      setSelected((current) => {
        if (current && items.some((item: RecordValue) => item.story === current)) return current;
        return String(items[0]?.story || "");
      });
    } catch (err) {
      notify(err instanceof Error ? err.message : "Unable to load stories", "error");
    } finally {
      setLoadingList(false);
    }
  }, [project, notify]);
  const loadContent = useCallback(async (story: string) => {
    if (!story) return;
    setLoadingContent(true);
    setDocTab("story");
    try {
      const response = await request(`/api/stories/content?story=${encodeURIComponent(story)}`, project);
      setTitle(String(response.title || ""));
      setJiraKey(String(response.jira_key || ""));
      setJiraUrl(String(response.jira_url || ""));
      setBusinessStatus(String(response.businessStatus || ""));
      setTechnicalStatus(String(response.technicalStatus || ""));
      const nextStory = String(response.story_markdown || "");
      const nextPlan = String(response.plan_markdown || "");
      setStoryMarkdown(nextStory);
      setPlanMarkdown(nextPlan);
      setBaseline({ story: nextStory, plan: nextPlan });
      const url = new URL(window.location.href);
      url.searchParams.set("story", story);
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
    } catch (err) {
      notify(err instanceof Error ? err.message : "Unable to load story content", "error");
    } finally {
      setLoadingContent(false);
    }
  }, [project, notify]);
  useEffect(() => { void loadStories(); }, [loadStories]);
  useEffect(() => { if (selected) void loadContent(selected); }, [selected, loadContent]);
  const selectStory = (story: string) => {
    if (story === selected) return;
    if (dirty && !window.confirm(t("common.unsavedObservatory"))) return;
    setSelected(story);
  };
  const openStartDelivery = () => {
    setStartError("");
    const preferred = deliveryOptions.find((item) => item.value === selected)?.value || deliveryOptions[0]?.value || "";
    setSelectedStartStory(preferred);
    setStartStep(1);
  };
  const startDelivery = async () => {
    const story = selectedStartStory.trim();
    if (!story) {
      notify("Select a story to start", "error");
      return;
    }
    if (dirty && !window.confirm(t("common.unsavedObservatory"))) return;
    setStartBusy(true);
    setStartError("");
    try {
      await request("/api/delivery/start", project, { method: "POST", json: { story } });
      setStartStep(0);
      notify(`Delivery started for ${story}`, "success");
      await loadStories();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to start delivery";
      setStartError(message);
      notify(message, "error");
    } finally {
      setStartBusy(false);
    }
  };
  const save = async () => {
    if (!selected || !dirty) return;
    setSaving(true);
    try {
      const result = await request("/api/stories/content", project, {
        method: "POST",
        json: { story: selected, story_markdown: storyMarkdown, plan_markdown: planMarkdown },
      });
      setBaseline({ story: storyMarkdown, plan: planMarkdown });
      notify(String(result.subject || "Story docs saved"), "success");
      await loadStories();
    } catch (err) {
      notify(err instanceof Error ? err.message : "Unable to save story docs", "error");
    } finally {
      setSaving(false);
    }
  };
  const storyKey = text(jiraKey || selected);
  const storyTitle = text(title, selected);
  const visibleStories = stories
    .filter((item) => {
      if (readyOnly && String(item.businessStatus || "").toLowerCase() !== "ready") return false;
      const needle = storyQuery.trim().toLowerCase();
      if (!needle) return true;
      const haystack = `${item.jira_key || ""} ${item.title || ""} ${item.story || ""} ${item.assignee || ""}`.toLowerCase();
      return haystack.includes(needle);
    })
    .slice()
    .sort((left, right) => {
      const leftDate = String(left.updatedAt || left.createdAt || "");
      const rightDate = String(right.updatedAt || right.createdAt || "");
      if (leftDate !== rightDate) return rightDate.localeCompare(leftDate);
      return String(right.story || "").localeCompare(String(left.story || ""));
    });
  return <div className="observatory-layout">
    <aside className="observatory-list panel">
      <div className="panel-header observatory-list-header">
        <h3>{t("heading.stories")}</h3>
        <div className="observatory-list-tools">
          <button type="button" className={`icon-button${searchOpen ? " active" : ""}`} title={t("action.searchStories")} aria-label={t("action.searchStories")} aria-pressed={searchOpen} onClick={() => setSearchOpen((value) => !value)}><Search size={15} /></button>
          <button type="button" className={`icon-button${readyOnly ? " active" : ""}`} title={readyOnly ? t("action.showingReadyStories") : t("action.filterReadyStories")} aria-label={t("action.filterStories")} aria-pressed={readyOnly} onClick={() => setReadyOnly((value) => !value)}><ListFilter size={15} /></button>
        </div>
      </div>
      {searchOpen && <div className="observatory-list-search"><input value={storyQuery} onChange={(event) => setStoryQuery(event.target.value)} placeholder={t("action.searchStories")} aria-label={t("action.searchStories")} autoFocus /></div>}
      <div className="observatory-list-body">
        {loadingList ? <div className="loading-state"><LoaderCircle size={18} className="spin" /> {t("common.loading")}</div> : null}
        {!loadingList && !visibleStories.length ? <Empty label={stories.length ? t("common.noStoriesFilter") : t("common.noStories")} /> : null}
        {visibleStories.map((item) => {
          const key = text(item.jira_key || item.story);
          const itemTitle = text(item.title, item.story);
          return <button className={`observatory-story ${selected === item.story ? "selected" : ""}`} key={item.story} onClick={() => selectStory(String(item.story))}>
            <div className="observatory-story-copy"><span className="observatory-key">{key}</span><span className="observatory-story-title">{itemTitle}</span></div>
            <StoryListMeta date={String(item.updatedAt || "")} assignee={String(item.assignee || "")} />
            <StoryListStatus business={String(item.businessStatus || "draft")} technical={String(item.technicalStatus || "draft")} />
          </button>;
        })}
      </div>
    </aside>
    <section className="observatory-detail panel">
      {!selected ? <Empty label={t("common.selectStory")} /> : <>
        <div className="observatory-header">
          <div className="observatory-title-row">
            <h2>
              {jiraUrl
                ? <a className="observatory-heading-link" href={jiraUrl} target="_blank" rel="noreferrer"><span className="observatory-key">{storyKey}</span><span className="observatory-heading-title">{storyTitle}</span><ExternalLink size={12} /></a>
                : <><span className="observatory-key">{storyKey}</span><span className="observatory-heading-title">{storyTitle}</span></>}
            </h2>
            <div className="panel-actions observatory-actions">
              {canStartDelivery && <button type="button" className="button secondary" disabled={startBusy || loadingContent} onClick={openStartDelivery}><Play size={14} />{t("action.startDelivery")}</button>}
              <button type="button" className={`button primary${saving ? " is-busy" : ""}`} disabled={!dirty || saving || loadingContent} onClick={() => void save()}>{saving ? <LoaderCircle size={14} className="spin" /> : <Save size={14} />}{saving ? t("common.saving") : t("common.save")}</button>
            </div>
          </div>
          <div className="observatory-subheader">
            <StoryStatusMeta business={businessStatus || "draft"} technical={technicalStatus || "draft"} />
          </div>
        </div>
        {loadingContent ? <div className="loading-state"><LoaderCircle size={20} className="spin" /> {t("common.loading")} Story…</div> : <>
          <div className="observatory-doc-tabs" role="tablist">
            <button type="button" role="tab" aria-selected={docTab === "story"} className={docTab === "story" ? "active" : ""} onClick={() => setDocTab("story")}>{t("label.story")}</button>
            <button type="button" role="tab" aria-selected={docTab === "plan"} className={docTab === "plan" ? "active" : ""} onClick={() => setDocTab("plan")}>{t("label.technical")} plan</button>
          </div>
          {docTab === "story"
            ? <ObservatoryDocEditor key={`${selected || "none"}-story`} value={storyMarkdown} onChange={setStoryMarkdown} />
            : <ObservatoryDocEditor key={`${selected || "none"}-plan`} value={planMarkdown} onChange={setPlanMarkdown} />}
        </>}
      </>}
    </section>
    {startStep > 0 && <StartDeliveryDialog stories={deliveryOptions} value={selectedStartStory} onChange={setSelectedStartStory} step={startStep === 1 ? 1 : 2} busy={startBusy} error={startError} onClose={() => { if (!startBusy) setStartStep(0); }} onContinue={() => setStartStep(2)} onConfirm={() => void startDelivery()} />}
  </div>;
}

function StoryReference({ jiraKey, title }: { jiraKey: string; title?: string }) { const { t } = useI18n(); return <span className="story-reference">{title ? <><code>{text(jiraKey)}</code><span className="story-reference-title">{title}</span></> : <code>{text(jiraKey, t("common.noData"))}</code>}</span>; }
function DeliveryFlow({ stages, deliveryStatus, currentStep, startedAt, finishedAt, remediation, now, onStageClick }: { stages: RecordValue[]; deliveryStatus: string; currentStep?: string; startedAt?: string; finishedAt?: string; remediation?: RecordValue; now: number; onStageClick: (stage: RecordValue) => void }) {
  const { t } = useI18n();
  const terminalSuccess = /completed|dev_done|pr_open/i.test(deliveryStatus);
  const stopped = /stopped from dashboard/i.test(String(currentStep || ""));
  const retrying = remediation?.status === "in_progress";
  const retry = retrying ? `${remediation.attempt}/${remediation.max_attempts}` : "";
  const states = stages.map((stage) => { const rawStatus = String(stage.status || "pending").toLowerCase(); return terminalSuccess || rawStatus === "completed" ? "completed" : /running|progress/.test(rawStatus) ? "running" : stopped && /fail|block/.test(rawStatus) ? "stopped" : /fail|block/.test(rawStatus) ? "failed" : "pending"; });
  const progressUnits = states.reduce((total, state) => total + (state === "completed" ? 1 : state === "running" ? .5 : 0), 0);
  const progress = stages.length > 1 ? Math.max(0, Math.min(100, ((progressUnits - 1) / (stages.length - 1)) * 100)) : 100;
  return <div className="delivery-flow"><div className="flow-heading"><div><span className="flow-title">{t("nav.delivery")} Flow</span>{retrying && <strong className="remediation-alert"><RotateCcw size={13} />Verification failed · Remediation retry {retry}</strong>}</div><p>{startedAt ? t("label.startedAt", { value: when(startedAt) }) : t("label.notStarted")}{finishedAt ? ` · ${t("label.finishedAtValue", { value: when(finishedAt) })}` : ""}</p></div><div className="flow-track-wrap"><span className="flow-track"><i style={{ width: `${progress}%` }} /></span><ol className="flow-steps" style={{ "--flow-count": stages.length } as React.CSSProperties}>{stages.map((stage, index) => {
    const rawStatus = String(stage.status || "pending").toLowerCase();
    const state = terminalSuccess || rawStatus === "completed" ? "completed" : /running|progress/.test(rawStatus) ? "running" : stopped && /fail|block/.test(rawStatus) ? "stopped" : /fail|block/.test(rawStatus) ? "failed" : "pending";
    const duration = state === "running" ? elapsed(stage.active_started_at || stage.started_at, new Date(now).toISOString()) : stage.duration || "Pending";
    const attemptCount = Array.isArray(stage.attempts) && stage.attempts.length > 1 ? ` · ${stage.attempts.length} attempts` : "";
    const caption = state === "stopped" ? t("label.stopped") : retrying && state === "running" && ["implement", "verification"].includes(stage.id) ? `Retry ${retry} · ${duration}` : retrying && stage.id === "verification" && state === "failed" ? `Failed · remediation ${retry}` : state === "failed" ? t("label.needsAttentionState") : `${duration}${attemptCount}`;
    return <li className={`flow-step ${state}`} key={`${stage.label}-${index}`}><button className="flow-stage-button" onClick={() => onStageClick(stage)}><span className="flow-marker">{state === "completed" ? "✓" : state === "running" ? <span className="pulse-dot" /> : index + 1}</span><span className="flow-copy"><strong>{text(stage.label)}</strong><span>{caption}</span></span></button></li>;
  })}</ol></div></div>;
}

function DeliveryLogDialog({ stage, content, error, loading, live = false, onClose }: { stage: RecordValue; content: string; error: string; loading: boolean; live?: boolean; onClose: () => void }) { const { t } = useI18n(); const logRef = useRef<HTMLPreElement>(null); useEffect(() => { if (live && logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [content, live]); return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal delivery-log-modal" role="dialog" aria-modal="true" aria-label={`${stage.label} ${t("label.log")}`} onMouseDown={(event) => event.stopPropagation()}><div className="delivery-log-header"><div><span>{stage.label}</span><strong>{stage.duration || "—"}{live && <em className="live-log"><i />{t("common.live")}</em>}</strong><p>{stage.detail || t("label.noLog")}</p>{Array.isArray(stage.attempts) && stage.attempts.length > 0 && <small className="stage-attempts">{stage.attempts.map((attempt: RecordValue) => t("common.attempt", { number: attempt.number, duration: attempt.duration })).join(" · ")}</small>}</div><button className="button secondary" onClick={onClose}>{t("common.close")}</button></div><pre ref={logRef} className="delivery-log-content"><code>{loading && !content ? t("common.loading") : error || content}</code></pre></section></div>; }

function Fact({ label, value }: { label: string; value: React.ReactNode }) { return <div className="fact"><span>{label}</span><strong>{value}</strong></div>; }
function PrLinks({ items }: { items: RecordValue[] }) { const { t } = useI18n(); return items.length ? <span className="pr-links">{items.map((item, index) => <a href={item.url} target="_blank" rel="noreferrer" key={`${item.url}-${index}`}>{text(item.repository, t("action.pullRequest"))}{String(item.url || "").match(/\/(\d+)\/?$/) ? ` #${String(item.url).match(/\/(\d+)\/?$/)?.[1]}` : ""}<ExternalLink size={12} /></a>)}</span> : <>—</>; }
function VerificationSummary({ checks, onClick }: { checks: RecordValue[]; onClick: () => void }) { const { t } = useI18n(); const failed = checks.filter((item) => item.status === "failed").length; const passed = checks.filter((item) => item.status === "passed").length; return checks.length ? <button className={`check-summary ${failed ? "failed" : ""}`} title={t("label.verification")} onClick={onClick}>{failed ? t("label.checksFailed", { count: failed }) : t("label.checksPassed", { count: `${passed}/${checks.length}` })}</button> : <>—</>; }
function VerificationDialog({ checks, onClose }: { checks: RecordValue[]; onClose: () => void }) { const { t } = useI18n(); return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal verification-modal" role="dialog" aria-modal="true" aria-label={t("label.verification")} onMouseDown={(event) => event.stopPropagation()}><div className="delivery-log-header"><div><span>{t("label.verification")}</span><strong>{t("label.checksTitle")}</strong><p>{t("label.checksPassed", { count: checks.filter((item) => item.status === "passed").length })} · {t("label.checksFailed", { count: checks.filter((item) => item.status === "failed").length })} · {t("label.checksSkipped", { count: checks.filter((item) => item.status === "skipped").length })}</p></div><button className="button secondary" onClick={onClose}>{t("common.close")}</button></div><div className="verification-list">{checks.map((check, index) => <article className="verification-check" key={`${check.repository}-${check.id}-${index}`}><div><strong>{text(check.label)}</strong><span>{text(check.repository, t("common.workspace"))}</span></div><Badge value={check.status} /><p>{text(check.summary, t("label.noSummary"))}</p>{check.command && <code>{check.command}</code>}</article>)}</div></section></div>; }

const promptStageMeta: Record<string, { title: string; description: string; icon: typeof Workflow }> = {
  "01-role-and-mission.md": { title: "Mission", description: "Scope, role, and review posture", icon: Sparkles },
  "02-pipeline.md": { title: "Pipeline", description: "End-to-end scan sequence", icon: Workflow },
  "03-configuration.md": { title: "Configuration", description: "Workspace and runtime inputs", icon: Settings2 },
  "04-workspace-and-worktrees.md": { title: "Worktrees", description: "Repository isolation and refresh", icon: GitBranch },
  "05-review-only-mode.md": { title: "Review mode", description: "Lightweight validation boundaries", icon: ScanSearch },
  "06-issue-registry.md": { title: "Issue registry", description: "Finding persistence and status", icon: CircleAlert },
  "07-error-handling.md": { title: "Error handling", description: "Failure recording and recovery", icon: CircleDot },
  "08-github-pr-and-git.md": { title: "Git and PR", description: "Branch, commit, and PR controls", icon: GitBranch },
  "09-severity-guideline.md": { title: "Severity", description: "Finding classification policy", icon: CircleAlert },
  "10-findings-and-auto-fix.md": { title: "Findings", description: "Review output and safe fixes", icon: Code2 },
  "11-output-contract.md": { title: "Output", description: "Structured result contract", icon: FileCode2 },
  "12-secrets-and-safety.md": { title: "Safety", description: "Secret redaction and boundaries", icon: ShieldCheck },
  "13-console-summary.md": { title: "Summary", description: "Console and report output", icon: CircleCheck },
  "01-role.md": { title: "Delivery role", description: "Delivery agent scope", icon: Sparkles },
  "02-workspace.md": { title: "Context", description: "Story, docs, and workspace inputs", icon: GitBranch },
  "03-implementation.md": { title: "Implementation", description: "Code changes and verification", icon: Code2 },
  "04-output-contract.md": { title: "Outcome", description: "PR, JIRA, and result record", icon: CircleCheck },
  "03-jira-context.md": { title: "Jira context", description: "Primary, related, and keyword context", icon: Link2 },
  "04-repository-scope.md": { title: "Repository scope", description: "Registered repository and worktree rules", icon: GitBranch },
  "05-patch-implementation.md": { title: "Implementation", description: "Minimal Bug or copy change", icon: Code2 },
  "06-self-check.md": { title: "Self-check", description: "Focused validation evidence", icon: CircleCheck },
  "07-blocked-question.md": { title: "Blocked question", description: "One answerable human question", icon: CircleHelp },
  "08-git-and-publish.md": { title: "Git handoff", description: "Agent output and publish boundaries", icon: GitBranch },
  "09-output-contract.md": { title: "Output contract", description: "Structured patch result", icon: FileCode2 },
  "10-secrets-and-safety.md": { title: "Safety", description: "Secrets and change boundaries", icon: ShieldCheck },
  "11-console-summary.md": { title: "Summary", description: "Concise Agent handoff", icon: CircleCheck },
  "coding-guideline.md": { title: "Code standard", description: "Repository-level coding guidance", icon: FileCode2 }
};

function promptMeta(item: { path: string }) { return promptStageMeta[item.path] || { title: item.path.replace(/\.md$/, "").replace(/^\d+-/, ""), description: "Prompt fragment", icon: FileCode2 }; }
function promptLayer(item: { path: string }, mode: "scan" | "delivery" | "patch") {
  const path = item.path;
  if (mode === "delivery") {
    if (["01-role.md", "02-workspace.md", "coding-guideline.md"].includes(path)) return "Inputs & Governance";
    if (path === "03-implementation.md") return "Implementation";
    return "Delivery Outputs";
  }
  if (mode === "patch") {
    if (["01-role-and-mission.md", "03-jira-context.md", "04-repository-scope.md", "10-secrets-and-safety.md"].includes(path)) return "Inputs & Governance";
    if (["02-pipeline.md", "05-patch-implementation.md", "06-self-check.md"].includes(path)) return "Patch Execution";
    if (["07-blocked-question.md", "08-git-and-publish.md"].includes(path)) return "Operational Controls";
    return "Patch Outputs";
  }
  if (["01-role-and-mission.md", "03-configuration.md", "04-workspace-and-worktrees.md", "12-secrets-and-safety.md"].includes(path)) return "Inputs & Governance";
  if (["02-pipeline.md", "05-review-only-mode.md", "09-severity-guideline.md", "10-findings-and-auto-fix.md"].includes(path)) return "Review Execution";
  if (["06-issue-registry.md", "07-error-handling.md", "08-github-pr-and-git.md"].includes(path)) return "Operational Controls";
  return "Delivery Outputs";
}

type WorkflowColumn = {
  title: string;
  eyebrow: string;
  layers: string[];
  scripts: Array<{ name: string; description: string }>;
};

function workflowColumns(mode: "scan" | "delivery" | "patch"): WorkflowColumn[] {
  if (mode === "delivery") return [
    { title: "Trigger", eyebrow: "ENTRY", layers: [], scripts: [{ name: "delivery_scheduler.py", description: "Find an approved, eligible story" }, { name: "prepare_delivery_run.py", description: "Create the run record" }] },
    { title: "Context", eyebrow: "GROUNDING", layers: ["Inputs & Governance"], scripts: [{ name: "capture_jira_context.py", description: "Read story, comments, and media" }, { name: "compose_delivery_prompt.py", description: "Assemble the agent context" }] },
    { title: "Implement", eyebrow: "AGENT", layers: ["Implementation"], scripts: [{ name: "run-delivery.sh", description: "Execute in isolated worktrees" }] },
    { title: "Verify & recover", eyebrow: "CONTROL", layers: [], scripts: [{ name: "run_delivery_verification.py", description: "Compile, test, and inspect" }, { name: "prepare_delivery_remediation.py", description: "Prepare a bounded retry" }] },
    { title: "Publish", eyebrow: "OUTCOME", layers: ["Delivery Outputs"], scripts: [{ name: "finalize_delivery.py", description: "Commit, PR, JIRA, and notification" }] }
  ];
  if (mode === "patch") return [
    { title: "Capture", eyebrow: "ENTRY", layers: [], scripts: [{ name: "patch_scheduler.py", description: "Find one eligible Task or Bug" }] },
    { title: "Context", eyebrow: "GROUNDING", layers: ["Inputs & Governance"], scripts: [{ name: "capture_patch_context.py", description: "Read the Jira story neighborhood" }, { name: "compose_patch_prompt.py", description: "Assemble bounded patch context" }] },
    { title: "Patch", eyebrow: "AGENT", layers: ["Patch Execution"], scripts: [{ name: "run-patch.sh", description: "Run in an isolated patch worktree" }] },
    { title: "Control", eyebrow: "SAFETY", layers: ["Operational Controls"], scripts: [{ name: "finalize_patch.py", description: "Self-check, commit, and publish" }] },
    { title: "Outcome", eyebrow: "HANDOFF", layers: ["Patch Outputs"], scripts: [] }
  ];
  return [
    { title: "Trigger", eyebrow: "ENTRY", layers: [], scripts: [{ name: "run-scan.sh", description: "Start a scheduled or manual scan" }] },
    { title: "Context", eyebrow: "GROUNDING", layers: ["Inputs & Governance"], scripts: [{ name: "prepare_scan_worktrees.py", description: "Refresh isolated repository views" }, { name: "compose_scan_prompt.py", description: "Assemble review context" }] },
    { title: "Review", eyebrow: "AGENT", layers: ["Review Execution"], scripts: [] },
    { title: "Control & remediate", eyebrow: "CONTROL", layers: ["Operational Controls"], scripts: [{ name: "auto_fix_sync.py", description: "Apply and re-check safe fixes" }] },
    { title: "Report", eyebrow: "OUTCOME", layers: ["Delivery Outputs"], scripts: [{ name: "render-report-and-notify.py", description: "HTML, PDF, dashboard, and Feishu" }] }
  ];
}

function PromptsView({ data, project, interact, notify }: { data: DashboardData; project: string; interact: (path: string, json: RecordValue, message: string) => Promise<boolean>; notify: Notify }) {
  const { t } = useI18n();
  const prompts = data.interactive?.prompts || [];
  const [mode, setMode] = useState<"scan" | "delivery" | "patch">("scan");
  const [selected, setSelected] = useState<{ mode: "scan" | "delivery" | "patch"; path: string } | null>(null);
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [view, setView] = useState({ x: 0, y: 0, scale: 1 });
  const [fullscreen, setFullscreen] = useState(false);
  const pointer = useRef<{ id: number; x: number; y: number } | null>(null);
  const viewport = useRef<HTMLDivElement | null>(null);
  const modePrompts = prompts.filter((item) => item.mode === mode);
  const choose = async (item: { mode: "scan" | "delivery" | "patch"; path: string }) => {
    setSelected(item);
    try { const response = await request(`/api/prompt?mode=${encodeURIComponent(item.mode)}&path=${encodeURIComponent(item.path)}`, project); setContent(response.content); }
    catch (err) { notify(err instanceof Error ? err.message : "Unable to load prompt", "error"); }
  };
  const savePrompt = async () => {
    if (!selected || saving) return;
    setSaving(true);
    try { await interact("/api/prompt", { mode: selected.mode, path: selected.path, content }, "Prompt saved"); }
    finally { setSaving(false); }
  };
  const switchMode = (next: "scan" | "delivery" | "patch") => { setMode(next); setSelected(null); setContent(""); setView({ x: 0, y: 0, scale: 1 }); };
  useEffect(() => {
    if (!fullscreen) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setFullscreen(false); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [fullscreen]);
  const panOrZoom = useCallback((event: WheelEvent) => {
    event.preventDefault();
    if (event.ctrlKey || event.metaKey) setView((current) => ({ ...current, scale: Math.max(.65, Math.min(1.55, current.scale * (event.deltaY > 0 ? .975 : 1.025))) }));
    else setView((current) => ({ ...current, x: current.x - event.deltaX, y: current.y - event.deltaY }));
  }, []);
  useEffect(() => { const node = viewport.current; if (!node) return; node.addEventListener("wheel", panOrZoom, { passive: false }); return () => node.removeEventListener("wheel", panOrZoom); }, [panOrZoom]);
  const startPan = (event: React.PointerEvent<HTMLDivElement>) => {
    if ((event.target as HTMLElement).closest("button,a,textarea,input")) return;
    pointer.current = { id: event.pointerId, x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const movePan = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!pointer.current || pointer.current.id !== event.pointerId) return;
    const dx = event.clientX - pointer.current.x;
    const dy = event.clientY - pointer.current.y;
    pointer.current = { ...pointer.current, x: event.clientX, y: event.clientY };
    setView((current) => ({ ...current, x: current.x + dx, y: current.y + dy }));
  };
  const stopPan = (event: React.PointerEvent<HTMLDivElement>) => {
    if (pointer.current?.id === event.pointerId) pointer.current = null;
  };
  const columns = workflowColumns(mode);
  return <>
    <div className="workflow-mode-switch" role="tablist"><button className={mode === "scan" ? "active" : ""} onClick={() => switchMode("scan")}>{t("label.autoScan")}</button><button className={mode === "delivery" ? "active" : ""} onClick={() => switchMode("delivery")}>{t("label.autoDelivery")}</button><button className={mode === "patch" ? "active" : ""} onClick={() => switchMode("patch")}>{t("label.autoPatch")}</button></div>
    <Panel title={t("heading.workflow", { feature: mode === "scan" ? t("label.autoScan") : mode === "delivery" ? t("label.autoDelivery") : t("label.autoPatch") })} action={<IconButton label={fullscreen ? t("action.exitFullscreen") : t("action.viewFullscreen")} onClick={() => setFullscreen((value) => !value)}>{fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}</IconButton>} className={`workflow-panel ${fullscreen ? "workflow-panel-fullscreen" : ""}`}>
      <div ref={viewport} className="workflow-canvas workflow-viewport" onPointerDown={startPan} onPointerMove={movePan} onPointerUp={stopPan} onPointerCancel={stopPan}><div className="workflow-scale" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})` }}><div className="workflow-columns">{columns.map((column, columnIndex) => {
        const columnPrompts = modePrompts.filter((item) => column.layers.includes(promptLayer(item, mode)));
        const nodes = [...column.scripts.map((script) => ({ kind: "script" as const, script })), ...columnPrompts.map((prompt) => ({ kind: "prompt" as const, prompt }))];
        return <section className="workflow-column" key={column.title}><header><span>{column.eyebrow}</span><strong>{column.title}</strong></header><div className="workflow-node-stack">{nodes.map((node, nodeIndex) => {
          const sequence = `${columnIndex + 1}.${nodeIndex + 1}`;
          if (node.kind === "script") return <article className="workflow-node script-node" key={node.script.name}><Terminal size={14} /><span><strong>{node.script.name}</strong><small>{node.script.description}</small></span><em><b>{sequence}</b> SCRIPT</em></article>;
          const item = node.prompt;
          const meta = promptMeta(item);
          const Icon = meta.icon;
          const isSelected = selected?.mode === item.mode && selected.path === item.path;
          return <button className={`workflow-node prompt-node ${isSelected ? "selected" : ""}`} onClick={() => void choose(item)} key={`${item.mode}/${item.path}`}><Icon size={14} /><span><strong>{meta.title}</strong><small>{meta.description}</small></span><em><b>{sequence}</b> PROMPT</em></button>;
        })}</div>{columnIndex < columns.length - 1 && <span className="workflow-connector" aria-hidden="true" />}</section>;
      })}</div><div className="workflow-retry"><RotateCcw size={14} /><span><strong>{mode === "delivery" ? "Remediation retry" : mode === "patch" ? "Blocked-question retry" : "Safe-fix re-review"}</strong><small>{mode === "delivery" ? "Verification failure → prepare_delivery_remediation.py → implementation agent → verification" : mode === "patch" ? "External Jira reply → capture context → rerun the complete patch flow" : "High-confidence finding → auto_fix_sync.py → focused validation → pull request"}</small></span></div></div></div>
    </Panel>
    {selected && <PromptInspectorDialog item={selected} content={content} saving={saving} onChange={setContent} onClose={() => { if (!saving) { setSelected(null); setContent(""); } }} onSave={() => void savePrompt()} />}
  </>;
}

function PromptInspectorDialog({ item, content, saving, onChange, onClose, onSave }: { item: { mode: "scan" | "delivery" | "patch"; path: string }; content: string; saving: boolean; onChange: (value: string) => void; onClose: () => void; onSave: () => void }) {
  const { t } = useI18n();
  const meta = promptMeta(item);
  const feature = item.mode === "scan" ? t("label.autoScan") : item.mode === "delivery" ? t("label.autoDelivery") : t("label.autoPatch");
  return <div className="modal-backdrop" role="presentation" onMouseDown={saving ? undefined : onClose}><section className="modal prompt-inspector-modal" role="dialog" aria-modal="true" aria-label={`${meta.title} prompt`} onMouseDown={(event) => event.stopPropagation()}><div className="prompt-inspector-header"><div><span>{feature} {t("label.prompt")}</span><strong>{meta.title}</strong><code>{item.path}</code></div><button className="button secondary" disabled={saving} onClick={onClose}>{t("common.close")}</button></div><div className="prompt-inspector-body"><div className="markdown-workbench"><label className="markdown-pane"><span>{t("prompt.original")}</span><textarea value={content} onChange={(event) => onChange(event.target.value)} spellCheck={false} disabled={saving} /></label><article className="markdown-preview"><span>{t("prompt.preview")}</span><MarkdownBody content={content} /></article></div></div><footer><button className="button" disabled={saving} onClick={onClose}>{t("common.cancel")}</button><button className={`button primary${saving ? " is-busy" : ""}`} disabled={saving} onClick={onSave}>{saving ? <LoaderCircle size={14} className="spin" /> : <Save size={14} />}{saving ? t("common.saving") : t("action.savePrompt")}</button></footer></section></div>;
}

function HelpTip({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  return <details className="field-help"><summary aria-label={t("common.explainSetting")}><CircleHelp size={13} /></summary><span role="tooltip">{children}</span></details>;
}

function Field({ label, help, children }: { label: string; help?: React.ReactNode; children: React.ReactNode }) {
  return <label className="field"><span className="field-label">{label}{help && <HelpTip>{help}</HelpTip>}</span>{children}</label>;
}

function StatusMultiSelect({ options, value, onChange, markDirty }: { options: string[]; value: string[]; onChange: (value: string[]) => void; markDirty: () => void }) {
  const { t } = useI18n();
  const picker = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const close = (event: PointerEvent) => { if (!picker.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", close); document.removeEventListener("keydown", escape); };
  }, []);
  const toggle = (status: string) => {
    onChange(value.includes(status) ? value.filter((item) => item !== status) : [...value, status]);
    markDirty();
  };
  const summary = value.length === 0 ? t("label.eligibleStatuses") : value.length === 1 ? value[0] : t("common.statusesSelected", { count: value.length });
  return <div ref={picker} className={`status-picker ${open ? "is-open" : ""}`}>
    <button type="button" className="status-picker-trigger" aria-label={t("label.eligibleStatuses")} aria-expanded={open} onClick={() => setOpen((current) => !current)}>
      <span className={`status-picker-summary ${value.length === 0 ? "placeholder" : ""}`} title={value.join(", ")}>{summary}</span><ChevronDown size={15} aria-hidden="true" />
    </button>
    {open && <div className="status-picker-menu" role="listbox" aria-label={t("label.eligibleStatuses")} aria-multiselectable="true">
      <div className="status-picker-options">{options.map((status) => { const selected = value.includes(status); return <button type="button" role="option" aria-selected={selected} className={`status-picker-option ${selected ? "selected" : ""}`} key={status} onClick={() => toggle(status)}><span className="status-picker-check" aria-hidden="true">{selected ? "✓" : ""}</span><span>{status}</span></button>; })}</div>
      <footer className="status-picker-footer"><span>{t("common.selected", { count: value.length })}</span>{value.length > 0 && <button type="button" onClick={() => { onChange([]); markDirty(); }}>{t("common.clear")}</button>}</footer>
    </div>}
  </div>;
}

function ModelField({ label, value, provider = "cursor_cli", onChange, markDirty }: { label: string; value: string; provider?: string; onChange: (value: string) => void; markDirty: () => void }) {
  const { t } = useI18n();
  const normalizedValue = trimmedModelValue(value);
  const options = provider === "codex" ? codexModelOptions : provider === "opencode" || provider === "deepseek" || provider === "deepseek_api" ? opencodeModelOptions : cursorModelOptions;
  const isPreset = options.some((model) => model.value === normalizedValue);
  const customModelLabel = normalizedValue || t("customModel.option");
  const [customOpen, setCustomOpen] = useState(false);
  const openCustom = () => setCustomOpen(true);
  return <Field label={label} help={t("customModel.help")}>
    <div className={`model-select-row${isPreset ? "" : " is-custom"}`}>
      <select title={!isPreset ? normalizedValue : undefined} value={isPreset ? normalizedValue : customModelOption} onChange={(event) => { if (event.target.value === customModelOption) openCustom(); else { onChange(event.target.value); markDirty(); } }}>
        {options.map((model) => <option value={model.value} key={model.value}>{model.label}</option>)}
        <option value={customModelOption}>{isPreset ? t("customModel.option") : customModelLabel}</option>
      </select>
      {!isPreset && <span className="custom-model-badge">{t("customModel.badge")}</span>}
    </div>
    {!isPreset && <button type="button" className="custom-model-edit" onClick={openCustom}>{t("customModel.edit")}</button>}
    {customOpen && <CustomModelDialog label={label} value={value} onClose={() => setCustomOpen(false)} onConfirm={(model) => { onChange(model); markDirty(); setCustomOpen(false); }} />}
  </Field>;
}

function WorkflowModelField({ label, provider, model, baseUrl, apiKeyEnv, reasoningEffort, accountEmail, onProviderChange, onModelChange, onBaseUrlChange, onApiKeyEnvChange, onReasoningEffortChange, onAccountEmailChange, markDirty }: { label: string; provider: string; model: string; baseUrl: string; apiKeyEnv: string; reasoningEffort: string; accountEmail: string; onProviderChange: (value: string) => void; onModelChange: (value: string) => void; onBaseUrlChange: (value: string) => void; onApiKeyEnvChange: (value: string) => void; onReasoningEffortChange: (value: string) => void; onAccountEmailChange: (value: string) => void; markDirty: () => void }) {
  const { t } = useI18n();
  const selectProvider = (value: string) => {
    onProviderChange(value);
    onModelChange(value === "codex" ? "gpt-5.6-luna" : value === "opencode" ? "deepseek-v4-flash" : value === "cursor_cli" ? "cursor-grok-4.5-medium" : value === "openai_compatible" ? "gpt-4o-mini" : model);
    if (value === "codex") {
      onBaseUrlChange("");
      onApiKeyEnvChange("");
    }
    onReasoningEffortChange(value === "codex" ? "xhigh" : "");
    onAccountEmailChange(value === "codex" ? codexAccountEmail : "");
    markDirty();
  };
  return <div className="workflow-model-editor">
    <div className="workflow-model-editor-heading"><strong>{label}</strong><span>{t("settings.workflowRuntimeLabel")}</span></div>
    <div className="form-grid compact workflow-model-editor-fields">
      <Field label={t("label.modelProvider")}><select value={provider} onChange={(event) => selectProvider(event.target.value)}><option value="codex">Codex</option><option value="opencode">OpenCode</option><option value="cursor_cli">Cursor CLI</option><option value="openai_compatible">OpenAI-compatible API</option></select></Field>
      <ModelField label={t("label.cursorModel")} provider={provider} value={model} onChange={onModelChange} markDirty={markDirty} />
      {provider === "codex" && <><Field label={t("settings.reasoningEffort")}><select value={reasoningEffort || "xhigh"} onChange={(event) => { onReasoningEffortChange(event.target.value); markDirty(); }}>{codexReasoningEffortOptions.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}</select></Field><div className="workflow-harness-note"><strong>{t("settings.codexHarness")}</strong><span>{t("settings.codexHarnessDescription")}</span><code>{accountEmail || codexAccountEmail}</code></div></>}
      {(provider === "openai_compatible" || provider === "openai") && <><Field label={t("label.apiBaseUrl")}><input value={baseUrl} placeholder="https://api.example.com/v1" onChange={(event) => { onBaseUrlChange(event.target.value); markDirty(); }} /></Field><Field label={t("label.apiKeyEnv")}><input value={apiKeyEnv} placeholder="OPENAI_API_KEY" onChange={(event) => { onApiKeyEnvChange(event.target.value); markDirty(); }} /></Field></>}
      {provider === "opencode" && <div className="workflow-harness-note"><strong>{t("settings.openCodeHarness")}</strong><span>{t("settings.openCodeHarnessDescription")}</span><code>{apiKeyEnv || "local model (no key)"}</code></div>}
    </div>
  </div>;
}

function CustomModelDialog({ label, value, onClose, onConfirm }: { label: string; value: string; onClose: () => void; onConfirm: (value: string) => void }) {
  const { t } = useI18n();
  const [draft, setDraft] = useState(value);
  const confirm = () => { const model = draft.trim(); if (model) onConfirm(model); };
  useEffect(() => { const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); }; window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown); }, [onClose]);
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal custom-model-modal" role="dialog" aria-modal="true" aria-labelledby="custom-model-title" onMouseDown={(event) => event.stopPropagation()}><div className="custom-model-header"><strong id="custom-model-title">{t("customModel.enter")}</strong><p>{label} · {t("customModel.help")}</p></div><div className="modal-body compact"><Field label={t("customModel.id")}><input autoFocus value={draft} placeholder={t("customModel.placeholder")} aria-label={t("customModel.id")} onChange={(event) => setDraft(event.target.value)} /></Field><p className="modal-copy">{t("customModel.copy")}</p></div><footer><button type="button" className="button" onClick={onClose}>{t("common.cancel")}</button><button type="button" className="button primary" disabled={!draft.trim()} onClick={confirm}>{t("common.confirm")}</button></footer></section></div>;
}

function RepositoryView({ data, interact }: { data: DashboardData; interact: (path: string, json: RecordValue, message: string) => Promise<boolean> }) {
  const { t } = useI18n();
  const workspace = data.interactive?.workspace || {};
  const [repositories, setRepositories] = useState<RecordValue[]>(workspace.repositories || []);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [filter, setFilter] = useState<"all" | "attention" | "patch">("all");
  useEffect(() => { if (!dirty) setRepositories(workspace.repositories || []); }, [workspace.repositories, dirty]);
  const update = (index: number, patch: RecordValue) => { setDirty(true); setRepositories((items) => items.map((item, current) => current === index ? { ...item, ...patch } : item)); };
  const commandsFor = (repository: RecordValue) => (repository.delivery_steps || []).map((step: RecordValue) => Array.isArray(step.command) ? step.command.join(" ") : "").filter(Boolean).join("\n");
  const verificationFor = (repository: RecordValue) => {
    const configured = repository.verification && typeof repository.verification === "object" ? repository.verification : {};
    const mode = ["auto", "custom", "skip"].includes(String(configured.mode || ""))
      ? String(configured.mode)
      : commandsFor(repository) ? "custom" : "auto";
    return { mode, compile: configured.compile !== false, tests: configured.tests !== false };
  };
  const automationFor = (repository: RecordValue) => ({ scan: { allow_auto_fix: repository.automation?.scan?.allow_auto_fix ?? repository.allow_auto_fix !== false }, delivery: { enabled: repository.automation?.delivery?.enabled !== false }, patch: { enabled: repository.automation?.patch?.enabled ?? true } });
  const updateAutomation = (index: number, section: "scan" | "delivery" | "patch", patch: RecordValue) => { setDirty(true); setRepositories((items) => items.map((item, current) => current === index ? { ...item, automation: { ...automationFor(item), [section]: { ...automationFor(item)[section], ...patch } } } : item)); };
  const updateVerification = (index: number, patch: RecordValue) => { setDirty(true); setRepositories((items) => items.map((item, current) => current === index ? { ...item, verification: { ...verificationFor(item), ...patch } } : item)); };
  const saveGovernance = async () => {
    if (!dirty || saving) return;
    setSaving(true);
    try {
      if (await interact("/api/repositories", { repositories }, "Repository governance saved")) {
        setDirty(false);
        setEditing(null);
      }
    }
    finally { setSaving(false); }
  };
  const attentionReasons = (repository: RecordValue) => {
    const health = repository.health || {};
    const reasons: string[] = [];
    if (health.git_status === "changes") reasons.push("Uncommitted changes");
    if (health.git_status === "behind") reasons.push("Branch behind remote");
    if (health.git_status === "diverged") reasons.push("Branch diverged");
    if (health.sync_status === "behind") reasons.push("Sync behind remote");
    if (health.sync_status === "diverged") reasons.push("Sync diverged");
    return Array.from(new Set(reasons));
  };
  const runtimeSummary = (health: RecordValue) => {
    const runtime = health.java_version ? `Java ${health.java_version}` : health.node_version ? `Node.js ${health.node_version}` : health.language || "Generic";
    const buildTools = health.build_tools?.join(", ") || "No build tool detected";
    return `${runtime} · ${buildTools}`;
  };
  const repositoryValue = (value: unknown) => { const display = text(value, t("status.notSet")); return <span className="repository-fact-value" data-tooltip={display} title={display} tabIndex={0} aria-label={display}><code>{display}</code></span>; };
  const attention = repositories.filter((repository) => attentionReasons(repository).length > 0).length;
  const scanEnabled = repositories.filter((repository) => automationFor(repository).scan.allow_auto_fix).length;
  const deliveryEnabled = repositories.filter((repository) => automationFor(repository).delivery.enabled).length;
  const patchEnabled = repositories.filter((repository) => automationFor(repository).patch.enabled).length;
  const visible = repositories.filter((repository) => filter === "all" || filter === "patch" && automationFor(repository).patch.enabled || filter === "attention" && attentionReasons(repository).length > 0);
  const selectedRepository = editing ? repositories.find((repository) => repository.name === editing) : null;
  const selectedIndex = selectedRepository ? repositories.indexOf(selectedRepository) : -1;
  const selectedHealth = selectedRepository?.health || {};
  const selectedAutomation = selectedRepository ? automationFor(selectedRepository) : null;
  const selectedVerification = selectedRepository ? verificationFor(selectedRepository) : null;
  return <div className="repository-page">
    <Panel title={t("common.repositoryGovernance")} action={<button className="button secondary" onClick={() => setAddOpen(true)}>{t("common.addRepository")}</button>}>
      <div className="repository-intro">{t("common.repositoryIntro")}</div>
      <div className="repository-overview"><Fact label={t("common.all")} value={repositories.length} /><Fact label={t("label.needsAttention")} value={attention} /><Fact label={t("label.autoScan")} value={`${scanEnabled}/${repositories.length} ${t("common.enabled")}`} /><Fact label={t("label.autoDelivery")} value={`${deliveryEnabled}/${repositories.length} ${t("common.enabled")}`} /><Fact label={t("label.autoPatch")} value={`${patchEnabled}/${repositories.length} ${t("common.enabled")}`} /></div>
      <div className="repository-filters"><button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>{t("common.all")} ({repositories.length})</button><button className={filter === "attention" ? "active" : ""} onClick={() => setFilter("attention")}>{t("label.needsAttention")} ({attention})</button><button className={filter === "patch" ? "active" : ""} onClick={() => setFilter("patch")}>{t("label.autoPatch")} {t("common.enabled")} ({patchEnabled})</button></div>
      {filter === "attention" && <div className="repository-filter-note"><CircleAlert size={14} aria-hidden="true" /><span>{t("common.attentionNote")}</span></div>}
      <div className="repository-list"><div className="repository-grid">{visible.map((repository) => {
        const health = repository.health || {};
        const automation = automationFor(repository);
        return <article className="repository-card" key={repository.name}>
          <button type="button" className="repository-card-button" onClick={() => setEditing(repository.name)} aria-label={`Edit ${repository.name || "repository"}`}>
            <div className="repository-card-heading"><div><strong>{repository.name || "Unnamed repository"}</strong><span>{runtimeSummary(health)}</span></div><ChevronRight size={16} aria-hidden="true" /></div>
            <div className="repository-card-bottom"><div className="repository-card-permissions"><span className={automation.scan.allow_auto_fix ? "enabled" : "disabled"}>Auto Scan {automation.scan.allow_auto_fix ? "enabled" : "disabled"}</span><span className={automation.delivery.enabled ? "enabled" : "disabled"}>Auto Delivery {automation.delivery.enabled ? "enabled" : "disabled"}</span><span className={automation.patch.enabled ? "enabled" : "disabled"}>Auto Patch {automation.patch.enabled ? "enabled" : "disabled"}</span></div><span className="repository-card-branch"><GitBranch size={12} aria-hidden="true" />{repository.default_branch || "main"}</span></div>
          </button>
        </article>;
      })}{visible.length === 0 && <Empty label={t("common.noData")} />}</div></div>
    </Panel>
    {selectedRepository && selectedIndex >= 0 && selectedAutomation && selectedVerification && <div className="modal-backdrop repository-config-backdrop" role="presentation" onMouseDown={() => setEditing(null)}><section className="modal repository-config-modal" role="dialog" aria-modal="true" aria-labelledby="repository-config-title" onMouseDown={(event) => event.stopPropagation()}>
      <header className="repository-config-header"><div><strong id="repository-config-title">{selectedRepository.name || t("common.unnamedRepository")}</strong><span>{t("common.repositoryConfiguration")}</span><p>{selectedHealth.language || t("common.generic")} · {selectedHealth.build_tools?.join(", ") || t("common.noBuildTool")} · {selectedRepository.default_branch || "main"}</p></div><IconButton label={t("common.close")} onClick={() => setEditing(null)}><X size={15} /></IconButton></header>
      <div className="repository-config-body"><div className="repository-editor">
        <section className="repository-section"><div><strong>{t("common.identityConnection")}</strong><span>{t("common.identityConnectionHelp")}</span></div><div className="repository-facts"><Fact label={t("common.localPath")} value={repositoryValue(selectedRepository.path)} /><Fact label={t("common.remote")} value={repositoryValue(selectedHealth.remote_url || selectedRepository.remote_url)} /><Fact label={t("common.gitStatus")} value={<Badge value={selectedHealth.git_status || "unknown"} />} /><Fact label={t("common.branchSync")} value={<Badge value={selectedHealth.sync_status || "unknown"} />} /></div><div className="form-grid compact"><Field label={t("common.defaultBranch")}><select value={selectedRepository.default_branch || ""} onChange={(event) => update(selectedIndex, { default_branch: event.target.value })}>{Array.from(new Set([selectedRepository.default_branch, ...(selectedRepository.branches || [])].filter(Boolean))).map((branch) => <option value={branch} key={branch}>{branch}</option>)}</select></Field></div></section>
        <section className="repository-section"><div><strong>{t("common.runtimeBuild")}</strong><span>{t("common.runtimeBuildHelp")}</span></div><div className="repository-facts"><Fact label={t("common.language")} value={selectedHealth.language || "Generic"} /><Fact label={t("common.java")} value={selectedHealth.java_version ? `Java ${selectedHealth.java_version}` : "Not detected"} /><Fact label={t("common.node")} value={selectedHealth.node_version ? `Node ${selectedHealth.node_version}` : "Not detected"} /><Fact label={t("common.buildTools")} value={selectedHealth.build_tools?.join(", ") || "Not detected"} /></div></section>
        <section className="repository-section"><div><strong>{t("common.automationPermissions")}</strong><span>{t("common.frontendDeliveryDisabled")}</span></div><div className="repository-policy-grid"><label><input type="checkbox" checked={selectedAutomation.scan.allow_auto_fix} onChange={(event) => updateAutomation(selectedIndex, "scan", { allow_auto_fix: event.target.checked })} /><span><strong>{t("common.autoScanFixes")}</strong><small>{t("common.autoScanFixesHelp")}</small></span></label><label><input type="checkbox" checked={selectedAutomation.delivery.enabled} onChange={(event) => updateAutomation(selectedIndex, "delivery", { enabled: event.target.checked })} /><span><strong>{t("common.deliveryPermission")}</strong><small>{t("common.deliveryPermissionHelp")}</small></span></label><label><input type="checkbox" checked={selectedAutomation.patch.enabled} onChange={(event) => updateAutomation(selectedIndex, "patch", { enabled: event.target.checked })} /><span><strong>{t("common.patchPermission")}</strong><small>{t("common.patchPermissionHelp")}</small></span></label></div></section>
        <section className="repository-section repository-verification-section"><div className="repository-section-heading"><strong>{t("common.deliveryVerification")}</strong><span>{t("common.deliveryVerificationHelp")}</span></div><div className="verification-group"><span className="verification-group-label">{t("common.policy")}</span><div className="verification-mode-grid"><label className={`verification-mode-card${selectedVerification.mode !== "skip" ? " selected" : ""}`}><input type="radio" name={`verification-mode-${selectedRepository.name}`} checked={selectedVerification.mode !== "skip"} onChange={() => updateVerification(selectedIndex, { mode: selectedVerification.mode === "custom" ? "custom" : "auto" })} /><span><strong>{t("common.runVerification")}</strong><small>{t("common.runVerificationHelp")}</small></span></label><label className={`verification-mode-card${selectedVerification.mode === "skip" ? " selected" : ""}`}><input type="radio" name={`verification-mode-${selectedRepository.name}`} checked={selectedVerification.mode === "skip"} onChange={() => updateVerification(selectedIndex, { mode: "skip" })} /><span><strong>{t("common.skipVerification")}</strong><small>{t("common.skipVerificationHelp")}</small></span></label></div></div>{selectedVerification.mode !== "skip" && <><div className="verification-group"><span className="verification-group-label">{t("common.executionSource")}</span><div className="verification-source-toggle"><label><input type="radio" name={`verification-source-${selectedRepository.name}`} checked={selectedVerification.mode === "auto"} onChange={() => updateVerification(selectedIndex, { mode: "auto" })} /><span><strong>{t("common.automaticProfile")}</strong><small>{t("common.automaticProfileHelp")}</small></span></label><label><input type="radio" name={`verification-source-${selectedRepository.name}`} checked={selectedVerification.mode === "custom"} onChange={() => updateVerification(selectedIndex, { mode: "custom" })} /><span><strong>{t("common.customCommands")}</strong><small>{t("common.customCommandsHelp")}</small></span></label></div></div>{selectedVerification.mode === "auto" ? <div className="verification-group"><span className="verification-group-label">{t("common.checksToRun")}</span><div className="verification-check-grid"><label><input type="checkbox" checked={selectedVerification.compile} onChange={(event) => updateVerification(selectedIndex, { compile: event.target.checked })} /><span><strong>{t("common.compileChecks")}</strong><small>{t("common.compileChecksHelp")}</small></span></label><label><input type="checkbox" checked={selectedVerification.tests} onChange={(event) => updateVerification(selectedIndex, { tests: event.target.checked })} /><span><strong>{t("common.tests")}</strong><small>{t("common.testsHelp")}</small></span></label></div></div> : <div className="verification-group"><span className="verification-group-label">{t("common.commands")}</span><div className="verification-command-editor">{selectedHealth.suggested_commands?.length > 0 && <button type="button" className="text-button verification-suggested-button" onClick={() => update(selectedIndex, { delivery_commands: selectedHealth.suggested_commands.join("\n") })}>{t("common.useSuggestedCommands", { count: selectedHealth.suggested_commands.length, suffix: currentDashboardLocale === "en" && selectedHealth.suggested_commands.length === 1 ? "" : currentDashboardLocale === "en" ? "s" : "" })}</button>}<label className="field repository-commands"><textarea value={selectedRepository.delivery_commands ?? commandsFor(selectedRepository)} rows={4} placeholder={t("common.oneCommandPerLine")} onChange={(event) => update(selectedIndex, { delivery_commands: event.target.value })} /></label></div></div>}</>}</section>
      </div></div><footer className="repository-config-footer"><div className="repository-config-actions"><button type="button" className="button" disabled={saving} onClick={() => setEditing(null)}>{t("common.close")}</button><button type="button" className={`button primary${saving ? " is-busy" : ""}`} disabled={!dirty || saving} onClick={() => void saveGovernance()}>{saving ? <LoaderCircle size={15} className="spin" /> : <Save size={15} />}{saving ? t("common.saving") : t("common.save")}</button></div></footer>
    </section></div>}
    {addOpen && <AddRepositoryDialog onClose={() => setAddOpen(false)} onAdd={(url) => { void interact("/api/repositories/clone", { url }, "Repository cloned and registered"); setAddOpen(false); }} />}
  </div>;
}

function AddRepositoryDialog({ onClose, onAdd }: { onClose: () => void; onAdd: (url: string) => void }) {
  const { t } = useI18n();
  const [url, setUrl] = useState("");
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal repository-modal" role="dialog" aria-modal="true" aria-label={t("common.addRepository")} onMouseDown={(event) => event.stopPropagation()}><div className="prompt-inspector-header"><div><strong>{t("common.addRepository")}</strong><span className="repository-modal-description">{t("common.addRepositoryDescription")}</span></div></div><div className="repository-modal-body"><Field label={t("common.cloneUrl")}><input autoFocus value={url} placeholder="https://git.example.com/team/service.git" onChange={(event) => setUrl(event.target.value)} /></Field></div><footer><button className="button" onClick={onClose}>{t("common.cancel")}</button><button className="button primary" disabled={!url.trim()} onClick={() => onAdd(url.trim())}>{t("common.cloneInspect")}</button></footer></section></div>;
}

function SettingsView({ data, project, notify, onDirtyChange, reload }: { data: DashboardData; project: string; notify: Notify; onDirtyChange: (dirty: boolean) => void; reload: () => Promise<void> }) {
  const { t } = useI18n();
  const workspace = data.interactive?.workspace || {};
  const schedules = data.interactive?.schedules || {};
  const agentsPayload = data.interactive?.agents || {};
  const runtimeStatus = workspace.runtime && typeof workspace.runtime === "object" ? workspace.runtime : {};
  const harnessProbe = runtimeStatus.harness_probe && typeof runtimeStatus.harness_probe === "object"
    ? runtimeStatus.harness_probe
    : workspace.harness && typeof workspace.harness === "object" ? workspace.harness : {};
  const harnessCapabilities = harnessProbe.capabilities && typeof harnessProbe.capabilities === "object" ? harnessProbe.capabilities : {};
  const enabledHarnessCapabilities = Object.entries(harnessCapabilities).filter(([, enabled]) => Boolean(enabled)).map(([name]) => name).join(" · ");
  const harnessSecurity = harnessProbe.security && typeof harnessProbe.security === "object" ? harnessProbe.security : {};
  const harnessSecuritySummary = Object.entries(harnessSecurity).map(([name, violated]) => `${name}:${violated ? "fail" : "ok"}`).join(" · ");
  const [scanWindow, setScanWindow] = useState(String(workspace.scan_window_days || 7));
  const [scanCron, setScanCron] = useState(String(schedules.scan?.cron || "0 12 * * 1-5"));
  const [scanEnabled, setScanEnabled] = useState(Boolean(schedules.scan));
  const [deliveryInterval, setDeliveryInterval] = useState(String(Math.round((schedules.delivery?.interval_seconds || 300) / 60)));
  const [eligibleStatuses, setEligibleStatuses] = useState<string[]>(Array.isArray(schedules.delivery?.jira_statuses) ? schedules.delivery.jira_statuses.map(String) : String(schedules.delivery?.jira_status || "To Do,Backlog,In Progress").split(",").map((value) => value.trim()).filter(Boolean));
  const [inDevStatus, setInDevStatus] = useState(String(schedules.delivery?.in_dev_status || ""));
  const [devDoneStatus, setDevDoneStatus] = useState(String(schedules.delivery?.dev_done_status || ""));
  const [blockedStatus, setBlockedStatus] = useState(String(schedules.delivery?.blocked_status || "Block"));
  const [deliveryEnabled, setDeliveryEnabled] = useState(Boolean(schedules.delivery?.enabled));
  const [patchInterval, setPatchInterval] = useState(String(Math.round((schedules.patch?.interval_seconds || 300) / 60)));
  const [patchStatuses, setPatchStatuses] = useState<string[]>(Array.isArray(schedules.patch?.jira_statuses) ? schedules.patch.jira_statuses.map(String) : ["To Do"]);
  const [patchStartStatus, setPatchStartStatus] = useState(String(schedules.patch?.in_progress_status || "In Progress"));
  const [patchDoneStatus, setPatchDoneStatus] = useState(String(schedules.patch?.done_status || "Done"));
  const [patchBlockedStatus, setPatchBlockedStatus] = useState(String(schedules.patch?.blocked_status || "Block"));
  const [patchEnabled, setPatchEnabled] = useState(Boolean(schedules.patch?.enabled));
  const globalWorkflow = workflowModelConfig(workspace, "scan");
  const [globalProvider, setGlobalProvider] = useState(globalWorkflow.provider);
  const [globalModel, setGlobalModel] = useState(globalWorkflow.model);
  const [globalBaseUrl, setGlobalBaseUrl] = useState(globalWorkflow.base_url);
  const [globalApiKeyEnv, setGlobalApiKeyEnv] = useState(globalWorkflow.api_key_env);
  const [globalReasoningEffort, setGlobalReasoningEffort] = useState(globalWorkflow.reasoning_effort);
  const [globalAccountEmail, setGlobalAccountEmail] = useState(globalWorkflow.account_email);
  const [workflowStatuses, setWorkflowStatuses] = useState<string[]>([]);
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [changedSecrets, setChangedSecrets] = useState<Record<string, string>>({});
  const [scanPublishMode, setScanPublishMode] = useState(String(workspace.publish?.scan || "pr"));
  const [deliveryPublishMode, setDeliveryPublishMode] = useState(String(workspace.publish?.delivery || "pr"));
  const [patchPublishMode, setPatchPublishMode] = useState(String(workspace.publish?.patch || "pr"));
  const [feishuEnabled, setFeishuEnabled] = useState(workspace.feishu_notifications_enabled !== false);
  const [deploymentEnabled, setDeploymentEnabled] = useState(Boolean(workspace.deployment_tracking?.enabled));
  const [deploymentProvider, setDeploymentProvider] = useState(String(workspace.deployment_tracking?.provider || "none"));
  const [deploymentPollInterval, setDeploymentPollInterval] = useState(String(workspace.deployment_tracking?.poll_interval_seconds || 30));
  const [deploymentTimeout, setDeploymentTimeout] = useState(String(workspace.deployment_tracking?.timeout_seconds || 3600));
  const [jenkinsJob, setJenkinsJob] = useState(String(workspace.deployment_tracking?.jenkins?.job || ""));
  const [githubRepository, setGithubRepository] = useState(String(workspace.deployment_tracking?.github_actions?.repository || ""));
  const [githubWorkflow, setGithubWorkflow] = useState(String(workspace.deployment_tracking?.github_actions?.workflow || ""));
  const [agentsEnabled, setAgentsEnabled] = useState(Boolean(agentsPayload.enabled));
  const [defaultLanguage, setDefaultLanguage] = useState(agentsPayload.conversation?.default_language || "zh-Hant");
  const [agentDrafts, setAgentDrafts] = useState<AgentSettings[]>(Array.isArray(agentsPayload.agents) ? agentsPayload.agents.map((agent) => ({ ...agent })) : []);
  const [accessDraft, setAccessDraft] = useState<AgentsAccessSettings>({
    allowed_chat_ids: agentsPayload.access?.allowed_chat_ids || [],
    allowed_user_ids: agentsPayload.access?.allowed_user_ids || [],
    mutation_allowed_user_ids: agentsPayload.access?.mutation_allowed_user_ids || [],
    admin_user_ids: agentsPayload.access?.admin_user_ids || [],
    legacy_warning: Boolean(agentsPayload.access?.legacy_warning),
    default_policy: agentsPayload.access?.default_policy || "deny",
  });
  const [recentFeishu, setRecentFeishu] = useState({
    user_ids: agentsPayload.recent_feishu?.private_user_ids || agentsPayload.recent_feishu?.user_ids || [],
    chat_ids: agentsPayload.recent_feishu?.group_chat_ids || agentsPayload.recent_feishu?.chat_ids || [],
    direct_chat_ids: agentsPayload.recent_feishu?.direct_chat_ids || [],
    users: agentsPayload.recent_feishu?.private_users || agentsPayload.recent_feishu?.users || [],
    chats: agentsPayload.recent_feishu?.group_chats || agentsPayload.recent_feishu?.chats || [],
    names: agentsPayload.recent_feishu?.names || {},
  });
  const [selectedPersonId, setSelectedPersonId] = useState("");
  const [agentsBaseline, setAgentsBaseline] = useState({
    enabled: Boolean(agentsPayload.enabled),
    defaultLanguage: agentsPayload.conversation?.default_language || "zh-Hant",
    agents: Array.isArray(agentsPayload.agents) ? JSON.stringify(agentsPayload.agents) : "[]",
    access: JSON.stringify(agentsPayload.access || {}),
    testCase: JSON.stringify(agentsPayload.test_case || {}),
  });
  const [testCaseDraft, setTestCaseDraft] = useState<TestCaseSettings>({
    language: agentsPayload.test_case?.language || "zh-Hant",
    table_name: agentsPayload.test_case?.table_name || "Sheet1",
    base_app_token_env: agentsPayload.test_case?.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN",
    base_app_token_configured: Boolean(agentsPayload.test_case?.base_app_token_configured),
    base_app_token_masked: agentsPayload.test_case?.base_app_token_masked || "",
  });
  const [testCaseToken, setTestCaseToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const markDirty = () => { setDirty(true); onDirtyChange(true); };
  const feishuName = (id: string) => {
    const fromMap = String(recentFeishu.names?.[id] || "").trim();
    if (fromMap) return fromMap;
    const user = (recentFeishu.users || []).find((item) => item.id === id);
    if (user?.name) return String(user.name).trim();
    const chat = (recentFeishu.chats || []).find((item) => item.id === id);
    return String(chat?.name || "").trim();
  };
  const shortFeishuId = (id: string) => {
    const value = String(id || "").trim();
    if (value.length <= 14) return value;
    return `${value.slice(0, 10)}…${value.slice(-4)}`;
  };
  const recentPeople = (recentFeishu.users?.length
    ? recentFeishu.users
    : recentFeishu.user_ids.map((id) => ({ id, name: feishuName(id) }))
  ).filter((item) => item.id);
  const isDirectChat = (chat: FeishuIdentityItem) => {
    const mode = String(chat.chat_mode || "").trim().toLowerCase();
    const context = String(chat.context_type || "").trim().toLowerCase();
    const kind = String(chat.kind || "").trim().toLowerCase();
    const name = String(chat.name || "").trim().toLowerCase();
    return context === "dm" || kind === "dm" || kind === "private" || ["p2p", "private", "dm"].includes(mode) || name === "direct message";
  };
  const recentChats = (recentFeishu.chats?.length
    ? recentFeishu.chats
    : recentFeishu.chat_ids.map((id) => ({ id, name: feishuName(id) }))
  ).filter((item) => item.id && !isDirectChat(item));
  const configuredUserIds = Array.from(new Set([
    ...(accessDraft.allowed_user_ids || []),
    ...(accessDraft.mutation_allowed_user_ids || []),
    ...(accessDraft.admin_user_ids || []),
  ]));
  const accessPeopleById = new Map<string, FeishuIdentityItem>();
  for (const person of recentPeople) if (person.id) accessPeopleById.set(String(person.id), person);
  for (const id of configuredUserIds) if (!accessPeopleById.has(id)) accessPeopleById.set(id, { id, name: feishuName(id) });
  const accessPeople = Array.from(accessPeopleById.values()).filter((item) => item.id);
  const accessPeopleGroups: Array<{ key: string; name: string; ids: string[]; pending: boolean }> = [];
  for (const person of accessPeople) {
    const id = String(person.id);
    const unionId = String(person.union_id || "").trim();
    const key = unionId || `id:${id}`;
    const pendingName = t("settings.pendingAccess");
    const name = String(person.name || feishuName(id) || pendingName);
    const group = accessPeopleGroups.find((item) => item.key === key);
    if (group) {
      group.ids.push(id);
      if (name !== pendingName) group.name = name;
    } else {
      accessPeopleGroups.push({ key, name, ids: [id], pending: false });
    }
  }
  for (const group of accessPeopleGroups) {
    group.pending = group.ids.some((id) => !configuredUserIds.includes(id));
  }
  const directChatIds = new Set((recentFeishu.direct_chat_ids || []).map(String));
  const accessChatIds = Array.from(new Set([...(recentFeishu.chat_ids || []), ...(accessDraft.allowed_chat_ids || [])])).filter((id) => !directChatIds.has(String(id)));
  const accessChats: FeishuIdentityItem[] = accessChatIds
    .map((id) => recentChats.find((chat) => String(chat.id) === id) || { id, name: feishuName(id), agents: [] })
    .filter((chat) => !isDirectChat(chat));
  const hasAccess = (field: "allowed_user_ids" | "mutation_allowed_user_ids" | "admin_user_ids", id: string) => (accessDraft[field] || []).includes(id);
  const toggleAccess = (field: "allowed_user_ids" | "mutation_allowed_user_ids" | "admin_user_ids" | "allowed_chat_ids", id: string, enabled: boolean) => {
    setAccessDraft((current) => {
      const values = current[field] || [];
      return { ...current, [field]: enabled ? Array.from(new Set([...values, id])) : values.filter((value) => value !== id) };
    });
    markDirty();
  };
  const configuredPeople = accessPeopleGroups.filter((group) => group.ids.some((id) => configuredUserIds.includes(id)));
  const syncAgents = (payload: AgentsSettingsPayload) => {
    const nextAgents = Array.isArray(payload.agents)
      ? payload.agents.map((agent) => ({ ...agent, provider: agent.provider || "deepseek", app_secret: "" }))
      : [];
    const nextAccess = {
      allowed_chat_ids: payload.access?.allowed_chat_ids || [],
      allowed_user_ids: payload.access?.allowed_user_ids || [],
      mutation_allowed_user_ids: payload.access?.mutation_allowed_user_ids || [],
      admin_user_ids: payload.access?.admin_user_ids || [],
      legacy_warning: Boolean(payload.access?.legacy_warning),
      default_policy: payload.access?.default_policy || "deny",
    };
    setAgentsEnabled(Boolean(payload.enabled));
    setDefaultLanguage(payload.conversation?.default_language || "zh-Hant");
    setAgentDrafts(nextAgents);
    setAccessDraft(nextAccess);
    setRecentFeishu({
      user_ids: payload.recent_feishu?.private_user_ids || payload.recent_feishu?.user_ids || [],
      chat_ids: payload.recent_feishu?.group_chat_ids || payload.recent_feishu?.chat_ids || [],
      direct_chat_ids: payload.recent_feishu?.direct_chat_ids || [],
      users: payload.recent_feishu?.private_users || payload.recent_feishu?.users || [],
      chats: payload.recent_feishu?.group_chats || payload.recent_feishu?.chats || [],
      names: payload.recent_feishu?.names || {},
    });
    setAgentsBaseline({
      enabled: Boolean(payload.enabled),
      defaultLanguage: payload.conversation?.default_language || "zh-Hant",
      agents: JSON.stringify(nextAgents),
      access: JSON.stringify(nextAccess),
      testCase: JSON.stringify(payload.test_case || {}),
    });
    setTestCaseDraft({
      language: payload.test_case?.language || "zh-Hant",
      table_name: payload.test_case?.table_name || "Sheet1",
      base_app_token_env: payload.test_case?.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN",
      base_app_token_configured: Boolean(payload.test_case?.base_app_token_configured),
      base_app_token_masked: payload.test_case?.base_app_token_masked || "",
    });
    setTestCaseToken("");
  };
  const updateAgent = (agentId: string, patch: Partial<AgentSettings>) => {
    setAgentDrafts((current) => current.map((agent) => agent.id === agentId ? { ...agent, ...patch } : agent));
    markDirty();
  };
  useEffect(() => { void request("/api/delivery/status-options", project).then((response) => setWorkflowStatuses(Array.isArray(response.options) ? response.options.map(String) : [])).catch(() => setWorkflowStatuses([])); }, [project]);
  useEffect(() => {
    let cancelled = false;
    void request("/api/agents", project)
      .then((response) => {
        if (cancelled) return;
        syncAgents(response as AgentsSettingsPayload);
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [project]);
  useEffect(() => {
    const global = workflowModelConfig(workspace, "scan");
    setScanWindow(String(workspace.scan_window_days || 7)); setScanCron(String(schedules.scan?.cron || "0 12 * * 1-5")); setScanEnabled(Boolean(schedules.scan)); setDeliveryInterval(String(Math.round((schedules.delivery?.interval_seconds || 300) / 60))); setEligibleStatuses(Array.isArray(schedules.delivery?.jira_statuses) ? schedules.delivery.jira_statuses.map(String) : String(schedules.delivery?.jira_status || "To Do,Backlog,In Progress").split(",").map((value) => value.trim()).filter(Boolean)); setInDevStatus(String(schedules.delivery?.in_dev_status || "")); setDevDoneStatus(String(schedules.delivery?.dev_done_status || "")); setBlockedStatus(String(schedules.delivery?.blocked_status || "Block")); setDeliveryEnabled(Boolean(schedules.delivery?.enabled)); setPatchInterval(String(Math.round((schedules.patch?.interval_seconds || 300) / 60))); setPatchStatuses(Array.isArray(schedules.patch?.jira_statuses) ? schedules.patch.jira_statuses.map(String) : ["To Do"]); setPatchStartStatus(String(schedules.patch?.in_progress_status || "In Progress")); setPatchDoneStatus(String(schedules.patch?.done_status || "Done")); setPatchBlockedStatus(String(schedules.patch?.blocked_status || "Block")); setPatchEnabled(Boolean(schedules.patch?.enabled)); setGlobalProvider(global.provider); setGlobalModel(global.model); setGlobalBaseUrl(global.base_url); setGlobalApiKeyEnv(global.api_key_env); setGlobalReasoningEffort(global.reasoning_effort); setGlobalAccountEmail(global.account_email); setFeishuEnabled(workspace.feishu_notifications_enabled !== false); setSecrets({}); setChangedSecrets({});
    if (data.interactive?.agents) syncAgents(data.interactive.agents);
    setDirty(false); onDirtyChange(false);
  }, [project]);
  useEffect(() => { setScanPublishMode(String(workspace.publish?.scan || "pr")); setDeliveryPublishMode(String(workspace.publish?.delivery || "pr")); setPatchPublishMode(String(workspace.publish?.patch || "pr")); }, [workspace.publish?.scan, workspace.publish?.delivery, workspace.publish?.patch]);
  useEffect(() => { setFeishuEnabled(workspace.feishu_notifications_enabled !== false); }, [workspace.feishu_notifications_enabled]);
  const deploymentConfigKey = JSON.stringify(workspace.deployment_tracking || {});
  useEffect(() => {
    const config = workspace.deployment_tracking || {};
    setDeploymentEnabled(Boolean(config.enabled));
    setDeploymentProvider(String(config.provider || "none"));
    setDeploymentPollInterval(String(config.poll_interval_seconds || 30));
    setDeploymentTimeout(String(config.timeout_seconds || 3600));
    setJenkinsJob(String(config.jenkins?.job || ""));
    setGithubRepository(String(config.github_actions?.repository || ""));
    setGithubWorkflow(String(config.github_actions?.workflow || ""));
  }, [deploymentConfigKey]);
  useEffect(() => { const warn = (event: BeforeUnloadEvent) => { if (!dirty) return; event.preventDefault(); event.returnValue = ""; }; window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [dirty]);
  const getSecret = async (name: string) => { const response = await request(`/api/integration?key=${encodeURIComponent(name)}`, project); return String(response.value); };
  const reveal = async (name: string) => { try { const result = await getSecret(name); setSecrets((current) => ({ ...current, [name]: result })); notify("Integration value revealed", "success"); } catch (err) { notify(err instanceof Error ? err.message : "Unable to reveal value", "error"); } };
  const copy = async (name: string) => { try { const result = await getSecret(name); await navigator.clipboard.writeText(result); notify("Integration value copied", "success"); } catch (err) { notify(err instanceof Error ? err.message : "Unable to copy value", "error"); } };
  const configured = workspace.configured_integrations || [];
  const integrationSources = (workspace.integration_sources || {}) as Record<string, string>;
  const jenkinsCredentialsConfigured = configured.includes("JENKINS_URL") && configured.includes("JENKINS_AUTH");
  const statusOptions = Array.from(new Set(["To Do", "Backlog", "In Progress", "Done", "Block", ...workflowStatuses, ...eligibleStatuses, ...patchStatuses, inDevStatus, devDoneStatus, patchStartStatus, patchDoneStatus, patchBlockedStatus].filter(Boolean)));
  const configuredDeliveryStatuses = Array.isArray(schedules.delivery?.jira_statuses) ? schedules.delivery.jira_statuses.map(String) : String(schedules.delivery?.jira_status || "To Do,Backlog,In Progress").split(",").map((value) => value.trim()).filter(Boolean);
  const configuredPatchStatuses = Array.isArray(schedules.patch?.jira_statuses) ? schedules.patch.jira_statuses.map(String) : ["To Do"];
  const sameValues = (left: string[], right: string[]) => left.length === right.length && left.every((value, index) => value === right[index]);
  const scanScheduleChanged = scanEnabled !== Boolean(schedules.scan) || (scanEnabled && scanCron !== String(schedules.scan?.cron || "0 12 * * 1-5"));
  const deliveryScheduleChanged = deliveryEnabled !== Boolean(schedules.delivery?.enabled) || (deliveryEnabled && (deliveryInterval !== String(Math.round((schedules.delivery?.interval_seconds || 300) / 60)) || !sameValues(eligibleStatuses, configuredDeliveryStatuses) || inDevStatus !== String(schedules.delivery?.in_dev_status || "") || devDoneStatus !== String(schedules.delivery?.dev_done_status || "") || blockedStatus !== String(schedules.delivery?.blocked_status || "Block")));
  const patchScheduleChanged = patchEnabled !== Boolean(schedules.patch?.enabled) || (patchEnabled && (patchInterval !== String(Math.round((schedules.patch?.interval_seconds || 300) / 60)) || !sameValues(patchStatuses, configuredPatchStatuses) || patchStartStatus !== String(schedules.patch?.in_progress_status || "In Progress") || patchDoneStatus !== String(schedules.patch?.done_status || "Done") || patchBlockedStatus !== String(schedules.patch?.blocked_status || "Block")));
  const publishPolicyChanged = scanPublishMode !== String(workspace.publish?.scan || "pr") || deliveryPublishMode !== String(workspace.publish?.delivery || "pr") || patchPublishMode !== String(workspace.publish?.patch || "pr");
  const deploymentConfig = {
    enabled: deploymentEnabled,
    provider: deploymentProvider,
    poll_interval_seconds: Number(deploymentPollInterval),
    timeout_seconds: Number(deploymentTimeout),
    jenkins: { job: jenkinsJob },
    github_actions: { repository: githubRepository, workflow: githubWorkflow },
  };
  const savedDeploymentConfig = workspace.deployment_tracking || {};
  const deploymentConfigChanged = JSON.stringify(deploymentConfig) !== JSON.stringify({
    enabled: Boolean(savedDeploymentConfig.enabled),
    provider: String(savedDeploymentConfig.provider || "none"),
    poll_interval_seconds: Number(savedDeploymentConfig.poll_interval_seconds || 30),
    timeout_seconds: Number(savedDeploymentConfig.timeout_seconds || 3600),
    jenkins: { job: String(savedDeploymentConfig.jenkins?.job || "") },
    github_actions: { repository: String(savedDeploymentConfig.github_actions?.repository || ""), workflow: String(savedDeploymentConfig.github_actions?.workflow || "") },
  });
  const agentsChanged = defaultLanguage !== agentsBaseline.defaultLanguage || agentsEnabled !== agentsBaseline.enabled || JSON.stringify(agentDrafts) !== agentsBaseline.agents || JSON.stringify(accessDraft) !== agentsBaseline.access || JSON.stringify({
    language: testCaseDraft.language || "zh-Hant",
    table_name: testCaseDraft.table_name || "Sheet1",
    base_app_token_env: testCaseDraft.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN",
  }) !== (() => {
    try {
      const baseline = JSON.parse(agentsBaseline.testCase || "{}") as TestCaseSettings;
      return JSON.stringify({
        language: baseline.language || "zh-Hant",
        table_name: baseline.table_name || "Sheet1",
        base_app_token_env: baseline.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN",
      });
    } catch {
      return JSON.stringify({ language: "zh-Hant", table_name: "Sheet1", base_app_token_env: "FEISHU_MBPASS_QA_SHEET_TOKEN" });
    }
  })() || Boolean(testCaseToken.trim());
  const saveAll = async () => {
    if (saving) return;
    setSaving(true);
    try {
      if (!globalModel.trim()) throw new Error("Choose a preset or enter a supported global model ID.");
      const saves = [
        () => request("/api/workspace", project, { method: "POST", json: { scan_window_days: Number(scanWindow), ai_provider: globalProvider, ai_model: globalModel.trim(), ai_base_url: globalBaseUrl.trim(), ai_api_key_env: globalApiKeyEnv.trim(), ai_reasoning_effort: globalReasoningEffort.trim(), ai_account_email: globalAccountEmail.trim(), feishu_notifications_enabled: feishuEnabled } }),
        ...Object.entries(changedSecrets).map(([key, value]) => () => request("/api/integration", project, { method: "POST", json: { key, value } }))
      ];
      if (scanScheduleChanged) saves.push(() => request("/api/schedule", project, { method: "POST", json: scanEnabled ? { kind: "scan", action: "save", cron: scanCron } : { kind: "scan", action: "remove" } }));
      if (deliveryScheduleChanged) saves.push(() => request("/api/schedule", project, { method: "POST", json: deliveryEnabled ? { kind: "delivery", action: "save", interval_minutes: Number(deliveryInterval), jira_statuses: eligibleStatuses, in_dev_status: inDevStatus, dev_done_status: devDoneStatus, blocked_status: blockedStatus } : { kind: "delivery", action: "remove" } }));
      if (patchScheduleChanged) saves.push(() => request("/api/schedule", project, { method: "POST", json: patchEnabled ? { kind: "patch", action: "save", interval_minutes: Number(patchInterval), jira_statuses: patchStatuses, issue_types: ["Task", "Bug"], in_progress_status: patchStartStatus, done_status: patchDoneStatus, blocked_status: patchBlockedStatus } : { kind: "patch", action: "remove" } }));
      if (publishPolicyChanged) saves.push(() => request("/api/publish-policy", project, { method: "POST", json: { scan_mode: scanPublishMode, delivery_mode: deliveryPublishMode, patch_mode: patchPublishMode } }));
      if (deploymentConfigChanged) saves.push(() => request("/api/deployment-config", project, { method: "POST", json: deploymentConfig }));
      if (agentsChanged) {
        saves.push(async () => {
          const result = await request("/api/agents", project, {
            method: "POST",
            json: {
              enabled: agentsEnabled,
              conversation: { version: "3.3", default_language: defaultLanguage },
              access: accessDraft,
              test_case: {
                destination: "sheet",
                language: testCaseDraft.language || "zh-Hant",
                table_name: testCaseDraft.table_name || "Sheet1",
                base_app_token_env: testCaseDraft.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN",
                ...(testCaseToken.trim() ? { base_app_token: testCaseToken.trim() } : {}),
              },
              agents: agentDrafts.map((agent) => {
                const body: Record<string, unknown> = {
                  id: agent.id,
                  role: agent.role,
                  workflow: agent.workflow,
                  conversation_enabled: agent.conversation_enabled,
                  mode: agent.mode,
                  soft_timeout_seconds: Number(agent.soft_timeout_seconds),
                  hard_timeout_seconds: Number(agent.hard_timeout_seconds),
                  reaction_enabled: agent.reaction_enabled,
                  max_concurrent_jobs: Number(agent.max_concurrent_jobs),
                  soul_version: agent.soul_version,
                  soul: agent.soul,
                  app_id: String(agent.app_id || "").trim(),
                };
                const secret = String(agent.app_secret || "").trim();
                if (secret) body.app_secret = secret;
                return body;
              }),
            },
          });
          syncAgents(result as AgentsSettingsPayload);
        });
      }
      for (const save of saves) await save();
      setChangedSecrets({}); setDirty(false); onDirtyChange(false); notify("Settings saved", "success"); void reload();
    } catch (err) { notify(err instanceof Error ? err.message : "Unable to save Settings", "error"); }
    finally { setSaving(false); }
  };
  const enabledScheduleCount = [scanEnabled, deliveryEnabled, patchEnabled].filter(Boolean).length;
  const enabledAgentCount = agentDrafts.filter((agent) => agent.conversation_enabled).length;
  return <div className="settings-stack">
    <PageIntro title={t("heading.workspaceSettings")} description={`${project || t("common.currentProject")} · ${t("context.settings.description")}`} action={<span className="settings-scope">{t("settings.localConfiguration")}</span>} />
    <div className="settings-summary">
      <div><span>{t("common.schedules")}</span><strong>{enabledScheduleCount}/3</strong><small>{t("common.active")}</small></div>
      <div><span>{t("common.agentConversations")}</span><strong>{enabledAgentCount}/{agentDrafts.length || 4}</strong><small>{t("common.enabled")}</small></div>
      <div><span>{t("heading.publishPolicy")}</span><strong>{deliveryPublishMode === "direct" ? t("settings.direct") : deliveryPublishMode === "merge" ? t("settings.merge") : t("settings.pullRequest")}</strong><small>{t("label.autoDelivery")}</small></div>
      <div><span>{t("common.integrations")}</span><strong>{configured.length}</strong><small>{t("common.configuredKeys")}</small></div>
    </div>
    <nav className="settings-nav" aria-label={t("common.settingsSections")}><a href="#settings-automation">{t("settings.automation")}</a><a href="#settings-agents">{t("settings.agentTeam")}</a><a href="#settings-project">{t("settings.projectOutput")}</a><a href="#settings-runtime">{t("settings.runtime")}</a></nav>
    <section className="settings-cluster" id="settings-automation">
      <div className="settings-cluster-heading"><div><span>{t("settings.controlPlane")}</span><h2>{t("settings.automation")}</h2><p>{t("settings.automationDescription")}</p></div><a href="#settings-agents">{t("settings.nextAgentTeam")} <ChevronRight size={13} /></a></div>
      <Panel title={t("heading.automationSchedules")}>
      <div className="settings-section"><div className="settings-copy"><div className="settings-heading"><div className="settings-title-stack"><h4>{t("label.autoScan")}</h4></div></div><p>{text(schedules.scan?.description, t("settings.scanDefaultDescription"))}</p></div><div className="settings-control wide"><div className="form-grid compact scan-settings-fields" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, padding: 0, width: "100%" }}><Field label={t("label.lookbackDays")}><input type="number" min="1" max="365" value={scanWindow} onChange={(event) => { setScanWindow(event.target.value); markDirty(); }} /></Field><Field label={t("label.cron")}><input value={scanCron} onChange={(event) => { setScanCron(event.target.value); markDirty(); }} /></Field></div></div><div className="settings-toggle"><ScheduleToggle enabled={scanEnabled} onChange={(enabled) => { setScanEnabled(enabled); markDirty(); }} /></div></div>
      <div className="settings-section divider"><div className="settings-copy"><div className="settings-heading"><div className="settings-title-stack"><h4>{t("label.autoDelivery")}</h4></div></div><p>{deliveryEnabled ? `Polling every ${deliveryInterval} minute(s).` : t("settings.deliveryPaused")}</p></div><div className="settings-control wide"><div className="form-grid compact"><Field label={t("label.intervalMinutes")}><input type="number" min="1" value={deliveryInterval} onChange={(event) => { setDeliveryInterval(event.target.value); markDirty(); }} /></Field><Field label={t("label.eligibleStatuses")} help={t("settings.deliveryStatusHelp")}><StatusMultiSelect options={statusOptions} value={eligibleStatuses} onChange={setEligibleStatuses} markDirty={markDirty} /></Field><Field label={t("label.moveStarted")}><select value={inDevStatus} onChange={(event) => { setInDevStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field><Field label={t("label.moveCompleted")}><select value={devDoneStatus} onChange={(event) => { setDevDoneStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field><Field label={t("label.moveFailed")}><select value={blockedStatus} onChange={(event) => { setBlockedStatus(event.target.value); markDirty(); }}>{Array.from(new Set([...statusOptions, "Block"])).map((value) => <option value={value} key={value}>{value}</option>)}</select></Field></div><p className="schedule-note">{t("settings.deliveryStatusNote")}</p></div><div className="settings-toggle"><ScheduleToggle enabled={deliveryEnabled} onChange={(enabled) => { setDeliveryEnabled(enabled); markDirty(); }} /></div></div>
      <div className="settings-section divider"><div className="settings-copy"><div className="settings-heading"><div className="settings-title-stack"><h4>{t("label.autoPatch")}</h4></div></div><p>{patchEnabled ? `Polling every ${patchInterval} minute(s) for Task and Bug cards.` : t("settings.patchPaused")}</p></div><div className="settings-control wide"><div className="form-grid compact"><Field label={t("label.intervalMinutes")}><input type="number" min="1" value={patchInterval} onChange={(event) => { setPatchInterval(event.target.value); markDirty(); }} /></Field><Field label={t("label.eligibleStatuses")}><StatusMultiSelect options={statusOptions} value={patchStatuses} onChange={setPatchStatuses} markDirty={markDirty} /></Field><Field label={t("label.moveStarted")}><select value={patchStartStatus} onChange={(event) => { setPatchStartStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field><Field label={t("label.moveCompleted")}><select value={patchDoneStatus} onChange={(event) => { setPatchDoneStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field><Field label={t("label.moveBlocked")}><select value={patchBlockedStatus} onChange={(event) => { setPatchBlockedStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field></div><p className="schedule-note">{t("settings.patchStatusNote")}</p></div><div className="settings-toggle"><ScheduleToggle enabled={patchEnabled} onChange={(enabled) => { setPatchEnabled(enabled); markDirty(); }} /></div></div>
      </Panel>
    </section>
    <section className="settings-cluster" id="settings-agents">
      <div className="settings-cluster-heading"><div><span>{t("settings.humanAgents")}</span><h2>{t("settings.agentTeam")}</h2><p>{t("settings.agentTeamDescription")}</p></div><a href="#settings-project">{t("settings.nextProjectOutput")} <ChevronRight size={13} /></a></div>
      <Panel title={t("heading.agentRoles")} action={<span className="muted">{t("settings.globalFeishuAgents")}</span>}>
      <div className="settings-section"><div className="settings-copy"><div className="settings-heading"><div className="settings-title-stack"><h4>{t("label.gateway")}</h4></div></div><p>Enable Feishu conversational agents. Config lives in {text(agentsPayload.config_path, "~/.lumon/agents/config.json")}. Restart `lumon agents start` after saving. Mutations fail closed until mutation users are configured.</p></div><div className="settings-toggle"><ScheduleToggle enabled={agentsEnabled} onChange={(enabled) => { setAgentsEnabled(enabled); markDirty(); }} /></div></div>
      <div className="settings-section divider">
        <div className="settings-copy">
          <div className="settings-heading"><div className="settings-title-stack"><h4>{t("settings.defaultReplyLanguage")}</h4></div></div>
          <p>{t("settings.defaultReplyLanguageDescription")}</p>
        </div>
        <div className="settings-control">
          <Field label={t("label.agentDefaultLanguage")}>
            <select value={defaultLanguage} onChange={(event) => { setDefaultLanguage(event.target.value); markDirty(); }}>
              <option value="zh-Hant">{t("language.zhHant")} (zh-Hant)</option>
              <option value="zh-Hans">{t("language.zhHans")} (zh-Hans)</option>
              <option value="en">{t("language.en")} (en)</option>
            </select>
          </Field>
        </div>
      </div>
      <div className="settings-section divider access-control-section">
        <div className="settings-copy">
          <div className="settings-heading"><div className="settings-title-stack"><h4>{t("settings.accessControl")}</h4></div></div>
          <p>{t("settings.accessControlDescription")}</p>
          {Boolean(accessDraft.legacy_warning ?? agentsPayload.access?.legacy_warning) && (
            <p className="schedule-note">{t("settings.legacyWarning")}</p>
          )}
        </div>
        <div className="settings-control wide access-control-panel">
          <div className="access-selector-grid">
            <Field label={t("settings.accessPerson")} help={t("settings.selectIdentityHelp")}><select value={selectedPersonId} onChange={(event) => setSelectedPersonId(event.target.value)}><option value="">{t("settings.selectPerson")}</option>{accessPeopleGroups.map((group) => <optgroup label={`${group.name} · ${group.ids.length}${group.pending ? ` · ${t("settings.pendingAccess")}` : ""}`} key={group.key}>{group.ids.map((id) => <option value={id} key={id}>{shortFeishuId(id)}</option>)}</optgroup>)}</select></Field>
          </div>
          <div className="access-permission-grid">
            <section className="access-permission-card">
              <div className="access-permission-heading"><div><strong>{t("settings.groupChats")}</strong><span>{t("settings.groupChatsDescription")}</span></div><Badge value={`${accessChats.filter((chat) => (accessDraft.allowed_chat_ids || []).includes(String(chat.id))).length}/${accessChats.length}`} /></div>
              <div className="access-list">
                {accessChats.length ? accessChats.map((chat) => {
                  const chatId = String(chat.id || "");
                  const agentNames = (chat.agents || []).map((id) => agentDrafts.find((agent) => agent.id === id)?.display_name || id).join(", ");
                  return <label className="access-list-row" key={chatId}><span className="access-list-main"><strong>{chat.name || feishuName(chatId) || shortFeishuId(chatId)}</strong><code>{chatId}</code>{agentNames && <small>{t("settings.agentMembership", { value: agentNames })}</small>}</span><input type="checkbox" checked={(accessDraft.allowed_chat_ids || []).includes(chatId)} onChange={(event) => toggleAccess("allowed_chat_ids", chatId, event.target.checked)} aria-label={`${t("settings.allowChat")} ${chat.name || chatId}`} /></label>;
                }) : <p className="schedule-note access-empty-note">{t("settings.noGroupChats")}</p>}
              </div>
            </section>
            <section className="access-permission-card">
              <div className="access-permission-heading"><div><strong>{t("settings.privateContacts")}</strong><span>{t("settings.privateContactsDescription")}</span></div><Badge value={`${accessPeople.filter((person) => hasAccess("allowed_user_ids", String(person.id))).length}/${accessPeople.length}`} /></div>
              <div className="access-list">
                {accessPeople.length ? accessPeople.map((person) => {
                  const personId = String(person.id || "");
                  const name = String(person.name || feishuName(personId) || t("settings.pendingAccess"));
                  return <label className="access-list-row" key={personId}><span className="access-list-main"><strong>{name}</strong><code>{personId}</code></span><input type="checkbox" checked={hasAccess("allowed_user_ids", personId)} onChange={(event) => toggleAccess("allowed_user_ids", personId, event.target.checked)} aria-label={`${t("settings.canTalk")} ${name}`} /></label>;
                }) : <p className="schedule-note access-empty-note">{t("settings.noPrivateContacts")}</p>}
              </div>
            </section>
          </div>
          {selectedPersonId && <div className="access-identity-editor"><div className="access-identity-heading"><span>{t("settings.identityRoles")}</span><code>{shortFeishuId(selectedPersonId)}</code></div><label><input type="checkbox" checked={hasAccess("allowed_user_ids", selectedPersonId)} onChange={(event) => toggleAccess("allowed_user_ids", selectedPersonId, event.target.checked)} />{t("settings.canTalk")}</label><label><input type="checkbox" checked={hasAccess("mutation_allowed_user_ids", selectedPersonId)} onChange={(event) => toggleAccess("mutation_allowed_user_ids", selectedPersonId, event.target.checked)} />{t("settings.canMutate")}</label><label><input type="checkbox" checked={hasAccess("admin_user_ids", selectedPersonId)} onChange={(event) => toggleAccess("admin_user_ids", selectedPersonId, event.target.checked)} />{t("settings.canAdmin")}</label></div>}
          {configuredPeople.length > 0 && <div className="access-summary"><div className="access-identity-heading"><span>{t("settings.accessSummary")}</span><small>{t("settings.identityCount", { count: configuredPeople.reduce((count, group) => count + group.ids.length, 0) })}</small></div>{configuredPeople.map((group) => <button type="button" className="access-summary-row" key={group.key} onClick={() => setSelectedPersonId(group.ids[0])}><strong>{group.name}</strong><span>{t("settings.identityCount", { count: group.ids.length })}</span><em>{["allowed_user_ids", "mutation_allowed_user_ids", "admin_user_ids"].filter((field) => group.ids.some((id) => hasAccess(field as "allowed_user_ids" | "mutation_allowed_user_ids" | "admin_user_ids", id))).length} {t("settings.rolesApplied")}</em></button>)}</div>}
        </div>
      </div>
      {agentDrafts.map((agent) => {
        return <div className="settings-section divider agent-role-section" key={agent.id}>
          <div className="settings-copy">
            <div className="settings-heading"><div className="settings-title-stack"><div className="agent-settings-identity"><AgentAvatar agentId={agent.id} displayName={agent.display_name} size="guide" /><span><h4>{agent.display_name}</h4><small>{agent.title}</small></span></div></div></div>
          </div>
          <div className="settings-control wide"><div className="form-grid compact agent-core-fields">
            <Field label={t("label.feishuAppId")}><input value={agent.app_id || ""} placeholder={agent.app_id_masked || "cli_…"} onChange={(event) => updateAgent(agent.id, { app_id: event.target.value })} /></Field>
            <Field label={t("label.feishuAppSecret")} help={agent.app_secret_configured ? `Configured (${agent.app_secret_masked || "set"}). Leave blank to keep.` : t("settings.appSecretRequired")}><input type="password" value={agent.app_secret || ""} placeholder={agent.app_secret_configured ? t("settings.keepSecret") : t("settings.enterSecret")} onChange={(event) => updateAgent(agent.id, { app_secret: event.target.value })} autoComplete="new-password" /></Field>
          </div></div><div className="agent-conversation-toggle"><ScheduleToggle label={t("label.conversation")} enabled={agent.conversation_enabled} onChange={(enabled) => updateAgent(agent.id, { conversation_enabled: enabled })} /></div>
        </div>;
      })}
      {agentDrafts.length === 0 && <div className="settings-section divider"><Empty label={t("common.noAgentRolesSettings")} /></div>}
      </Panel>
    </section>
    <section className="settings-cluster" id="settings-project">
      <div className="settings-cluster-heading"><div><span>{t("settings.businessOutput")}</span><h2>{t("settings.projectOutput")}</h2><p>{t("settings.projectOutputDescription")}</p></div><a href="#settings-runtime">{t("settings.nextRuntime")} <ChevronRight size={13} /></a></div>
      <Panel title={t("heading.testCases")} action={<span className="muted">Mark · {project || t("common.project")}</span>}>
      <div className="settings-section">
        <div className="settings-copy">
          <div className="settings-heading"><div className="settings-title-stack"><h4>{t("settings.generationLanguage")}</h4></div></div>
          <p>{t("settings.generationDescription")}</p>
        </div>
        <div className="settings-control wide">
          <div className="form-grid compact">
            <Field label={t("label.outputLanguage")}>
              <select
                value={testCaseDraft.language || "zh-Hant"}
                onChange={(event) => {
                  setTestCaseDraft((current) => ({ ...current, language: event.target.value }));
                  markDirty();
                }}
              >
                <option value="zh-Hant">{t("language.zhHant")} (zh-Hant)</option>
                <option value="zh-Hans">{t("language.zhHans")} (zh-Hans)</option>
                <option value="en">{t("language.en")}</option>
              </select>
            </Field>
            <Field label={t("label.spreadsheetTab")}>
              <input
                value={testCaseDraft.table_name || "Sheet1"}
                onChange={(event) => {
                  setTestCaseDraft((current) => ({ ...current, table_name: event.target.value }));
                  markDirty();
                }}
              />
            </Field>
            <Field
              label={t("label.spreadsheetToken")}
              help={testCaseDraft.base_app_token_configured
                ? `Configured (${testCaseDraft.base_app_token_masked || "set"}). Leave blank to keep. Env: ${testCaseDraft.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN"}`
                : `Stored in ~/.lumon/.env.local as ${testCaseDraft.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN"}`}
            >
              <input
                value={testCaseToken}
                placeholder={testCaseDraft.base_app_token_configured ? "Leave blank to keep current token" : "https://…/sheets/TOKEN or TOKEN"}
                onChange={(event) => {
                  setTestCaseToken(event.target.value);
                  markDirty();
                }}
                autoComplete="off"
              />
            </Field>
          </div>
          <p className="schedule-note">{t("settings.afterGeneration")}</p>
        </div>
      </div>
      </Panel>
    </section>
    <section className="settings-cluster" id="settings-runtime">
      <div className="settings-cluster-heading"><div><span>{t("settings.operatingDetails")}</span><h2>{t("settings.runtime")}</h2><p>{t("settings.runtimeDescription")}</p></div><a href="#settings-automation">{t("settings.backAutomation")} <ChevronLeft size={13} /></a></div>
      <Panel title={t("heading.executionModels")} action={<span className="muted">{t("settings.modelCenter")}</span>}>
        <div className="settings-section model-center-section">
          <div className="settings-copy">
            <h4>{t("settings.modelCenter")}</h4>
            <p>{t("settings.modelCenterDescription")}</p>
          </div>
          <div className="settings-control wide">
            <div className="model-center">
              <section className="model-center-block model-center-global">
                <div className="model-center-heading"><strong>{t("settings.globalModelConfig")}</strong><span>{t("settings.globalModelScope")}</span></div>
                <WorkflowModelField label={t("settings.globalModelConfig")} provider={globalProvider} model={globalModel} baseUrl={globalBaseUrl} apiKeyEnv={globalApiKeyEnv} reasoningEffort={globalReasoningEffort} accountEmail={globalAccountEmail} onProviderChange={setGlobalProvider} onModelChange={(value) => { setGlobalModel(value); markDirty(); }} onBaseUrlChange={(value) => { setGlobalBaseUrl(value); markDirty(); }} onApiKeyEnvChange={(value) => { setGlobalApiKeyEnv(value); markDirty(); }} onReasoningEffortChange={(value) => { setGlobalReasoningEffort(value); markDirty(); }} onAccountEmailChange={(value) => { setGlobalAccountEmail(value); markDirty(); }} markDirty={markDirty} />
              </section>
            </div>
          </div>
        </div>
      </Panel>
      <Panel title={t("settings.openCodeRuntime")} action={<Badge value={runtimeStatus.installed && runtimeStatus.api_key_configured && runtimeStatus.account_configured !== false ? "ready" : "setup"} />}>
        <div className="settings-section">
          <div className="settings-copy">
            <h4>{t("settings.openCodeRuntime")}</h4>
            <p>{t("settings.openCodeRuntimeDescription")}</p>
          </div>
          <div className="settings-control wide">
            <div className="runtime-status-grid">
              <div><span>{t("settings.harness")}</span><strong>{text(runtimeStatus.harness, "OpenCode")}</strong></div>
              <div><span>{t("settings.runtimeModel")}</span><code>{text(runtimeStatus.model, globalModel)}</code></div>
              {runtimeStatus.provider === "codex" && <div><span>{t("settings.reasoningEffort")}</span><code>{text(runtimeStatus.reasoning_effort, globalReasoningEffort || "xhigh")}</code></div>}
              <div><span>{t("settings.cliVersion")}</span><strong>{text(runtimeStatus.version, runtimeStatus.installed ? "installed" : "not installed")}</strong></div>
              <div><span>{t("settings.deepSeekCredential")}</span><strong className={runtimeStatus.api_key_configured ? "runtime-ok" : "runtime-warning"}>{text(runtimeStatus.api_key_env, "local model (no key)")} · {runtimeStatus.api_key_configured ? t("settings.configured") : t("settings.notConfigured")}</strong></div>
              {runtimeStatus.provider === "codex" && <div><span>{t("settings.runtimeAccount")}</span><strong className={runtimeStatus.account_match ? "runtime-ok" : "runtime-warning"}>{text(runtimeStatus.account_email, t("settings.notConfigured"))} · {runtimeStatus.account_match ? t("settings.configured") : t("settings.notConfigured")}</strong></div>}
              <div><span>{t("settings.sessionMode")}</span><strong>{text(runtimeStatus.session_mode)}</strong></div>
              <div><span>{t("settings.permissionProfile")}</span><strong>{text(runtimeStatus.permission_profile)}</strong></div>
              <div className="runtime-status-wide"><span>{t("settings.actionCatalog")}</span><code>{text(runtimeStatus.action_catalog)}</code></div>
            </div>
          </div>
        </div>
      </Panel>
      <Panel title={t("settings.harnessStatus")} action={<Badge value={harnessProbe.ready ? t("settings.harnessReady") : t("settings.harnessBlocked")} />}>
        <div className="settings-section">
          <div className="settings-copy">
            <h4>{t("settings.harnessStatus")}</h4>
            <p>{t("settings.harnessStatusDescription")}</p>
          </div>
          <div className="settings-control wide">
            <div className="runtime-status-grid">
              <div><span>{t("settings.harnessMode")}</span><strong>{text(harnessProbe.mode, "trusted_dedicated_machine")}</strong></div>
              <div><span>{t("settings.harness")}</span><strong>{text(harnessProbe.provider, runtimeStatus.harness || "unknown")}</strong></div>
              <div><span>{t("settings.harnessSecurity")}</span><strong>{text(harnessProbe.checks?.agent_security_mode, "trusted_dedicated_machine")}</strong></div>
              <div className="runtime-status-wide"><span>{t("settings.harnessCapabilities")}</span><code>{enabledHarnessCapabilities || "—"}</code></div>
              <div className="runtime-status-wide"><span>{t("settings.harnessSecurity")}</span><code className={Object.values(harnessSecurity).some(Boolean) ? "runtime-warning" : "runtime-ok"}>{harnessSecuritySummary || "—"}</code></div>
              {Array.isArray(harnessProbe.warnings) && harnessProbe.warnings.length > 0 && <div className="runtime-status-wide"><span>{t("settings.harnessWarnings")}</span><strong className="runtime-warning">{harnessProbe.warnings.join(" · ")}</strong></div>}
            </div>
          </div>
        </div>
      </Panel>
    <Panel title={t("heading.publishPolicy")}><div className="settings-section"><div className="settings-copy"><h4>{t("settings.automationOutcome")}</h4><p>{t("settings.publishDescription")}</p></div><div className="settings-control wide"><div className="form-grid compact"><Field label={t("label.autoScan")}><select value={scanPublishMode} onChange={(event) => { setScanPublishMode(event.target.value); markDirty(); }}><option value="pr">{t("settings.openPullRequest")}</option><option value="merge">{t("settings.mergeAfterPullRequest")}</option></select></Field><Field label={t("label.autoDelivery")}><select value={deliveryPublishMode} onChange={(event) => { setDeliveryPublishMode(event.target.value); markDirty(); }}><option value="pr">{t("settings.openPullRequest")}</option><option value="merge">{t("settings.mergeAfterPullRequest")}</option><option value="direct">{t("settings.pushDirectly")}</option></select></Field><Field label={t("label.autoPatch")}><select value={patchPublishMode} onChange={(event) => { setPatchPublishMode(event.target.value); markDirty(); }}><option value="pr">{t("settings.openPullRequest")}</option><option value="direct">{t("settings.pushDirectly")}</option></select></Field></div></div></div></Panel>
    <Panel title={t("settings.deploymentTracking")}>
      <div className="settings-section">
        <div className="settings-copy deployment-tracking-copy"><h4>{t("settings.deploymentTracking")}</h4><p>{t("settings.deploymentTrackingDescription")}</p><div className="deployment-policy-note"><span className="field-label">{t("settings.deploymentOwner")}</span><strong>{t("settings.deploymentOwnerValue")}</strong><p>{t("settings.deploymentFailureHandling")}</p></div></div>
        <div className="settings-control wide deployment-settings-control">
          <div className="form-grid compact">
            <Field label={t("settings.deploymentProvider")} help={t("settings.deploymentProviderHelp")}><select value={deploymentProvider} onChange={(event) => { setDeploymentProvider(event.target.value); setDeploymentEnabled(event.target.value !== "none"); markDirty(); }}><option value="none">{t("settings.deploymentDisabled")}</option><option value="jenkins">{t("settings.jenkins")}</option><option value="github_actions">{t("settings.githubActions")}</option></select></Field>
            <Field label={t("settings.deploymentOwner")} help={t("settings.deploymentOwnerHelp")}><div className="settings-static-value">{t("settings.deploymentOwnerValue")}</div></Field>
            <Field label={t("settings.pollInterval")}><input type="number" min="5" value={deploymentPollInterval} onChange={(event) => { setDeploymentPollInterval(event.target.value); markDirty(); }} /></Field>
            <Field label={t("settings.deploymentTimeout")}><input type="number" min="60" value={deploymentTimeout} onChange={(event) => { setDeploymentTimeout(event.target.value); markDirty(); }} /></Field>
            {deploymentProvider === "jenkins" && <><Field label={t("settings.jenkinsPipeline")} help={t("settings.jenkinsPipelineHelp")}><input value={jenkinsJob} placeholder="folder/job-name" onChange={(event) => { setJenkinsJob(event.target.value); markDirty(); }} /></Field><div className="deployment-credentials"><div><span className="field-label">{t("settings.credentials")}</span><span className={`integration-status${jenkinsCredentialsConfigured ? " is-configured" : ""}`}>{jenkinsCredentialsConfigured ? t("settings.configured") : t("settings.notConfigured")}</span></div><code>JENKINS_URL + JENKINS_AUTH</code><p>{t("settings.jenkinsCredentials")}</p></div></>}
            {deploymentProvider === "github_actions" && <><Field label={t("settings.githubRepository")}><input value={githubRepository} placeholder="owner/repository" onChange={(event) => { setGithubRepository(event.target.value); markDirty(); }} /></Field><Field label={t("settings.githubWorkflow")}><input value={githubWorkflow} placeholder="deploy.yml" onChange={(event) => { setGithubWorkflow(event.target.value); markDirty(); }} /></Field><div className="deployment-credentials"><div><span className="field-label">{t("settings.credentials")}</span><span className="integration-status is-configured">{t("settings.localGhLogin")}</span></div><p>{t("settings.githubCredentials")}</p></div></>}
          </div>
        </div>
        <div className="settings-toggle"><ScheduleToggle enabled={deploymentEnabled && deploymentProvider !== "none"} onChange={(enabled) => { setDeploymentEnabled(enabled); markDirty(); }} /></div>
      </div>
    </Panel>
    <Panel title={t("heading.notifications")}><div className="settings-section"><div className="settings-copy"><h4>{t("settings.feishuNotifications")}</h4><p>{t("settings.notificationsDescription")}</p></div><div className="settings-toggle"><ScheduleToggle enabled={feishuEnabled} onChange={(enabled) => { setFeishuEnabled(enabled); markDirty(); }} /></div></div></Panel>
    <Panel title={t("heading.variableKeys")} action={<span className="muted">{t("settings.storedWorkspaceOrLumon")}</span>}><div className="settings-section"><div className="settings-copy"><h4>{t("settings.availableKeys")}</h4><p>{t("settings.availableKeysDescription")}</p></div><div className="settings-control wide"><div className="secret-list">{configured.length ? configured.map((name: string) => { const value = changedSecrets[name] ?? secrets[name] ?? ""; const source = integrationSources[name] === "lumon_local" ? t("settings.storedLumon") : t("settings.storedWorkspace"); return <div className="secret-row" key={name}><span className="secret-name"><code>{name}</code><small>{source}</small></span><input type={secrets[name] || changedSecrets[name] !== undefined ? "text" : "password"} value={value} placeholder={t("settings.revealReplacement")} aria-label={t("common.valueFor", { name })} onChange={(event) => { const next = event.target.value; setChangedSecrets((current) => ({ ...current, [name]: next })); markDirty(); }} /><div><IconButton label={t("common.revealValue")} onClick={() => void reveal(name)}>{secrets[name] ? <EyeOff size={15} /> : <Eye size={15} />}</IconButton><IconButton label={t("common.copyValue")} onClick={() => void copy(name)}><Copy size={15} /></IconButton></div></div>; }) : <Empty label={t("common.noIntegrationKeys")} />}</div></div></div></Panel>
      </section>
    <footer className="settings-save-bar"><span className={dirty ? "settings-save-status unsaved" : "settings-save-status"}>{saving ? t("common.saving") : dirty ? t("settings.unsavedChanges") : t("settings.allSaved")}</span><button className={`button primary${saving ? " is-busy" : ""}`} disabled={!dirty || saving} onClick={() => void saveAll()}>{saving ? <LoaderCircle size={15} className="spin" /> : <Save size={15} />}{saving ? t("common.saving") : t("action.saveChanges")}</button></footer>
  </div>;
}

function ScheduleToggle({ enabled, onChange, label }: { enabled: boolean; onChange: (enabled: boolean) => void; label?: string }) { const { t } = useI18n(); return <label className="schedule-toggle"><input type="checkbox" aria-label={label} checked={enabled} onChange={(event) => onChange(event.target.checked)} /><span aria-hidden="true" /><em>{enabled ? t("common.enabled") : t("common.paused")}</em></label>; }

createRoot(document.getElementById("root")!).render(<DashboardI18nProvider><App /></DashboardI18nProvider>);
