import { memo, useCallback, useEffect, useRef, useState } from "react";
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

const lumenVersion = __LUMEN_VERSION__;

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
  access?: AgentsAccessSettings;
  recent_feishu?: {
    user_ids?: string[];
    chat_ids?: string[];
    users?: FeishuIdentityItem[];
    chats?: FeishuIdentityItem[];
    names?: Record<string, string>;
  };
  pending_questions?: Array<{ question_id?: string; agent_id?: string; action?: string; question?: string; missing?: string[]; created_at?: string; expires_at?: string }>;
  agents?: AgentSettings[];
  test_case?: TestCaseSettings;
}

interface DashboardData extends RecordValue {
  activity?: { available?: boolean; detail?: string; count?: number; items?: RecordValue[] };
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

const tabItems: Array<{ id: Tab; label: string; icon: typeof ScanSearch }> = [
  { id: "overview", label: "OVERVIEW", icon: LayoutDashboard },
  { id: "activity", label: "ACTIVITY", icon: Activity },
  { id: "scan", label: "AUTO SCAN", icon: ScanSearch },
  { id: "delivery", label: "AUTO DELIVERY", icon: Truck },
  { id: "patch", label: "AUTO PATCH", icon: Code2 },
  { id: "observatory", label: "OBSERVATORY", icon: Eye },
  { id: "repositories", label: "REPOSITORY", icon: FolderGit2 },
  { id: "prompts", label: "WORKFLOW", icon: Workflow },
  { id: "settings", label: "SETTINGS", icon: Settings2 }
];

const tabContext: Record<Tab, { title: string; description: string }> = {
  overview: { title: "MANAGER OVERVIEW", description: "Agent ownership, workflow health, and the next human decision." },
  activity: { title: "AGENT ACTIVITY", description: "Conversation records, outcomes, and the evidence behind each Agent turn." },
  scan: { title: "AUTO SCAN", description: "Review history and manage tracked findings." },
  delivery: { title: "AUTO DELIVERY", description: "Story execution, verification, and pull request delivery." },
  patch: { title: "AUTO PATCH", description: "Jira Task and Bug capture, focused fixes, and safe handoff." },
  observatory: { title: "OBSERVATORY", description: "Browse and edit story briefs and technical plans." },
  repositories: { title: "REPOSITORY", description: "Local repositories, automation permissions, and delivery verification policy." },
  prompts: { title: "WORKFLOW", description: "The prompts, scripts, control points, and recovery paths behind each local automation." },
  settings: { title: "SETTINGS", description: "Workspace configuration, scheduling, and local integrations." }
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

const cursorModelOptions = [
  { label: "Auto", value: "auto" },
  { label: "Composer 2.5", value: "composer-2.5" },
  { label: "Cursor Grok 4.5 Medium", value: "cursor-grok-4.5-medium" },
  { label: "Sonnet 4.5", value: "sonnet-4.5" },
  { label: "GPT-5.1 Codex", value: "gpt-5.1-codex" }
];
const customModelOption = "__custom__";

function text(value: unknown, fallback = "—") { return value === undefined || value === null || value === "" ? fallback : String(value); }
function modelValue(value: unknown, fallback = "cursor-grok-4.5-medium") {
  const normalized = String(value ?? "").trim();
  return normalized || fallback;
}
function trimmedModelValue(value: unknown) { return String(value ?? "").trim(); }
function when(value: unknown) {
  if (!value) return "—";
  const date = new Date(String(value));
  return Number.isNaN(date.valueOf()) ? String(value) : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(date);
}
function elapsed(start?: string, end?: string) {
  if (!start || !end) return "—";
  const seconds = Math.round((new Date(end).valueOf() - new Date(start).valueOf()) / 1000);
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}
function durationMs(value: unknown) {
  if (value === undefined || value === null || value === "") return "—";
  const milliseconds = Number(value);
  if (!Number.isFinite(milliseconds)) return "—";
  if (milliseconds < 1000) return `${Math.round(milliseconds)}ms`;
  const seconds = Math.round(milliseconds / 1000);
  return `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}
function statusTone(value: unknown) {
  const normalized = String(value || "unknown").toLowerCase().replaceAll("_", " ");
  if (normalized === "open" || normalized === "reopened" || /(failed|blocked)/.test(normalized)) return "danger";
  if (/(completed|succeeded|clean|passed|resolved|synced|configured|included|available|approved|ready|done|pr open)/.test(normalized)) return "success";
  if (/(progress|running|active|partial|draft|not started)/.test(normalized)) return "info";
  return "neutral";
}
function titleStatus(value: unknown) {
  const raw = text(value, "unknown").toLowerCase().replaceAll("_", " ");
  const labels: Record<string, string> = {
    "completed with findings": "Completed", completed: "Completed", clean: "Completed",
    passed: "Passed", failed: "Failed", skipped: "Skipped", open: "Open",
    "in progress": "In progress", running: "Running", configured: "Active",
    "not configured": "Not set", resolved: "Resolved", reopened: "Reopened", synced: "Synced",
    ignored: "Ignored", blocked: "Blocked", pending: "Pending", active: "Active",
    "pr open": "PR open", "not started": "Not started", "dev done": "Dev done",
    approved: "Approved", ready: "Ready", draft: "Draft", done: "Done", clarifying: "Clarifying", changed: "Changed"
  };
  return labels[raw] || raw.replace(/\b\w/g, (letter) => letter.toUpperCase());
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
  return <div className={`observatory-meta${compact ? " compact" : ""}`}>
    <span className="observatory-meta-item"><em>Business</em><Badge value={business || "draft"} /></span>
    <span className="observatory-meta-item"><em>Technical</em><Badge value={technical || "draft"} /></span>
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
  const businessTone = statusTone(business || "draft");
  const technicalTone = statusTone(technical || "draft");
  const icon = (tone: string) => tone === "success" ? <i className="observatory-status-dot" /> : <CircleDot size={11} />;
  return <div className="observatory-story-status">
    <span className={`observatory-story-status-item ${businessTone}`}>
      {icon(businessTone)}
      Business {titleStatus(business || "draft")}
    </span>
    <span className={`observatory-story-status-item ${technicalTone}`}>
      {icon(technicalTone)}
      Technical {titleStatus(technical || "draft")}
    </span>
  </div>;
}

function FullscreenMedia({ label, onClose, children }: { label: string; onClose: () => void; children: React.ReactNode }) {
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
        <button type="button" className="button secondary" title="Zoom out" aria-label="Zoom out" onClick={() => setZoom((value) => clampZoom(value - FULLSCREEN_ZOOM_STEP))}><ZoomOut size={14} /></button>
        <button type="button" className="button secondary media-fullscreen-zoom-label" title="Reset view" aria-label="Reset view" onClick={resetView}>{Math.round(zoom * 100)}%</button>
        <button type="button" className="button secondary" title="Zoom in" aria-label="Zoom in" onClick={() => setZoom((value) => clampZoom(value + FULLSCREEN_ZOOM_STEP))}><ZoomIn size={14} /></button>
        <button type="button" className="button secondary" onClick={onClose} aria-label="Close fullscreen"><X size={14} /></button>
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
      <button type="button" className="mermaid-fullscreen-btn" title="Show fullscreen" aria-label="Show fullscreen" onClick={() => setFullscreen(true)}><Maximize2 size={14} /></button>
      <div className="mermaid-block" ref={ref} />
    </div>
    {fullscreen && <FullscreenMedia label="Diagram" onClose={() => setFullscreen(false)}>
      <div className="mermaid-block mermaid-block-fullscreen" dangerouslySetInnerHTML={{ __html: mermaidSvgCache.get(chart) || ref.current?.innerHTML || "" }} />
    </FullscreenMedia>}
  </>;
});

function MarkdownImage({ src, alt }: { src?: string; alt?: string }) {
  const [fullscreen, setFullscreen] = useState(false);
  if (!src) return null;
  return <>
    <span className="markdown-image-wrap">
      <button type="button" className="mermaid-fullscreen-btn" title="Show fullscreen" aria-label="Show fullscreen" onClick={() => setFullscreen(true)}><Maximize2 size={14} /></button>
      <img src={src} alt={alt || ""} />
    </span>
    {fullscreen && <FullscreenMedia label={alt || "Image"} onClose={() => setFullscreen(false)}>
      <img src={src} alt={alt || ""} />
    </FullscreenMedia>}
  </>;
}

function CodeFence({ className, children }: { className?: string; children?: React.ReactNode }) {
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
        title="Copy code"
        aria-label="Copy code"
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
    button.title = "Copy code";
    button.setAttribute("aria-label", "Copy code");
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
    return `\n\n<div class="mermaid-wrap" contenteditable="false" data-mm-id="${id}"><button type="button" class="mermaid-fullscreen-btn" data-mm-fullscreen title="Show fullscreen" aria-label="Show fullscreen"></button><div class="mermaid-block" data-mm-host></div></div>\n\n`;
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
      button.title = "Show fullscreen";
      button.setAttribute("aria-label", "Show fullscreen");
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
  }, []);
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
    const href = window.prompt(existing ? "Edit link URL" : "Link URL", current);
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
    <div className="observatory-toolbar" role="toolbar" aria-label="Formatting tools">
      <button type="button" title="Heading" onMouseDown={(event) => event.preventDefault()} onClick={() => run("formatBlock", "h2")}><Heading2 size={14} /></button>
      <button type="button" title="Bold" onMouseDown={(event) => event.preventDefault()} onClick={() => run("bold")}><Bold size={14} /></button>
      <button type="button" title="Italic" onMouseDown={(event) => event.preventDefault()} onClick={() => run("italic")}><Italic size={14} /></button>
      <button type="button" title="Link — Shift+click a link to place the caret, then edit" onMouseDown={(event) => event.preventDefault()} onClick={editOrCreateLink}><Link2 size={14} /></button>
      <button type="button" title="List" onMouseDown={(event) => event.preventDefault()} onClick={() => run("insertUnorderedList")}><List size={14} /></button>
      <button type="button" title="Code" onMouseDown={(event) => event.preventDefault()} onClick={() => run("formatBlock", "pre")}><Code2 size={14} /></button>
    </div>
    <div className="observatory-doc-preview-wrap">
      <button
        type="button"
        className="observatory-doc-fullscreen-btn"
        title={docFullscreen ? "Exit fullscreen" : "Fullscreen"}
        aria-label={docFullscreen ? "Exit fullscreen" : "Fullscreen"}
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
        aria-label="Document body"
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
    {fullscreen && <FullscreenMedia label={fullscreen.kind === "img" ? (fullscreen.alt || "Image") : "Diagram"} onClose={() => setFullscreen(null)}>
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
  const initialProject = new URLSearchParams(window.location.search).get("project") || window.DASHBOARD_DATA?.interactive?.project || "";
  const [project, setProject] = useState(initialProject);
  const [data, setData] = useState<DashboardData | null>(null);
  const pathTab = (tabItems.find((item) => `/${item.id}` === window.location.pathname)?.id || "overview") as Tab;
  const [activeTab, setActiveTab] = useState<Tab>(pathTab);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.localStorage.getItem("lumen-sidebar-collapsed") === "true");
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
        setError("Static report mode: interactive actions are unavailable.");
      }
      else setError(err instanceof Error ? err.message : "Unable to load Dashboard state");
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
  useEffect(() => { window.localStorage.setItem("lumen-sidebar-collapsed", String(sidebarCollapsed)); }, [sidebarCollapsed]);
  useEffect(() => { const onPopState = () => setActiveTab((tabItems.find((item) => `/${item.id}` === window.location.pathname)?.id || "scan") as Tab); window.addEventListener("popstate", onPopState); return () => window.removeEventListener("popstate", onPopState); }, []);

  const confirmLeaveUnsaved = () => {
    if (settingsDirty && !window.confirm("You have unsaved Settings changes. Leave without saving?")) return false;
    if (observatoryDirty && !window.confirm("You have unsaved Observatory changes. Leave without saving?")) return false;
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
    catch (err) { notify(err instanceof Error ? err.message : "Request failed", "error"); return false; }
  };
  const projects = data?.interactive?.projects || [];
  const tagline = data?.product?.tagline || "Engineering, made legible.";
  const context = tabContext[activeTab];

  return <main className={`dashboard-layout ${sidebarCollapsed ? "sidebar-is-collapsed" : ""}`}>
    <aside className="sidebar" aria-label="Lumen navigation">
      <div className="sidebar-brand">
        <img src="assets/lumen-mark.png" className="brand-mark" alt="Lumen" />
        <div className="sidebar-brand-copy"><strong>Lumen</strong><span>{tagline}</span></div>
      </div>
      <nav className="side-nav" aria-label="Dashboard sections">{tabItems.map((item) => { const Icon = item.icon; return <button title={item.label} className={activeTab === item.id ? "active" : ""} onClick={() => changeTab(item.id)} key={item.id}><Icon size={17} /><span>{item.label}</span></button>; })}</nav>
      <div className="sidebar-foot">
        {!sidebarCollapsed && <img src="assets/inspire-group-logo.png" className="company-mark" alt="INSPIRE GROUP" />}
        <small>{sidebarCollapsed ? `V${lumenVersion}` : `Version ${lumenVersion}`}</small>
      </div>
    </aside>
    <button type="button" className="icon-button sidebar-toggle" title={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"} aria-label={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"} onPointerDown={(event) => { event.preventDefault(); event.stopPropagation(); setSidebarCollapsed((value) => !value); }}>{sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}</button>
    <section className="content-area">
      <header className="masthead">
        <div className="masthead-context"><strong>{context.title}</strong><span>{context.description}</span></div>
        <div className="masthead-actions"><span className="last-updated">{lastUpdated ? `Updated ${when(lastUpdated.toISOString())}` : "Syncing…"}</span><label className="project-picker"><span>Project</span><select value={project} onChange={(event) => changeProject(event.target.value)}>{projects.map((item) => <option value={item.slug} key={item.slug}>{item.name}</option>)}</select><ChevronDown size={15} /></label></div>
      </header>
      <div className="page-content" key={activeTab}>
        {error && <div className="status-note"><Activity size={15} />{error}</div>}
        {!data && loading ? <div className="loading-state"><LoaderCircle size={22} className="spin" /> Loading local workspace state…</div> : null}
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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const overwrite = async () => {
    setBusy(true); setError("");
    try {
      await request("/api/git-sync/force", project, { method: "POST", json: {} });
      notify("Remote branch overwritten with the local Lumen commit", "success");
      onClose();
      await onResolved();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to overwrite the remote branch";
      setError(message);
    } finally { setBusy(false); }
  };
  return <div className="modal-backdrop" role="presentation"><section className="modal git-sync-conflict-modal" role="dialog" aria-modal="true" aria-label="Git sync conflict"><div className="modal-body compact"><strong>Remote updates need your decision</strong><p className="modal-copy">Lumen committed local workspace changes, but the remote {conflict.branch || "branch"} changed before the push. Review the remote changes before choosing whether to overwrite them.</p><div className="git-sync-conflict-details"><span>Repository</span><code>{conflict.repo || "Workspace"}</code><span>Local commit</span><code>{conflict.local_oid || "—"}</code></div>{error && <p className="git-sync-error" role="alert">{error}</p>}</div><footer><button className="button" disabled={busy} onClick={onClose}>Later</button><button className="button danger" disabled={busy} onClick={() => void overwrite()}>{busy ? "Overwriting…" : "Overwrite remote"}</button></footer></section></div>;
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

function OverviewView({ data, project, onNavigate }: { data: DashboardData; project: string; onNavigate: (tab: Tab) => void }) {
  const settings = data.interactive?.agents || {};
  const agents = settings.agents || [];
  const pending = settings.pending_questions || [];
  const workflows = workflowProfiles.map((profile) => ({
    ...profile,
    status: profile.workflow === "auto_scan" ? data.runs?.[0]?.status || "not started" : profile.workflow === "auto_delivery" ? data.delivery?.current?.delivery_status || "not started" : data.patch?.current?.patch_status || "not started",
  }));
  const agentState = (agent: AgentSettings) => {
    if (!agent.app_id || !agent.app_secret_configured) return "setup";
    if (!agent.conversation_enabled) return "paused";
    return "ready";
  };
  const readyAgents = agents.filter((agent) => agentState(agent) === "ready").length;
  const activeWorkflows = workflows.filter((workflow) => /running|progress|active/i.test(String(workflow.status))).length;
  const stateLabel = (state: string) => state === "setup" ? "not configured" : state;
  return <div className="manager-overview">
    <PageIntro title="Manager overview" description={`${project || "Current project"} · one place to see Agent ownership, workflow health, and the next decision.`} action={<button className="button secondary" onClick={() => onNavigate("settings")}><Settings2 size={14} />Open Settings</button>} />
    <div className="metrics">
      <Metric label="Agents ready" value={`${readyAgents}/${agents.length}`} />
      <Metric label="Workflows active" value={activeWorkflows} />
      <Metric label="Questions waiting" value={pending.length} />
      <Metric label="Gateway" value={settings.enabled ? "Enabled" : "Paused"} />
    </div>
    <Panel title="Agent roster" action={<span className="muted">{agents.length} roles · shared runtime</span>}>
      <div className="agent-roster">
        {agents.length ? agents.map((agent) => {
          const state = agentState(agent);
          const profile = workflowProfile(agent.workflow) || managerProfile;
          const workflow = workflowProfiles.find((item) => item.workflow === agent.workflow)?.tab;
          return <article className="agent-card" key={agent.id}>
            <div className="agent-card-heading"><div><span className="overview-kicker">{profile.feature}</span><h4>{agent.display_name}</h4><p>{profile.mission}</p></div><Badge value={stateLabel(state)} /></div>
            <div className="agent-card-facts"><div><span>Owns</span><strong title={profile.feature}>{profile.feature}</strong></div><div><span>Receives</span><strong title={profile.input}>{profile.input}</strong></div><div><span>Returns</span><strong title={profile.output}>{profile.output}</strong></div></div>
            <div className="agent-card-footer"><span>{state === "ready" ? "Conversation and actions available" : state === "paused" ? "Conversation is paused in Settings" : "Credentials are required"}</span>{workflow ? <button className="text-button" onClick={() => onNavigate("activity")}>View activity <ChevronRight size={13} /></button> : <span className="overview-manager-label">Manager</span>}</div>
          </article>;
        }) : <Empty label="No Agent roles available yet." />}
      </div>
    </Panel>
    <Panel title="Workflow control" action={<span className="muted">Three human-owned capabilities</span>}>
      <div className="workflow-roster">
        {workflows.map((workflow) => <article className="workflow-card" key={workflow.workflow}>
          <div className="workflow-card-heading"><div><span className="overview-kicker">{workflow.agent}</span><h4>{workflow.feature}</h4></div><Badge value={workflow.status} /></div>
          <p>{workflow.mission}</p>
          <div className="workflow-card-io"><span><b>Input</b>{workflow.input}</span><span><b>Output</b>{workflow.output}</span></div>
          <button className="button secondary" onClick={() => onNavigate(workflow.tab)}>Inspect {workflow.feature} <ChevronRight size={13} /></button>
        </article>)}
      </div>
    </Panel>
    <Panel title="Questions waiting for you" action={<span className="muted">{pending.length ? `${pending.length} unanswered` : "Conversation is clear"}</span>}>
      {pending.length ? <div className="pending-question-list">{pending.map((question, index) => <article className="pending-question" key={question.question_id || `${question.agent_id}-${index}`}><div className="pending-question-heading"><div><span className="overview-kicker">{text(question.agent_id, "Agent")}</span><strong>{text(question.action, "Clarification")}</strong></div><time>{when(question.created_at)}</time></div><p>{text(question.question, "The Agent needs one more decision before continuing.")}</p></article>)}</div> : <div className="overview-empty"><CircleHelp size={17} />No unanswered Agent questions.</div>}
    </Panel>
  </div>;
}

function ActivityView({ data, project, onNavigate }: { data: DashboardData; project: string; onNavigate: (tab: Tab) => void }) {
  const records = data.activity?.items || [];
  const [agentFilter, setAgentFilter] = useState("all");
  const visible = records.filter((record) => agentFilter === "all" || String(record.agent_id || "") === agentFilter);
  const roles = Array.from(new Set(records.map((record) => String(record.agent_id || "")).filter(Boolean)));
  const completed = records.filter((record) => /completed|success|delegated/i.test(String(record.status || ""))).length;
  const attention = records.filter((record) => /failed|blocked|denied/i.test(String(record.status || ""))).length;
  const profileFor = (record: RecordValue) => workflowProfile(String(record.workflow || "")) || _AGENT_ACTIVITY_UI_PROFILES[String(record.agent_id || "")] || managerProfile;
  return <div className="activity-page">
    <PageIntro title="Agent activity" description={`${project || "Current project"} · one readable record for every conversation, handoff, and result.`} action={<button className="button secondary" onClick={() => onNavigate("settings")}><Settings2 size={14} />Manage capture</button>} />
    <div className="activity-role-guide">
      {[...workflowProfiles, managerProfile].map((profile) => <article key={profile.workflow}>
        <span className="activity-role-dot" aria-hidden="true" />
        <div><strong>{profile.agent} · {profile.feature}</strong><p>{profile.mission}</p></div>
      </article>)}
    </div>
    <div className="metrics activity-metrics">
      <Metric label="Recorded turns" value={records.length} />
      <Metric label="Completed" value={completed} />
      <Metric label="Needs attention" value={attention} />
      <Metric label="Roles seen" value={roles.length} />
    </div>
    <Panel title="Conversation records" action={<div className="activity-toolbar"><span className="muted">{visible.length} shown</span><label><span>Role</span><select aria-label="Filter activity by role" value={agentFilter} onChange={(event) => setAgentFilter(event.target.value)}><option value="all">All roles</option>{roles.map((agent) => <option value={agent} key={agent}>{String(records.find((record) => String(record.agent_id || "") === agent)?.display_name || agent)}</option>)}</select></label></div>}>
      {!data.activity?.available && <div className="activity-note"><Activity size={15} />{text(data.activity?.detail, "No Agent conversation store is available yet. New Feishu conversations will appear here after the gateway starts.")}</div>}
      {visible.length ? <div className="activity-record-list">{visible.map((record) => {
        const profile = profileFor(record);
        const workflow = workflowProfiles.find((item) => item.workflow === record.workflow);
        const requestText = String(record.request_text || "").trim();
        const responseText = String(record.response_text || "").trim();
        const sourceLabel = record.source === "conversation" ? "Request + result" : record.source === "outcome" ? "Result captured · request predates transcript capture" : "Trace only";
        const timeline = Array.isArray(record.timeline) ? record.timeline : [];
        return <article className="activity-record" key={String(record.trace_id || `${record.agent_id}-${record.started_at}`)}>
          <header className="activity-record-header"><div className="activity-record-identity"><span className={`activity-avatar activity-avatar-${String(record.agent_id || "agent")}`} aria-hidden="true">{String(record.display_name || profile.agent || "A").slice(0, 1)}</span><div><span className="overview-kicker">{profile.feature}</span><h4>{text(record.display_name, profile.agent)}</h4><p>{text(record.action, sourceLabel)}</p></div></div><div className="activity-record-status"><Badge value={text(record.status, "unknown")} /><time>{when(record.started_at)}</time></div></header>
          <div className="activity-thread">
            <div className="activity-message user"><span>You</span><p>{requestText || "This older trace has an outcome, but its incoming message was not captured by that runtime version."}</p></div>
            <div className="activity-message agent"><span>{text(record.display_name, profile.agent)}</span><p>{responseText || "No final response text was retained; open the source trace in the Agent logs if deeper evidence is needed."}</p></div>
          </div>
          <footer className="activity-record-footer"><span>{sourceLabel}</span><span>Trace <code>{text(record.trace_id)}</code></span><span>{record.latency_ms ? `${record.latency_ms} ms` : `${record.event_count || 0} events`}</span>{workflow && <button className="text-button" onClick={() => onNavigate(workflow.tab)}>Open {workflow.feature} <ChevronRight size={13} /></button>}</footer>
          {timeline.length > 0 && <details className="activity-trail"><summary>Execution trail</summary><div>{timeline.map((event: RecordValue, index: number) => <p key={`${event.event}-${index}`}><time>{when(event.at)}</time><strong>{text(event.event)}</strong>{event.detail && <span>{text(event.detail)}</span>}</p>)}</div></details>}
        </article>;
      })}</div> : <div className="activity-empty"><MessageCirclePlaceholder /><strong>No conversation records match this filter.</strong><span>{data.activity?.available ? "Ask one of the Agents in Feishu, then refresh this page." : "The local activity store will be created by the first Agent turn."}</span></div>}
    </Panel>
    <p className="activity-retention-note">Only bounded local request/result text is shown here. Trace IDs and raw execution evidence remain available in the local Agent store.</p>
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
        ? `Dashboard is still running an older version. Run \`lumen dashboard stop --project ${project}\`, then open the dashboard again.`
        : message;
      setScanError(detail);
      notify(detail, "error");
    } finally {
      setScanBusy(false);
    }
  };
  return <>
    <section className="metrics"><Metric label="Open findings" value={openIssues.length} onClick={jumpToFindings} /><Metric label="Successful Scan · 7d" value={stats.success_7d || 0} /><Metric label="Failed · 7d" value={stats.failed_7d || 0} /><Metric label="Lookback window" value={`${data.scan_window_days || 7}d`} /></section>
    <Panel title="Scan History" action={<span className="panel-actions"><button type="button" className="button secondary" disabled={scanBusy} onClick={() => { setScanError(""); setScanStep(1); }}><Play size={14} />Start scan</button><span className="muted">{runs.length} runs</span></span>}><div className="table-scroll"><table><thead><tr><th>Started</th><th>Status</th><th>Issues</th><th>Duration</th><th>Artifacts</th></tr></thead><tbody>{pageRuns.map((run: RecordValue) => <tr key={run.id}><td>{when(run.started_at || run.finished_at)}</td><td><Badge value={run.status} /></td><td><SeverityBreakdown run={run} /></td><td>{text(run.duration)}</td><td><div className="artifact-links">{run.html && <a href={`${run.html}?project=${encodeURIComponent(project)}`} target="_blank">HTML</a>}{run.pdf && <a href={`${run.pdf}?project=${encodeURIComponent(project)}`} target="_blank">PDF</a>}{!run.html && !run.pdf && "—"}</div></td></tr>)}</tbody></table></div>{runs.length > runPageSize && <Pagination page={runPage} pageCount={Math.ceil(runs.length / runPageSize)} onChange={setRunPage} />}</Panel>
    <Panel title="Tracked Findings" action={<span className="muted">{filteredIssues.length} of {issues.length} records</span>}><div className="finding-filters" role="tablist">{(["all", "open", "resolved", "ignored"] as const).map((value) => <button className={filter === value ? "active" : ""} onClick={() => setFilter(value)} key={value}>{value === "all" ? "All" : titleStatus(value)} <span>{counts[value]}</span></button>)}</div><div id="tracked-findings" className="findings">{filteredIssues.length ? filteredIssues.map((issue: RecordValue) => <Finding issue={issue} onIgnore={() => setIgnoreCandidate(issue)} key={issue.id} />) : <Empty label="No findings match this status." />}</div></Panel>
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
  const first = step === 1;
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={first ? "Start scan" : "Confirm start scan"} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>{first ? "Start a scan?" : "Confirm scan start"}</strong><p className="modal-copy">{first ? `This will launch an auto-scan for ${project}.` : `Are you sure you want to start a scan for ${project} now? A scan agent will run against the configured repositories.`}</p>{error && <p className="status-note">{error}</p>}</div><footer><button className="button" disabled={busy} onClick={onClose}>Cancel</button>{first ? <button className="button primary" disabled={busy} onClick={onContinue}>Continue</button> : <button className="button primary" disabled={busy} onClick={onConfirm}><Play size={14} />{busy ? "Starting…" : "Start scan"}</button>}</footer></section></div>;
}

function Metric({ label, value, onClick }: { label: string; value: string | number; onClick?: () => void }) { return <div className={`metric ${onClick ? "metric-action" : ""}`} onClick={onClick} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined} onKeyDown={(event) => { if (onClick && (event.key === "Enter" || event.key === " ")) onClick(); }}><span>{label}</span><strong>{value}</strong></div>; }
function Empty({ label }: { label: string }) { return <div className="empty"><ShieldCheck size={20} />{label}</div>; }
function SeverityBreakdown({ run }: { run: RecordValue }) {
  const levels = [["High", Number(run.high || 0), "high"], ["Medium", Number(run.medium || 0), "medium"], ["Low", Number(run.low || 0), "low"]] as const;
  const present = levels.filter(([, count]) => count > 0);
  return present.length ? <span className="severity-breakdown">{present.map(([label, count, tone]) => <b className={tone} key={label}>{label}: {count}</b>)}</span> : <>—</>;
}
function Pagination({ page, pageCount, onChange }: { page: number; pageCount: number; onChange: (page: number) => void }) { return <footer className="pagination"><span>Page {page + 1} of {pageCount}</span><div><button className="button secondary" disabled={page === 0} onClick={() => onChange(page - 1)}>Previous</button><button className="button secondary" disabled={page === pageCount - 1} onClick={() => onChange(page + 1)}>Next</button></div></footer>; }
function Finding({ issue, onIgnore }: { issue: RecordValue; onIgnore: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const status = issue.status || issue.issue_status || "open";
  const statusKey = String(status).toLowerCase();
  const isIgnorable = !["ignored", "resolved"].includes(statusKey);
  const primaryId = text(issue.jira_key) || text(issue.id);
  return <article className="finding"><div className="finding-main"><div className="finding-copy"><div className="finding-heading"><h4>{text(issue.title, "Untitled finding")}</h4><Badge value={status} /></div><p className="finding-meta"><code className="finding-id">{primaryId}</code><i>|</i>{text(issue.repository, "Unknown repository")} <i>|</i> {when(issue.last_seen_at)}</p><div className="finding-links finding-row-links"><button className="finding-link" onClick={() => setExpanded(!expanded)}>{expanded ? "Hide detail" : "View detail"}</button>{issue.jira_key && issue.jira_url && <a className="finding-link" href={issue.jira_url} target="_blank" rel="noreferrer">{issue.jira_key}<ExternalLink size={12} /></a>}{issue.pr_url && <a className="finding-link" href={issue.pr_url} target="_blank" rel="noreferrer">Pull request<ExternalLink size={12} /></a>}</div></div><div className="finding-actions">{isIgnorable && <button className="button secondary" onClick={onIgnore}>Mark ignored</button>}</div></div>{expanded && <div className="finding-detail"><FindingDetail label="Status" value={titleStatus(status)} /><FindingDetail label="Resolution basis" value={issue.resolution_basis_label || issue.resolution_basis} /><FindingDetail label="Verification" value={issue.verification_label || issue.verification_status} /><FindingDetail label="Resolved by" value={issue.resolved_by} /><FindingDetail label="Resolved at" value={when(issue.resolved_at)} /><FindingDetail label="Last verification" value={when(issue.last_verified_at)} /><FindingDetail label="Impact" value={issue.impact} /><FindingDetail label="Trigger" value={issue.trigger} /><FindingDetail label="Root cause" value={issue.root_cause} /><FindingDetail label="Code" value={issue.code_snippet} code /><FindingDetail label="Recommended correction" value={issue.suggestion} /><FindingDetail label="Validation" value={issue.validation} /><FindingDetail label="Risk Finding ID" value={issue.risk_finding_id} /><FindingDetail label="Legacy Issue ID" value={issue.id} /><FindingDetail label="Status source" value={issue.status_source} /></div>}</article>;
}

function FindingDetail({ label, value, code = false }: { label: string; value: unknown; code?: boolean }) { return <section className="finding-detail-row"><h5>{label}</h5>{code ? <pre><code>{text(value, "No code snippet was captured for this historical finding.")}</code></pre> : <p>{text(value, "Not recorded.")}</p>}</section>; }
function IgnoreDialog({ onClose, onConfirm }: { onClose: () => void; onConfirm: (reason: string) => void }) {
  const [reason, setReason] = useState("");
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal" role="dialog" aria-modal="true" aria-label="Ignore finding" onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>Mark this finding as ignored?</strong><Field label="Reason (optional)"><textarea className="ignore-reason" rows={2} autoFocus value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Why is this safe to ignore?" /></Field></div><footer><button className="button" onClick={onClose}>Cancel</button><button className="button primary" onClick={() => onConfirm(reason)}>Mark ignored</button></footer></section></div>;
}

function DeliveryView({ data, project, notify, reload }: { data: DashboardData; project: string; notify: Notify; reload: () => Promise<void> }) {
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
  const running = /in_progress|running/i.test(String(current.delivery_status || ""));
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
    catch (err) { const message = err instanceof Error ? err.message : "Unable to retry delivery"; setRetryError(message === "Not found" ? "Dashboard is still running an older version. Run `lumen dashboard stop --project …`, then open the dashboard again." : message); }
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
    <Panel title="Current Progress" className="delivery-summary" action={<span className="panel-actions">{canStart && <button className="button secondary" disabled={actionBusy} onClick={openStart}><Play size={14} />Start</button>}{running && <button className="button danger secondary" disabled={actionBusy} onClick={() => void stop()}>Stop</button>}{canRetry && <button className="button secondary" onClick={() => setRetryOpen(true)}><RotateCcw size={14} />Retry</button>}</span>}><div className="delivery-facts"><Fact label="Current story" value={<StoryReference jiraKey={current.jira_key || current.story_id} title={current.story_title} />} /><Fact label="Status" value={<Badge value={current.delivery_status || "not started"} />} /><Fact label="Elapsed" value={elapsed(current.started_at, current.finished_at || (running ? new Date(now).toISOString() : undefined))} /><Fact label="Finished" value={running ? "Running" : when(current.finished_at)} /></div>{actionError && <div className="status-note">{actionError}</div>}<DeliveryFlow stages={stages} deliveryStatus={String(current.delivery_status || "")} currentStep={String(current.current_step || "")} startedAt={current.started_at} finishedAt={current.finished_at} remediation={current.remediation} now={now} onStageClick={openStage} /></Panel>
    <Panel title="Delivery History" className="history-panel" action={<span className="muted">{runs.length} runs</span>}><div className="table-scroll"><table><thead><tr><th>Story</th><th>Finished</th><th>Status</th><th>Pull requests</th><th>Checks</th><th>Duration</th><th>Trace</th><th>Operation</th></tr></thead><tbody>{runs.length ? runs.map((run: RecordValue) => { const runChecks = run.verification || []; const failed = runChecks.filter((item: RecordValue) => item.status === "failed"); const canInspectStatus = failed.length || /failed|blocked/i.test(String(run.status)); return <tr key={run.run_id}><td><div className="history-story"><span className="history-story-line"><code>{text(run.jira_key || run.story || run.run_id)}</code>{run.story_title && <span className="history-story-title">{run.story_title}</span>}</span><small>{text(run.branch, "")}</small></div></td><td>{when(run.finished_at || run.started_at)}</td><td>{canInspectStatus ? <button className="status-badge-button" title="Open failure log" onClick={() => void openStage({ label: "Delivery failure", duration: elapsed(run.started_at, run.finished_at), detail: failed.map((item: RecordValue) => item.summary || item.label).filter(Boolean).join(" · ") || "Open the delivery log for details." }, run.run_id)}><Badge value={run.status} /></button> : <Badge value={run.status} />}</td><td><PrLinks items={run.pull_requests || []} /></td><td><VerificationSummary checks={runChecks} onClick={() => setSelectedChecks(runChecks)} /></td><td>{elapsed(run.started_at, run.finished_at)}</td><td>{run.agent_trace && <button className="text-button" onClick={() => void openTrace(run.run_id)}>View trace</button>}</td><td><IconButton label="Delete delivery record" danger disabled={deletingHistoryId === run.run_id} onClick={() => setDeleteCandidate(run)}><Trash2 size={15} /></IconButton></td></tr>; }) : <tr><td colSpan={8}><Empty label="No delivery history yet." /></td></tr>}</tbody></table></div></Panel>
    <Panel title="Scheduler Activity" action={<span className="panel-actions"><span className="muted">{schedulerActivity.length} recent events</span>{delivery.scheduler_log_available && <button className="button secondary" onClick={() => void openSchedulerLog()}><Terminal size={14} />View raw log</button>}</span>}><div className="scheduler-activity">{schedulerActivity.length ? schedulerActivity.map((event: RecordValue, index: number) => <article className="scheduler-event" key={`${event.at}-${index}`}><Badge value={event.outcome} /><div><strong>{text(event.story_id || event.jira_key, "Workspace")}</strong><p>{text(event.message)}</p></div><time>{when(event.at)}</time></article>) : <Empty label="No scheduled delivery activity recorded yet." />}</div></Panel>
    {selectedStage && <DeliveryLogDialog stage={selectedStage} content={logContent} error={logError} loading={loadingLog} live={selectedLogIsLive} onClose={() => setSelectedStage(null)} />}
    {schedulerLogOpen && <DeliveryLogDialog stage={{ label: "Scheduler log", duration: "Recent raw output", detail: "Launchd output is capped at 256 KiB; structured activity retains the latest 200 events." }} content={logContent} error={logError} loading={loadingLog} onClose={() => setSchedulerLogOpen(false)} />}
    {selectedChecks && <VerificationDialog checks={selectedChecks} onClose={() => setSelectedChecks(null)} />}
    {retryOpen && <RetryDeliveryDialog story={text(current.jira_key || current.story_id)} busy={retrying} error={retryError} onClose={() => setRetryOpen(false)} onConfirm={() => void retry()} />}
    {startStep > 0 && <StartDeliveryDialog stories={storyOptions} value={selectedStory} onChange={setSelectedStory} step={startStep === 1 ? 1 : 2} busy={actionBusy} error={actionError} onClose={() => { if (!actionBusy) setStartStep(0); }} onContinue={() => setStartStep(2)} onConfirm={() => void start()} />}
    {deleteCandidate && <DeleteHistoryDialog run={deleteCandidate} busy={Boolean(deletingHistoryId)} onClose={() => setDeleteCandidate(null)} onConfirm={() => void removeHistory()} />}
  </>;
}

function PatchView({ data, project, notify, reload }: { data: DashboardData; project: string; notify: Notify; reload: () => Promise<void> }) {
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
    <Panel title="Current Progress" action={<span className="panel-actions">{running ? <button className="button danger secondary" disabled={busy} onClick={() => void stop()}>Stop</button> : <button className="button secondary" disabled={busy} onClick={() => void openCandidates()}><Play size={14} />Run one cycle</button>}</span>}>
      <div className="delivery-facts"><Fact label="Jira card" value={<StoryReference jiraKey={current.jira_key} title={current.jira_summary} />} /><Fact label="Status" value={<Badge value={current.patch_status || "not started"} />} /><Fact label="Branch" value={<code>{text(current.branch)}</code>} /><Fact label="Repositories" value={Array.isArray(current.repositories) ? current.repositories.map((item: RecordValue) => item.name).filter(Boolean).join(", ") || "—" : "—"} /></div>
      {current.question && <div className="status-note"><CircleHelp size={15} />{current.question}</div>}
      <PatchFlow phases={Array.isArray(current.stages) ? current.stages : []} overallStatus={String(current.patch_status || "")} />
    </Panel>
    <Panel title="Patch History" action={<span className="muted">{runs.length} runs</span>}>{historyError && <div className="status-note">{historyError}</div>}<div className="table-scroll patch-history-scroll"><table className="patch-history-table"><thead><tr><th>Jira</th><th>Summary</th><th>Status</th><th>Repositories</th><th>Finished</th><th>Log</th><th>Operation</th></tr></thead><tbody>{runs.length ? runs.map((run: RecordValue) => <tr key={run.run_id}><td><div className="patch-history-jira"><span className="patch-history-key">{text(run.jira_key)}</span>{run.jira_summary && <span className="patch-history-jira-title" title={text(run.jira_summary)}>{text(run.jira_summary)}</span>}</div></td><td><span className="patch-history-summary" title={text(run.summary)}>{text(run.summary)}</span></td><td><Badge value={run.status} /></td><td>{(run.repositories || []).map((item: RecordValue) => item.name).filter(Boolean).join(", ") || "—"}</td><td><span className="patch-history-finished">{when(run.finished_at)}</span></td><td><button className="text-button" onClick={() => void loadLog(run.run_id)}>View log</button></td><td><IconButton label="Delete Auto Patch record" danger disabled={deletingHistoryId === run.run_id} onClick={() => setDeleteCandidate(run)}><Trash2 size={15} /></IconButton></td></tr>) : <tr><td colSpan={7}><Empty label="No Auto Patch history yet." /></td></tr>}</tbody></table></div></Panel>
    <Panel title="Scheduler Activity"><div className="scheduler-activity">{activity.length ? activity.map((event: RecordValue, index: number) => <article className="scheduler-event" key={`${event.at}-${index}`}><Badge value={event.outcome} /><div><strong>{text(event.jira_key || event.card, "Workspace")}</strong><p>{text(event.message)}</p></div><time>{when(event.at)}</time></article>) : <Empty label="No Auto Patch activity recorded yet." />}</div></Panel>
    {candidateOpen && <PatchCandidateDialog candidates={candidates} selected={selectedCandidate} loading={candidateLoading} error={candidateError} busy={busy} onChange={setSelectedCandidate} onClose={() => { if (!busy) setCandidateOpen(false); }} onConfirm={() => void start(selectedCandidate)} />}
    {logOpen && <DeliveryLogDialog stage={{ label: "Auto Patch log", detail: "Recent Auto Patch agent output" }} content={log} error={logError} loading={!log && !logError} onClose={() => setLogOpen(false)} />}
    {deleteCandidate && <DeleteHistoryDialog kind="patch" run={deleteCandidate} busy={Boolean(deletingHistoryId)} onClose={() => setDeleteCandidate(null)} onConfirm={() => void removeHistory()} />}
  </>;
}

function PatchCandidateDialog({ candidates, selected, loading, error, busy, onChange, onClose, onConfirm }: { candidates: RecordValue[]; selected: string; loading: boolean; error: string; busy: boolean; onChange: (value: string) => void; onClose: () => void; onConfirm: () => void }) {
  const available = candidates.filter((candidate) => candidate.available);
  const empty = !loading && !error && !candidates.length;
  const unavailable = !loading && Boolean(error);
  const title = loading ? "Scanning the active sprint" : unavailable ? "Auto Patch scan unavailable" : empty ? "No Jira cards to patch" : "Choose a Jira card to patch";
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal patch-candidate-modal" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>{title}</strong><p className="modal-copy">Only Task and Bug cards in the current active sprint are shown.</p>{loading && <div className="patch-candidate-empty">Scanning the active sprint…</div>}{unavailable && <div className="patch-candidate-error"><CircleAlert size={17} /><div><strong>Unable to scan Jira cards</strong><p>{error}</p></div></div>}{empty && <div className="patch-candidate-empty">No pending Auto Patch Jira cards were found in the current active sprint.</div>}{!loading && !error && candidates.length > 0 && <div className="patch-candidate-list">{candidates.map((candidate: RecordValue) => { const key = String(candidate.jira_key || ""); const disabled = !candidate.available; return <label className={`patch-candidate-option${selected === key ? " selected" : ""}${disabled ? " disabled" : ""}`} key={key}><input type="radio" name="patch-candidate" value={key} checked={selected === key} disabled={disabled || busy} onChange={() => onChange(key)} /><span><strong>{key} · {text(candidate.summary)}</strong><small>{text(candidate.issue_type, "Task")} · {text(candidate.status, "Unknown status")}{candidate.priority ? ` · Priority ${candidate.priority}` : ""}</small>{candidate.reason && <em>{candidate.reason}</em>}</span></label>; })}</div>}</div><footer><button className="button" disabled={busy} onClick={onClose}>Close</button>{!empty && !unavailable && <button className="button primary" disabled={busy || !selected || available.length === 0} onClick={onConfirm}><Play size={14} />{busy ? "Starting…" : "Start patch"}</button>}</footer></section></div>;
}

function PatchFlow({ phases, overallStatus }: { phases: RecordValue[]; overallStatus: string }) {
  const visiblePhases = phases.filter((phase) => !["screen", "context"].includes(String(phase.id || "").toLowerCase()));
  const skipped = String(overallStatus).toLowerCase() === "skipped";
  const completed = visiblePhases.filter((phase) => phase.status === "completed").length;
  const trackWidth = skipped
    ? visiblePhases.length > 1 ? Math.round(Math.max(completed - 1, 0) / (visiblePhases.length - 1) * 100) : 0
    : visiblePhases.length ? Math.round(completed / visiblePhases.length * 100) : 0;
  return <div className="delivery-flow patch-flow"><div className="flow-heading"><div><span className="flow-title">Patch Flow</span></div><p>Capture → repository → patch → publish</p></div><div className="flow-track-wrap"><span className="flow-track"><i style={{ width: `${trackWidth}%` }} /></span><ol className="flow-steps" style={{ "--flow-count": Math.max(visiblePhases.length, 1) } as React.CSSProperties}>{visiblePhases.map((phase, index) => { const status = String(phase.status || "pending").toLowerCase(); const state = skipped && status !== "completed" ? "skipped" : status === "completed" ? "completed" : /in_progress|running/.test(status) ? "running" : /failed|blocked/.test(status) ? "failed" : "pending"; const detail = text(phase.detail || phase.status, "Pending"); const duration = phase.started_at ? elapsed(phase.started_at, phase.finished_at || new Date().toISOString()) : "—"; return <li className={`flow-step ${state}`} key={phase.id || index}><div className="flow-stage-button"><span className="flow-marker">{state === "completed" ? "✓" : state === "skipped" ? "–" : index + 1}</span><span className="flow-copy"><strong>{text(phase.label)}</strong><span className="flow-detail" title={detail}>{detail}</span><small className="flow-duration">{duration}</small></span></div></li>; })}</ol></div></div>;
}

function StartDeliveryDialog({ stories, value, onChange, step, busy, error, onClose, onContinue, onConfirm }: { stories: Array<{ value: string; label: string }>; value: string; onChange: (value: string) => void; step: 1 | 2; busy: boolean; error: string; onClose: () => void; onContinue: () => void; onConfirm: () => void }) {
  const first = step === 1;
  const selectedLabel = stories.find((item) => item.value === value)?.label || value;
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={first ? "Start delivery" : "Confirm start delivery"} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>{first ? "Start delivery" : "Confirm delivery start"}</strong><p className="modal-copy">{first ? "Choose a ready story to launch." : `Are you sure you want to start delivery for ${selectedLabel} now?`}</p>{first && <label className="field"><span>Story</span><select value={value} onChange={(event) => onChange(event.target.value)} disabled={busy || stories.length === 0}>{stories.length ? stories.map((item) => <option value={item.value} key={item.value} title={item.label}>{item.label}</option>) : <option value="">No ready stories</option>}</select></label>}{error && <p className="status-note">{error}</p>}</div><footer><button className="button" disabled={busy} onClick={onClose}>Cancel</button>{first ? <button className="button primary" disabled={busy || !value} onClick={onContinue}>Continue</button> : <button className="button primary" disabled={busy || !value} onClick={onConfirm}><Play size={14} />{busy ? "Starting…" : "Start delivery"}</button>}</footer></section></div>;
}

function RetryDeliveryDialog({ story, busy, error, onClose, onConfirm }: { story: string; busy: boolean; error: string; onClose: () => void; onConfirm: () => void }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal" role="dialog" aria-modal="true" aria-label="Reset and retry delivery" onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>Reset and retry {story}?</strong><p>This removes the Story worktrees, resets its Delivery and JIRA status, then starts a new run. The failed run and logs stay in history.</p>{error && <p className="status-note">{error}</p>}</div><footer><button className="button" disabled={busy} onClick={onClose}>Cancel</button><button className="button primary" disabled={busy} onClick={onConfirm}><RotateCcw size={14} />{busy ? "Starting…" : "Retry"}</button></footer></section></div>;
}

function DeleteHistoryDialog({ kind = "delivery", run, busy, onClose, onConfirm }: { kind?: "delivery" | "patch"; run: RecordValue; busy: boolean; onClose: () => void; onConfirm: () => void }) {
  const patch = kind === "patch";
  const story = text(run.jira_key || run.story || run.run_id);
  return <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}><section className="modal delete-history-modal" role="dialog" aria-modal="true" aria-label={`Delete ${patch ? "Auto Patch" : "delivery"} history`} onMouseDown={(event) => event.stopPropagation()}><div className="modal-body compact"><strong>Delete {patch ? "Auto Patch" : "delivery"} history?</strong><p className="modal-copy">This removes the {story} record, log, and trace files. This action cannot be undone.</p></div><footer><button className="button" disabled={busy} onClick={onClose}>Cancel</button><button className="button danger delete-confirm" disabled={busy} onClick={onConfirm}><Trash2 size={14} />{busy ? "Deleting…" : "Delete record"}</button></footer></section></div>;
}

function ObservatoryView({ project, notify, onDirtyChange }: { project: string; notify: Notify; onDirtyChange: (dirty: boolean) => void }) {
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
    if (dirty && !window.confirm("You have unsaved Observatory changes. Switch stories without saving?")) return;
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
    if (dirty && !window.confirm("You have unsaved Observatory changes. Start delivery without saving?")) return;
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
        <h3>Stories</h3>
        <div className="observatory-list-tools">
          <button type="button" className={`icon-button${searchOpen ? " active" : ""}`} title="Search stories" aria-label="Search stories" aria-pressed={searchOpen} onClick={() => setSearchOpen((value) => !value)}><Search size={15} /></button>
          <button type="button" className={`icon-button${readyOnly ? " active" : ""}`} title={readyOnly ? "Showing business-ready stories" : "Filter business-ready stories"} aria-label="Filter stories" aria-pressed={readyOnly} onClick={() => setReadyOnly((value) => !value)}><ListFilter size={15} /></button>
        </div>
      </div>
      {searchOpen && <div className="observatory-list-search"><input value={storyQuery} onChange={(event) => setStoryQuery(event.target.value)} placeholder="Search stories" aria-label="Search stories" autoFocus /></div>}
      <div className="observatory-list-body">
        {loadingList ? <div className="loading-state"><LoaderCircle size={18} className="spin" /> Loading…</div> : null}
        {!loadingList && !visibleStories.length ? <Empty label={stories.length ? "No stories match this filter." : "No stories found in the docs repository."} /> : null}
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
      {!selected ? <Empty label="Select a story to inspect." /> : <>
        <div className="observatory-header">
          <div className="observatory-title-row">
            <h2>
              {jiraUrl
                ? <a className="observatory-heading-link" href={jiraUrl} target="_blank" rel="noreferrer"><span className="observatory-key">{storyKey}</span><span className="observatory-heading-title">{storyTitle}</span><ExternalLink size={12} /></a>
                : <><span className="observatory-key">{storyKey}</span><span className="observatory-heading-title">{storyTitle}</span></>}
            </h2>
            <div className="panel-actions observatory-actions">
              {canStartDelivery && <button type="button" className="button secondary" disabled={startBusy || loadingContent} onClick={openStartDelivery}><Play size={14} />Start delivery</button>}
              <button type="button" className={`button primary${saving ? " is-busy" : ""}`} disabled={!dirty || saving || loadingContent} onClick={() => void save()}>{saving ? <LoaderCircle size={14} className="spin" /> : <Save size={14} />}{saving ? "Saving…" : "Save"}</button>
            </div>
          </div>
          <div className="observatory-subheader">
            <StoryStatusMeta business={businessStatus || "draft"} technical={technicalStatus || "draft"} />
          </div>
        </div>
        {loadingContent ? <div className="loading-state"><LoaderCircle size={20} className="spin" /> Loading story…</div> : <>
          <div className="observatory-doc-tabs" role="tablist">
            <button type="button" role="tab" aria-selected={docTab === "story"} className={docTab === "story" ? "active" : ""} onClick={() => setDocTab("story")}>Story</button>
            <button type="button" role="tab" aria-selected={docTab === "plan"} className={docTab === "plan" ? "active" : ""} onClick={() => setDocTab("plan")}>Technical plan</button>
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

function StoryReference({ jiraKey, title }: { jiraKey: string; title?: string }) { return <span className="story-reference">{title ? <><code>{text(jiraKey)}</code><span className="story-reference-title">{title}</span></> : <code>{text(jiraKey, "No active delivery")}</code>}</span>; }
function DeliveryFlow({ stages, deliveryStatus, currentStep, startedAt, finishedAt, remediation, now, onStageClick }: { stages: RecordValue[]; deliveryStatus: string; currentStep?: string; startedAt?: string; finishedAt?: string; remediation?: RecordValue; now: number; onStageClick: (stage: RecordValue) => void }) {
  const terminalSuccess = /completed|dev_done|pr_open/i.test(deliveryStatus);
  const stopped = /stopped from dashboard/i.test(String(currentStep || ""));
  const retrying = remediation?.status === "in_progress";
  const retry = retrying ? `${remediation.attempt}/${remediation.max_attempts}` : "";
  const states = stages.map((stage) => { const rawStatus = String(stage.status || "pending").toLowerCase(); return terminalSuccess || rawStatus === "completed" ? "completed" : /running|progress/.test(rawStatus) ? "running" : stopped && /fail|block/.test(rawStatus) ? "stopped" : /fail|block/.test(rawStatus) ? "failed" : "pending"; });
  const progressUnits = states.reduce((total, state) => total + (state === "completed" ? 1 : state === "running" ? .5 : 0), 0);
  const progress = stages.length > 1 ? Math.max(0, Math.min(100, ((progressUnits - 1) / (stages.length - 1)) * 100)) : 100;
  return <div className="delivery-flow"><div className="flow-heading"><div><span className="flow-title">Delivery Flow</span>{retrying && <strong className="remediation-alert"><RotateCcw size={13} />Verification failed · Remediation retry {retry}</strong>}</div><p>{startedAt ? `Started ${when(startedAt)}` : "Awaiting delivery trigger"}{finishedAt ? ` · Finished ${when(finishedAt)}` : ""}</p></div><div className="flow-track-wrap"><span className="flow-track"><i style={{ width: `${progress}%` }} /></span><ol className="flow-steps" style={{ "--flow-count": stages.length } as React.CSSProperties}>{stages.map((stage, index) => {
    const rawStatus = String(stage.status || "pending").toLowerCase();
    const state = terminalSuccess || rawStatus === "completed" ? "completed" : /running|progress/.test(rawStatus) ? "running" : stopped && /fail|block/.test(rawStatus) ? "stopped" : /fail|block/.test(rawStatus) ? "failed" : "pending";
    const duration = state === "running" ? elapsed(stage.active_started_at || stage.started_at, new Date(now).toISOString()) : stage.duration || "Pending";
    const attemptCount = Array.isArray(stage.attempts) && stage.attempts.length > 1 ? ` · ${stage.attempts.length} attempts` : "";
    const caption = state === "stopped" ? "Stopped" : retrying && state === "running" && ["implement", "verification"].includes(stage.id) ? `Retry ${retry} · ${duration}` : retrying && stage.id === "verification" && state === "failed" ? `Failed · remediation ${retry}` : state === "failed" ? "Needs attention" : `${duration}${attemptCount}`;
    return <li className={`flow-step ${state}`} key={`${stage.label}-${index}`}><button className="flow-stage-button" onClick={() => onStageClick(stage)}><span className="flow-marker">{state === "completed" ? "✓" : state === "running" ? <span className="pulse-dot" /> : index + 1}</span><span className="flow-copy"><strong>{text(stage.label)}</strong><span>{caption}</span></span></button></li>;
  })}</ol></div></div>;
}

function DeliveryLogDialog({ stage, content, error, loading, live = false, onClose }: { stage: RecordValue; content: string; error: string; loading: boolean; live?: boolean; onClose: () => void }) { const logRef = useRef<HTMLPreElement>(null); useEffect(() => { if (live && logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [content, live]); return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal delivery-log-modal" role="dialog" aria-modal="true" aria-label={`${stage.label} log`} onMouseDown={(event) => event.stopPropagation()}><div className="delivery-log-header"><div><span>{stage.label}</span><strong>{stage.duration || "—"}{live && <em className="live-log"><i />Live</em>}</strong><p>{stage.detail || "Delivery log excerpt"}</p>{Array.isArray(stage.attempts) && stage.attempts.length > 0 && <small className="stage-attempts">{stage.attempts.map((attempt: RecordValue) => `Attempt ${attempt.number}: ${attempt.duration}`).join(" · ")}</small>}</div><button className="button secondary" onClick={onClose}>Close</button></div><pre ref={logRef} className="delivery-log-content"><code>{loading && !content ? "Loading log…" : error || content}</code></pre></section></div>; }

function Fact({ label, value }: { label: string; value: React.ReactNode }) { return <div className="fact"><span>{label}</span><strong>{value}</strong></div>; }
function PrLinks({ items }: { items: RecordValue[] }) { return items.length ? <span className="pr-links">{items.map((item, index) => <a href={item.url} target="_blank" rel="noreferrer" key={`${item.url}-${index}`}>{text(item.repository, "Pull request")}{String(item.url || "").match(/\/(\d+)\/?$/) ? ` #${String(item.url).match(/\/(\d+)\/?$/)?.[1]}` : ""}<ExternalLink size={12} /></a>)}</span> : <>—</>; }
function VerificationSummary({ checks, onClick }: { checks: RecordValue[]; onClick: () => void }) { const failed = checks.filter((item) => item.status === "failed").length; const passed = checks.filter((item) => item.status === "passed").length; return checks.length ? <button className={`check-summary ${failed ? "failed" : ""}`} title="Open verification details" onClick={onClick}>{failed ? `${failed} failed` : `${passed}/${checks.length} passed`}</button> : <>—</>; }
function VerificationDialog({ checks, onClose }: { checks: RecordValue[]; onClose: () => void }) { return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal verification-modal" role="dialog" aria-modal="true" aria-label="Verification checks" onMouseDown={(event) => event.stopPropagation()}><div className="delivery-log-header"><div><span>Verification</span><strong>Checks</strong><p>{checks.filter((item) => item.status === "passed").length} passed · {checks.filter((item) => item.status === "failed").length} failed · {checks.filter((item) => item.status === "skipped").length} skipped</p></div><button className="button secondary" onClick={onClose}>Close</button></div><div className="verification-list">{checks.map((check, index) => <article className="verification-check" key={`${check.repository}-${check.id}-${index}`}><div><strong>{text(check.label)}</strong><span>{text(check.repository, "Workspace")}</span></div><Badge value={check.status} /><p>{text(check.summary, "No summary recorded.")}</p>{check.command && <code>{check.command}</code>}</article>)}</div></section></div>; }

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
    <div className="workflow-mode-switch" role="tablist"><button className={mode === "scan" ? "active" : ""} onClick={() => switchMode("scan")}>Auto Scan</button><button className={mode === "delivery" ? "active" : ""} onClick={() => switchMode("delivery")}>Auto Delivery</button><button className={mode === "patch" ? "active" : ""} onClick={() => switchMode("patch")}>Auto Patch</button></div>
    <Panel title={mode === "scan" ? "Auto Scan Workflow" : mode === "delivery" ? "Auto Delivery Workflow" : "Auto Patch Workflow"} action={<IconButton label={fullscreen ? "Exit full screen" : "View full screen"} onClick={() => setFullscreen((value) => !value)}>{fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}</IconButton>} className={`workflow-panel ${fullscreen ? "workflow-panel-fullscreen" : ""}`}>
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
  const meta = promptMeta(item);
  return <div className="modal-backdrop" role="presentation" onMouseDown={saving ? undefined : onClose}><section className="modal prompt-inspector-modal" role="dialog" aria-modal="true" aria-label={`${meta.title} prompt`} onMouseDown={(event) => event.stopPropagation()}><div className="prompt-inspector-header"><div><span>{item.mode === "scan" ? "Auto Scan" : item.mode === "delivery" ? "Auto Delivery" : "Auto Patch"} prompt</span><strong>{meta.title}</strong><code>{item.path}</code></div><button className="button secondary" disabled={saving} onClick={onClose}>Close</button></div><div className="prompt-inspector-body"><div className="markdown-workbench"><label className="markdown-pane"><span>Original Markdown</span><textarea value={content} onChange={(event) => onChange(event.target.value)} spellCheck={false} disabled={saving} /></label><article className="markdown-preview"><span>Preview</span><MarkdownBody content={content} /></article></div></div><footer><button className="button" disabled={saving} onClick={onClose}>Cancel</button><button className={`button primary${saving ? " is-busy" : ""}`} disabled={saving} onClick={onSave}>{saving ? <LoaderCircle size={14} className="spin" /> : <Save size={14} />}{saving ? "Saving…" : "Save prompt"}</button></footer></section></div>;
}

function HelpTip({ children }: { children: React.ReactNode }) {
  return <details className="field-help"><summary aria-label="Explain this setting"><CircleHelp size={13} /></summary><span role="tooltip">{children}</span></details>;
}

function Field({ label, help, children }: { label: string; help?: React.ReactNode; children: React.ReactNode }) {
  return <label className="field"><span className="field-label">{label}{help && <HelpTip>{help}</HelpTip>}</span>{children}</label>;
}

function StatusMultiSelect({ options, value, onChange, markDirty }: { options: string[]; value: string[]; onChange: (value: string[]) => void; markDirty: () => void }) {
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
  const summary = value.length === 0 ? "Select statuses" : value.length === 1 ? value[0] : `${value.length} statuses selected`;
  return <div ref={picker} className={`status-picker ${open ? "is-open" : ""}`}>
    <button type="button" className="status-picker-trigger" aria-label="Eligible JIRA statuses" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
      <span className={`status-picker-summary ${value.length === 0 ? "placeholder" : ""}`} title={value.join(", ")}>{summary}</span><ChevronDown size={15} aria-hidden="true" />
    </button>
    {open && <div className="status-picker-menu" role="listbox" aria-label="Eligible JIRA statuses" aria-multiselectable="true">
      <div className="status-picker-options">{options.map((status) => { const selected = value.includes(status); return <button type="button" role="option" aria-selected={selected} className={`status-picker-option ${selected ? "selected" : ""}`} key={status} onClick={() => toggle(status)}><span className="status-picker-check" aria-hidden="true">{selected ? "✓" : ""}</span><span>{status}</span></button>; })}</div>
      <footer className="status-picker-footer"><span>{value.length} selected</span>{value.length > 0 && <button type="button" onClick={() => { onChange([]); markDirty(); }}>Clear</button>}</footer>
    </div>}
  </div>;
}

function ModelField({ label, value, onChange, markDirty }: { label: string; value: string; onChange: (value: string) => void; markDirty: () => void }) {
  const normalizedValue = trimmedModelValue(value);
  const isPreset = cursorModelOptions.some((model) => model.value === normalizedValue);
  const [customOpen, setCustomOpen] = useState(false);
  const openCustom = () => setCustomOpen(true);
  return <Field label={label} help="Choose a preset, or select Custom and enter a model ID supported by Cursor. Lumen does not validate custom model availability.">
    <select value={isPreset ? normalizedValue : customModelOption} onChange={(event) => { if (event.target.value === customModelOption) openCustom(); else { onChange(event.target.value); markDirty(); } }}>
      {cursorModelOptions.map((model) => <option value={model.value} key={model.value}>{model.label}</option>)}
      <option value={customModelOption}>Custom Cursor model ID…</option>
    </select>
    {!isPreset && <button type="button" className="custom-model-edit" onClick={openCustom}>Edit custom model</button>}
    {customOpen && <CustomModelDialog label={label} value={value} onClose={() => setCustomOpen(false)} onConfirm={(model) => { onChange(model); markDirty(); setCustomOpen(false); }} />}
  </Field>;
}

function CustomModelDialog({ label, value, onClose, onConfirm }: { label: string; value: string; onClose: () => void; onConfirm: (value: string) => void }) {
  const [draft, setDraft] = useState(value);
  const confirm = () => { const model = draft.trim(); if (model) onConfirm(model); };
  useEffect(() => { const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); }; window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown); }, [onClose]);
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal custom-model-modal" role="dialog" aria-modal="true" aria-labelledby="custom-model-title" onMouseDown={(event) => event.stopPropagation()}><div className="custom-model-header"><strong id="custom-model-title">Enter a custom Cursor model</strong><p>{label} · Use a model ID supported by Cursor.</p></div><div className="modal-body compact"><Field label="Cursor model ID"><input autoFocus value={draft} placeholder="e.g. cursor-grok-4.5-medium" aria-label="Custom Cursor model ID" onChange={(event) => setDraft(event.target.value)} /></Field><p className="modal-copy">Lumen does not validate model availability. The value will be used on the next run.</p></div><footer><button type="button" className="button" onClick={onClose}>Cancel</button><button type="button" className="button primary" disabled={!draft.trim()} onClick={confirm}>Confirm</button></footer></section></div>;
}

function RepositoryView({ data, interact }: { data: DashboardData; interact: (path: string, json: RecordValue, message: string) => Promise<boolean> }) {
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
  const repositoryValue = (value: unknown) => { const display = text(value, "Not configured"); return <span className="repository-fact-value" data-tooltip={display} title={display} tabIndex={0} aria-label={display}><code>{display}</code></span>; };
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
    <Panel title="Repository Governance" action={<button className="button secondary" onClick={() => setAddOpen(true)}>Add repository</button>}>
      <div className="repository-intro">Connect repositories by Git URL. Lumen clones them into <code>repos/</code>, detects runtime and build tooling, then lets you approve the automation that may change or publish code.</div>
      <div className="repository-overview"><Fact label="Registered" value={repositories.length} /><Fact label="Needs attention" value={attention} /><Fact label="Auto Scan" value={`${scanEnabled}/${repositories.length} enabled`} /><Fact label="Auto Delivery" value={`${deliveryEnabled}/${repositories.length} enabled`} /><Fact label="Auto Patch" value={`${patchEnabled}/${repositories.length} enabled`} /></div>
      <div className="repository-filters"><button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>All ({repositories.length})</button><button className={filter === "attention" ? "active" : ""} onClick={() => setFilter("attention")}>Needs attention ({attention})</button><button className={filter === "patch" ? "active" : ""} onClick={() => setFilter("patch")}>Auto Patch enabled ({patchEnabled})</button></div>
      {filter === "attention" && <div className="repository-filter-note"><CircleAlert size={14} aria-hidden="true" /><span>Needs attention means uncommitted changes, a branch behind remote, or a diverged branch/sync.</span></div>}
      <div className="repository-list"><div className="repository-grid">{visible.map((repository) => {
        const health = repository.health || {};
        const automation = automationFor(repository);
        return <article className="repository-card" key={repository.name}>
          <button type="button" className="repository-card-button" onClick={() => setEditing(repository.name)} aria-label={`Edit ${repository.name || "repository"}`}>
            <div className="repository-card-heading"><div><strong>{repository.name || "Unnamed repository"}</strong><span>{runtimeSummary(health)}</span></div><ChevronRight size={16} aria-hidden="true" /></div>
            <div className="repository-card-bottom"><div className="repository-card-permissions"><span className={automation.scan.allow_auto_fix ? "enabled" : "disabled"}>Auto Scan {automation.scan.allow_auto_fix ? "enabled" : "disabled"}</span><span className={automation.delivery.enabled ? "enabled" : "disabled"}>Auto Delivery {automation.delivery.enabled ? "enabled" : "disabled"}</span><span className={automation.patch.enabled ? "enabled" : "disabled"}>Auto Patch {automation.patch.enabled ? "enabled" : "disabled"}</span></div><span className="repository-card-branch"><GitBranch size={12} aria-hidden="true" />{repository.default_branch || "main"}</span></div>
          </button>
        </article>;
      })}{visible.length === 0 && <Empty label="No repositories match this view." />}</div></div>
    </Panel>
    {selectedRepository && selectedIndex >= 0 && selectedAutomation && selectedVerification && <div className="modal-backdrop repository-config-backdrop" role="presentation" onMouseDown={() => setEditing(null)}><section className="modal repository-config-modal" role="dialog" aria-modal="true" aria-labelledby="repository-config-title" onMouseDown={(event) => event.stopPropagation()}>
      <header className="repository-config-header"><div><strong id="repository-config-title">{selectedRepository.name || "Unnamed repository"}</strong><span>Repository configuration</span><p>{selectedHealth.language || "Generic"} · {selectedHealth.build_tools?.join(", ") || "No build tool detected"} · {selectedRepository.default_branch || "main"}</p></div><IconButton label="Close repository configuration" onClick={() => setEditing(null)}><X size={15} /></IconButton></header>
      <div className="repository-config-body"><div className="repository-editor">
        <section className="repository-section"><div><strong>Identity & connection</strong><span>Detected locally; the default branch is the only editable connection setting.</span></div><div className="repository-facts"><Fact label="Local path" value={repositoryValue(selectedRepository.path)} /><Fact label="Remote" value={repositoryValue(selectedHealth.remote_url || selectedRepository.remote_url)} /><Fact label="Git status" value={<Badge value={selectedHealth.git_status || "unknown"} />} /><Fact label="Branch sync" value={<Badge value={selectedHealth.sync_status || "unknown"} />} /></div><div className="form-grid compact"><Field label="Default branch"><select value={selectedRepository.default_branch || ""} onChange={(event) => update(selectedIndex, { default_branch: event.target.value })}>{Array.from(new Set([selectedRepository.default_branch, ...(selectedRepository.branches || [])].filter(Boolean))).map((branch) => <option value={branch} key={branch}>{branch}</option>)}</select></Field></div></section>
        <section className="repository-section"><div><strong>Runtime & build</strong><span>Detected from repository files. These values are read-only until the repository changes.</span></div><div className="repository-facts"><Fact label="Language" value={selectedHealth.language || "Generic"} /><Fact label="Java" value={selectedHealth.java_version ? `Java ${selectedHealth.java_version}` : "Not detected"} /><Fact label="Node" value={selectedHealth.node_version ? `Node ${selectedHealth.node_version}` : "Not detected"} /><Fact label="Build tools" value={selectedHealth.build_tools?.join(", ") || "Not detected"} /></div></section>
        <section className="repository-section"><div><strong>Automation permissions</strong><span>Frontend delivery remains disabled globally and cannot be enabled here.</span></div><div className="repository-policy-grid"><label><input type="checkbox" checked={selectedAutomation.scan.allow_auto_fix} onChange={(event) => updateAutomation(selectedIndex, "scan", { allow_auto_fix: event.target.checked })} /><span><strong>Auto Scan fixes</strong><small>Allow high-confidence Scan fixes and their configured publish flow.</small></span></label><label><input type="checkbox" checked={selectedAutomation.delivery.enabled} onChange={(event) => updateAutomation(selectedIndex, "delivery", { enabled: event.target.checked })} /><span><strong>Auto Delivery</strong><small>Allow approved technical delivery work for this repository.</small></span></label><label><input type="checkbox" checked={selectedAutomation.patch.enabled} onChange={(event) => updateAutomation(selectedIndex, "patch", { enabled: event.target.checked })} /><span><strong>Auto Patch</strong><small>Allow Jira-driven fixes and publishing for this repository.</small></span></label></div></section>
        <section className="repository-section repository-verification-section"><div className="repository-section-heading"><strong>Delivery verification</strong><span>Choose what Lumen should run for this repository after implementation.</span></div><div className="verification-group"><span className="verification-group-label">Policy</span><div className="verification-mode-grid"><label className={`verification-mode-card${selectedVerification.mode !== "skip" ? " selected" : ""}`}><input type="radio" name={`verification-mode-${selectedRepository.name}`} checked={selectedVerification.mode !== "skip"} onChange={() => updateVerification(selectedIndex, { mode: selectedVerification.mode === "custom" ? "custom" : "auto" })} /><span><strong>Run verification</strong><small>Use the automatic profile or your custom commands.</small></span></label><label className={`verification-mode-card${selectedVerification.mode === "skip" ? " selected" : ""}`}><input type="radio" name={`verification-mode-${selectedRepository.name}`} checked={selectedVerification.mode === "skip"} onChange={() => updateVerification(selectedIndex, { mode: "skip" })} /><span><strong>Skip verification</strong><small>Do not run compile, static checks, or tests.</small></span></label></div></div>{selectedVerification.mode !== "skip" && <><div className="verification-group"><span className="verification-group-label">Execution source</span><div className="verification-source-toggle"><label><input type="radio" name={`verification-source-${selectedRepository.name}`} checked={selectedVerification.mode === "auto"} onChange={() => updateVerification(selectedIndex, { mode: "auto" })} /><span><strong>Automatic profile</strong><small>Detect commands from repository files at runtime.</small></span></label><label><input type="radio" name={`verification-source-${selectedRepository.name}`} checked={selectedVerification.mode === "custom"} onChange={() => updateVerification(selectedIndex, { mode: "custom" })} /><span><strong>Custom commands</strong><small>Run only the commands entered below.</small></span></label></div></div>{selectedVerification.mode === "auto" ? <div className="verification-group"><span className="verification-group-label">Checks to run</span><div className="verification-check-grid"><label><input type="checkbox" checked={selectedVerification.compile} onChange={(event) => updateVerification(selectedIndex, { compile: event.target.checked })} /><span><strong>Compile & static checks</strong><small>Compile, syntax, typecheck, lint, or PMD checks.</small></span></label><label><input type="checkbox" checked={selectedVerification.tests} onChange={(event) => updateVerification(selectedIndex, { tests: event.target.checked })} /><span><strong>Tests</strong><small>Unit, integration, and test-suite commands.</small></span></label></div></div> : <div className="verification-group"><span className="verification-group-label">Commands</span><div className="verification-command-editor">{selectedHealth.suggested_commands?.length > 0 && <button type="button" className="text-button verification-suggested-button" onClick={() => update(selectedIndex, { delivery_commands: selectedHealth.suggested_commands.join("\n") })}>Use {selectedHealth.suggested_commands.length} suggested command{selectedHealth.suggested_commands.length === 1 ? "" : "s"}</button>}<label className="field repository-commands"><textarea value={selectedRepository.delivery_commands ?? commandsFor(selectedRepository)} rows={4} placeholder="One command per line." onChange={(event) => update(selectedIndex, { delivery_commands: event.target.value })} /></label></div></div>}</>}</section>
      </div></div><footer className="repository-config-footer"><div className="repository-config-actions"><button type="button" className="button" disabled={saving} onClick={() => setEditing(null)}>Close</button><button type="button" className={`button primary${saving ? " is-busy" : ""}`} disabled={!dirty || saving} onClick={() => void saveGovernance()}>{saving ? <LoaderCircle size={15} className="spin" /> : <Save size={15} />}{saving ? "Saving…" : "Save"}</button></div></footer>
    </section></div>}
    {addOpen && <AddRepositoryDialog onClose={() => setAddOpen(false)} onAdd={(url) => { void interact("/api/repositories/clone", { url }, "Repository cloned and registered"); setAddOpen(false); }} />}
  </div>;
}

function AddRepositoryDialog({ onClose, onAdd }: { onClose: () => void; onAdd: (url: string) => void }) {
  const [url, setUrl] = useState("");
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="modal repository-modal" role="dialog" aria-modal="true" aria-label="Add repository" onMouseDown={(event) => event.stopPropagation()}><div className="prompt-inspector-header"><div><strong>Add repository</strong><span className="repository-modal-description">Lumen clones the Git URL, detects the branch and tooling, enables existing Scan and Delivery behavior, and authorizes Auto Patch by default.</span></div></div><div className="repository-modal-body"><Field label="Clone URL"><input autoFocus value={url} placeholder="https://git.example.com/team/service.git" onChange={(event) => setUrl(event.target.value)} /></Field></div><footer><button className="button" onClick={onClose}>Cancel</button><button className="button primary" disabled={!url.trim()} onClick={() => onAdd(url.trim())}>Clone and inspect</button></footer></section></div>;
}

function SettingsView({ data, project, notify, onDirtyChange, reload }: { data: DashboardData; project: string; notify: Notify; onDirtyChange: (dirty: boolean) => void; reload: () => Promise<void> }) {
  const workspace = data.interactive?.workspace || {};
  const schedules = data.interactive?.schedules || {};
  const agentsPayload = data.interactive?.agents || {};
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
  const [scanModel, setScanModel] = useState(modelValue(workspace.models?.scan));
  const [deliveryModel, setDeliveryModel] = useState(modelValue(workspace.models?.delivery));
  const [patchModel, setPatchModel] = useState(modelValue(workspace.models?.patch));
  const [workflowStatuses, setWorkflowStatuses] = useState<string[]>([]);
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [changedSecrets, setChangedSecrets] = useState<Record<string, string>>({});
  const [scanPublishMode, setScanPublishMode] = useState(String(workspace.publish?.scan || "pr"));
  const [deliveryPublishMode, setDeliveryPublishMode] = useState(String(workspace.publish?.delivery || "pr"));
  const [patchPublishMode, setPatchPublishMode] = useState(String(workspace.publish?.patch || "pr"));
  const [feishuEnabled, setFeishuEnabled] = useState(workspace.feishu_notifications_enabled !== false);
  const [agentsEnabled, setAgentsEnabled] = useState(Boolean(agentsPayload.enabled));
  const [agentDrafts, setAgentDrafts] = useState<AgentSettings[]>(Array.isArray(agentsPayload.agents) ? agentsPayload.agents.map((agent) => ({ ...agent })) : []);
  const [accessDraft, setAccessDraft] = useState<AgentsAccessSettings>({
    allowed_chat_ids: agentsPayload.access?.allowed_chat_ids || [],
    allowed_user_ids: agentsPayload.access?.allowed_user_ids || [],
    mutation_allowed_user_ids: agentsPayload.access?.mutation_allowed_user_ids || [],
    admin_user_ids: agentsPayload.access?.admin_user_ids || [],
    legacy_warning: Boolean(agentsPayload.access?.legacy_warning),
    default_policy: agentsPayload.access?.default_policy || "legacy_allow",
  });
  const [recentFeishu, setRecentFeishu] = useState({
    user_ids: agentsPayload.recent_feishu?.user_ids || [],
    chat_ids: agentsPayload.recent_feishu?.chat_ids || [],
    users: agentsPayload.recent_feishu?.users || [],
    chats: agentsPayload.recent_feishu?.chats || [],
    names: agentsPayload.recent_feishu?.names || {},
  });
  const [agentsBaseline, setAgentsBaseline] = useState({
    enabled: Boolean(agentsPayload.enabled),
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
  const feishuLabel = (id: string) => {
    const name = feishuName(id);
    return name ? `${name} · ${shortFeishuId(id)}` : shortFeishuId(id);
  };
  const recentPeople = (recentFeishu.users?.length
    ? recentFeishu.users
    : recentFeishu.user_ids.map((id) => ({ id, name: feishuName(id) }))
  ).filter((item) => item.id);
  const recentChats = (recentFeishu.chats?.length
    ? recentFeishu.chats
    : recentFeishu.chat_ids.map((id) => ({ id, name: feishuName(id) }))
  ).filter((item) => item.id);
  const syncAgents = (payload: AgentsSettingsPayload) => {
    const nextAgents = Array.isArray(payload.agents)
      ? payload.agents.map((agent) => ({ ...agent, app_secret: "" }))
      : [];
    const nextAccess = {
      allowed_chat_ids: payload.access?.allowed_chat_ids || [],
      allowed_user_ids: payload.access?.allowed_user_ids || [],
      mutation_allowed_user_ids: payload.access?.mutation_allowed_user_ids || [],
      admin_user_ids: payload.access?.admin_user_ids || [],
      legacy_warning: Boolean(payload.access?.legacy_warning),
      default_policy: payload.access?.default_policy || "legacy_allow",
    };
    setAgentsEnabled(Boolean(payload.enabled));
    setAgentDrafts(nextAgents);
    setAccessDraft(nextAccess);
    setRecentFeishu({
      user_ids: payload.recent_feishu?.user_ids || [],
      chat_ids: payload.recent_feishu?.chat_ids || [],
      users: payload.recent_feishu?.users || [],
      chats: payload.recent_feishu?.chats || [],
      names: payload.recent_feishu?.names || {},
    });
    setAgentsBaseline({
      enabled: Boolean(payload.enabled),
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
  const addAccessId = (
    field: "allowed_chat_ids" | "allowed_user_ids" | "mutation_allowed_user_ids" | "admin_user_ids",
    value: string,
  ) => {
    const id = value.trim();
    if (!id) return;
    setAccessDraft((current) => {
      const existing = current[field] || [];
      if (existing.includes(id)) return current;
      return { ...current, [field]: [...existing, id] };
    });
    markDirty();
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
    setScanWindow(String(workspace.scan_window_days || 7)); setScanCron(String(schedules.scan?.cron || "0 12 * * 1-5")); setScanEnabled(Boolean(schedules.scan)); setDeliveryInterval(String(Math.round((schedules.delivery?.interval_seconds || 300) / 60))); setEligibleStatuses(Array.isArray(schedules.delivery?.jira_statuses) ? schedules.delivery.jira_statuses.map(String) : String(schedules.delivery?.jira_status || "To Do,Backlog,In Progress").split(",").map((value) => value.trim()).filter(Boolean)); setInDevStatus(String(schedules.delivery?.in_dev_status || "")); setDevDoneStatus(String(schedules.delivery?.dev_done_status || "")); setBlockedStatus(String(schedules.delivery?.blocked_status || "Block")); setDeliveryEnabled(Boolean(schedules.delivery?.enabled)); setPatchInterval(String(Math.round((schedules.patch?.interval_seconds || 300) / 60))); setPatchStatuses(Array.isArray(schedules.patch?.jira_statuses) ? schedules.patch.jira_statuses.map(String) : ["To Do"]); setPatchStartStatus(String(schedules.patch?.in_progress_status || "In Progress")); setPatchDoneStatus(String(schedules.patch?.done_status || "Done")); setPatchBlockedStatus(String(schedules.patch?.blocked_status || "Block")); setPatchEnabled(Boolean(schedules.patch?.enabled)); setScanModel(modelValue(workspace.models?.scan)); setDeliveryModel(modelValue(workspace.models?.delivery)); setPatchModel(modelValue(workspace.models?.patch)); setFeishuEnabled(workspace.feishu_notifications_enabled !== false); setSecrets({}); setChangedSecrets({});
    if (data.interactive?.agents) syncAgents(data.interactive.agents);
    setDirty(false); onDirtyChange(false);
  }, [project]);
  useEffect(() => { setScanPublishMode(String(workspace.publish?.scan || "pr")); setDeliveryPublishMode(String(workspace.publish?.delivery || "pr")); setPatchPublishMode(String(workspace.publish?.patch || "pr")); }, [workspace.publish?.scan, workspace.publish?.delivery, workspace.publish?.patch]);
  useEffect(() => { setFeishuEnabled(workspace.feishu_notifications_enabled !== false); }, [workspace.feishu_notifications_enabled]);
  useEffect(() => { const warn = (event: BeforeUnloadEvent) => { if (!dirty) return; event.preventDefault(); event.returnValue = ""; }; window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [dirty]);
  const getSecret = async (name: string) => { const response = await request(`/api/integration?key=${encodeURIComponent(name)}`, project); return String(response.value); };
  const reveal = async (name: string) => { try { const result = await getSecret(name); setSecrets((current) => ({ ...current, [name]: result })); notify("Integration value revealed", "success"); } catch (err) { notify(err instanceof Error ? err.message : "Unable to reveal value", "error"); } };
  const copy = async (name: string) => { try { const result = await getSecret(name); await navigator.clipboard.writeText(result); notify("Integration value copied", "success"); } catch (err) { notify(err instanceof Error ? err.message : "Unable to copy value", "error"); } };
  const configured = workspace.configured_integrations || [];
  const statusOptions = Array.from(new Set(["To Do", "Backlog", "In Progress", "Done", "Block", ...workflowStatuses, ...eligibleStatuses, ...patchStatuses, inDevStatus, devDoneStatus, patchStartStatus, patchDoneStatus, patchBlockedStatus].filter(Boolean)));
  const configuredDeliveryStatuses = Array.isArray(schedules.delivery?.jira_statuses) ? schedules.delivery.jira_statuses.map(String) : String(schedules.delivery?.jira_status || "To Do,Backlog,In Progress").split(",").map((value) => value.trim()).filter(Boolean);
  const configuredPatchStatuses = Array.isArray(schedules.patch?.jira_statuses) ? schedules.patch.jira_statuses.map(String) : ["To Do"];
  const sameValues = (left: string[], right: string[]) => left.length === right.length && left.every((value, index) => value === right[index]);
  const scanScheduleChanged = scanEnabled !== Boolean(schedules.scan) || (scanEnabled && scanCron !== String(schedules.scan?.cron || "0 12 * * 1-5"));
  const deliveryScheduleChanged = deliveryEnabled !== Boolean(schedules.delivery?.enabled) || (deliveryEnabled && (deliveryInterval !== String(Math.round((schedules.delivery?.interval_seconds || 300) / 60)) || !sameValues(eligibleStatuses, configuredDeliveryStatuses) || inDevStatus !== String(schedules.delivery?.in_dev_status || "") || devDoneStatus !== String(schedules.delivery?.dev_done_status || "") || blockedStatus !== String(schedules.delivery?.blocked_status || "Block")));
  const patchScheduleChanged = patchEnabled !== Boolean(schedules.patch?.enabled) || (patchEnabled && (patchInterval !== String(Math.round((schedules.patch?.interval_seconds || 300) / 60)) || !sameValues(patchStatuses, configuredPatchStatuses) || patchStartStatus !== String(schedules.patch?.in_progress_status || "In Progress") || patchDoneStatus !== String(schedules.patch?.done_status || "Done") || patchBlockedStatus !== String(schedules.patch?.blocked_status || "Block")));
  const publishPolicyChanged = scanPublishMode !== String(workspace.publish?.scan || "pr") || deliveryPublishMode !== String(workspace.publish?.delivery || "pr") || patchPublishMode !== String(workspace.publish?.patch || "pr");
  const agentsChanged = agentsEnabled !== agentsBaseline.enabled || JSON.stringify(agentDrafts) !== agentsBaseline.agents || JSON.stringify(accessDraft) !== agentsBaseline.access || JSON.stringify({
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
  const accessMappings = (
    [
      ["Chats", accessDraft.allowed_chat_ids || []],
      ["Allowed users", accessDraft.allowed_user_ids || []],
      ["Mutation users", accessDraft.mutation_allowed_user_ids || []],
      ["Admins", accessDraft.admin_user_ids || []],
    ] as Array<[string, string[]]>
  ).filter(([, ids]) => ids.length > 0);
  const saveAll = async () => {
    if (saving) return;
    setSaving(true);
    try {
      if (!scanModel.trim() || !deliveryModel.trim() || !patchModel.trim()) throw new Error("Choose a preset or enter a Cursor-supported model ID for all workflows.");
      for (const agent of agentDrafts) {
        if (!String(agent.model || "").trim()) throw new Error(`${agent.display_name || agent.id} needs a Cursor model.`);
        if (!String(agent.soul || "").trim()) throw new Error(`${agent.display_name || agent.id} SOUL cannot be empty.`);
      }
      const saves = [
        () => request("/api/workspace", project, { method: "POST", json: { scan_window_days: Number(scanWindow), scan_model: scanModel.trim(), delivery_model: deliveryModel.trim(), patch_model: patchModel.trim(), feishu_notifications_enabled: feishuEnabled } }),
        ...Object.entries(changedSecrets).map(([key, value]) => () => request("/api/integration", project, { method: "POST", json: { key, value } }))
      ];
      if (scanScheduleChanged) saves.push(() => request("/api/schedule", project, { method: "POST", json: scanEnabled ? { kind: "scan", action: "save", cron: scanCron } : { kind: "scan", action: "remove" } }));
      if (deliveryScheduleChanged) saves.push(() => request("/api/schedule", project, { method: "POST", json: deliveryEnabled ? { kind: "delivery", action: "save", interval_minutes: Number(deliveryInterval), jira_statuses: eligibleStatuses, in_dev_status: inDevStatus, dev_done_status: devDoneStatus, blocked_status: blockedStatus } : { kind: "delivery", action: "remove" } }));
      if (patchScheduleChanged) saves.push(() => request("/api/schedule", project, { method: "POST", json: patchEnabled ? { kind: "patch", action: "save", interval_minutes: Number(patchInterval), jira_statuses: patchStatuses, issue_types: ["Task", "Bug"], in_progress_status: patchStartStatus, done_status: patchDoneStatus, blocked_status: patchBlockedStatus } : { kind: "patch", action: "remove" } }));
      if (publishPolicyChanged) saves.push(() => request("/api/publish-policy", project, { method: "POST", json: { scan_mode: scanPublishMode, delivery_mode: deliveryPublishMode, patch_mode: patchPublishMode } }));
      if (agentsChanged) {
        saves.push(async () => {
          const result = await request("/api/agents", project, {
            method: "POST",
            json: {
              enabled: agentsEnabled,
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
                  model: agent.model,
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
    <PageIntro title="Workspace settings" description={`${project || "Current project"} · one place for automation, Agent access, delivery policy, and integrations.`} action={<span className="settings-scope">Local configuration</span>} />
    <div className="settings-summary">
      <div><span>Schedules</span><strong>{enabledScheduleCount}/3</strong><small>running</small></div>
      <div><span>Agent conversations</span><strong>{enabledAgentCount}/{agentDrafts.length || 4}</strong><small>enabled</small></div>
      <div><span>Publish policy</span><strong>{deliveryPublishMode === "direct" ? "Direct" : deliveryPublishMode === "merge" ? "Merge" : "PR"}</strong><small>Auto Delivery</small></div>
      <div><span>Integrations</span><strong>{configured.length}</strong><small>configured keys</small></div>
    </div>
    <nav className="settings-nav" aria-label="Settings sections"><a href="#settings-automation">Automation</a><a href="#settings-agents">Agent team</a><a href="#settings-project">Project output</a><a href="#settings-runtime">Runtime &amp; integrations</a></nav>
    <section className="settings-cluster" id="settings-automation">
      <div className="settings-cluster-heading"><div><span>01 · CONTROL PLANE</span><h2>Automation</h2><p>Schedules and execution policies that decide when work can move.</p></div><a href="#settings-agents">Next: Agent team <ChevronRight size={13} /></a></div>
      <Panel title="Automation Schedules">
      <div className="settings-section"><div className="settings-copy"><div className="settings-heading"><div className="settings-title-stack"><h4>Auto Scan</h4></div></div><p>{text(schedules.scan?.description, "No recurring scan is configured.")}</p></div><div className="settings-control wide"><div className="form-grid compact scan-settings-fields" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, padding: 0, width: "100%" }}><Field label="Lookback, days"><input type="number" min="1" max="365" value={scanWindow} onChange={(event) => { setScanWindow(event.target.value); markDirty(); }} /></Field><Field label="Five-field cron"><input value={scanCron} onChange={(event) => { setScanCron(event.target.value); markDirty(); }} /></Field></div></div><div className="settings-toggle"><ScheduleToggle enabled={scanEnabled} onChange={(enabled) => { setScanEnabled(enabled); markDirty(); }} /></div></div>
      <div className="settings-section divider"><div className="settings-copy"><div className="settings-heading"><div className="settings-title-stack"><h4>Auto Delivery</h4></div></div><p>{deliveryEnabled ? `Polling every ${deliveryInterval} minute(s).` : "Delivery polling is paused."}</p></div><div className="settings-control wide"><div className="form-grid compact"><Field label="Interval, minutes"><input type="number" min="1" value={deliveryInterval} onChange={(event) => { setDeliveryInterval(event.target.value); markDirty(); }} /></Field><Field label="Eligible JIRA statuses" help="Select every Jira status that may start Auto Delivery. The Story must also be Business Ready, Technical Approved, and not already running."><StatusMultiSelect options={statusOptions} value={eligibleStatuses} onChange={setEligibleStatuses} markDirty={markDirty} /></Field><Field label="Move to when started"><select value={inDevStatus} onChange={(event) => { setInDevStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field><Field label="Move to when completed"><select value={devDoneStatus} onChange={(event) => { setDevDoneStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field><Field label="Move to when failed"><select value={blockedStatus} onChange={(event) => { setBlockedStatus(event.target.value); markDirty(); }}>{Array.from(new Set([...statusOptions, "Block"])).map((value) => <option value={value} key={value}>{value}</option>)}</select></Field></div><p className="schedule-note">Select To Do, Backlog, In Progress, or any other eligible Jira status. On failure, Lumen moves the Jira card to the selected Block status and adds a Needs attention comment.</p></div><div className="settings-toggle"><ScheduleToggle enabled={deliveryEnabled} onChange={(enabled) => { setDeliveryEnabled(enabled); markDirty(); }} /></div></div>
      <div className="settings-section divider"><div className="settings-copy"><div className="settings-heading"><div className="settings-title-stack"><h4>Auto Patch</h4></div></div><p>{patchEnabled ? `Polling every ${patchInterval} minute(s) for Task and Bug cards.` : "Auto Patch polling is paused."}</p></div><div className="settings-control wide"><div className="form-grid compact"><Field label="Interval, minutes"><input type="number" min="1" value={patchInterval} onChange={(event) => { setPatchInterval(event.target.value); markDirty(); }} /></Field><Field label="Eligible JIRA statuses"><StatusMultiSelect options={statusOptions} value={patchStatuses} onChange={setPatchStatuses} markDirty={markDirty} /></Field><Field label="Move to when started"><select value={patchStartStatus} onChange={(event) => { setPatchStartStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field><Field label="Move to when completed"><select value={patchDoneStatus} onChange={(event) => { setPatchDoneStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field><Field label="Move to when blocked"><select value={patchBlockedStatus} onChange={(event) => { setPatchBlockedStatus(event.target.value); markDirty(); }}>{statusOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></Field></div><p className="schedule-note">Only Task and Bug cards are captured. Blocked cards retry after a new external Jira comment.</p></div><div className="settings-toggle"><ScheduleToggle enabled={patchEnabled} onChange={(enabled) => { setPatchEnabled(enabled); markDirty(); }} /></div></div>
      </Panel>
    </section>
    <section className="settings-cluster" id="settings-agents">
      <div className="settings-cluster-heading"><div><span>02 · HUMAN-FACING AGENTS</span><h2>Agent team</h2><p>Who speaks to people, what each role owns, and which conversations may mutate state.</p></div><a href="#settings-project">Next: Project output <ChevronRight size={13} /></a></div>
      <Panel title="Agent Roles" action={<span className="muted">Global Feishu agents</span>}>
      <div className="settings-section"><div className="settings-copy"><div className="settings-heading"><div className="settings-title-stack"><h4>Agent Gateway</h4></div></div><p>Enable Feishu conversational agents. Config lives in {text(agentsPayload.config_path, "~/.lumen/agents/config.json")}. Restart `lumen agents start` after saving. Mutations fail closed until mutation users are configured.</p></div><div className="settings-toggle"><ScheduleToggle enabled={agentsEnabled} onChange={(enabled) => { setAgentsEnabled(enabled); markDirty(); }} /></div></div>
      <div className="settings-section divider access-control-section">
        <div className="settings-copy">
          <div className="settings-heading"><div className="settings-title-stack"><h4>Access Control</h4></div></div>
          <p>Who may talk to agents, and who may mutate (resolve findings, update schedules, start delivery). Add Allowed chat IDs to let Dylan/Milchick reply in those groups when @mentioned.</p>
          {Boolean(accessDraft.legacy_warning ?? agentsPayload.access?.legacy_warning) && (
            <p className="schedule-note">Legacy allow mode is unsafe for local agents. Prefer per-agent Access &amp; Exposure with default_policy=deny.</p>
          )}
        </div>
        <div className="settings-control wide access-control-panel">
          <div className="form-grid compact">
            <Field label="Allowed chat IDs" help="Whitelist group chats. Dylan/Milchick stay DM-only unless a chat is listed here; @mention is still required in groups."><input value={(accessDraft.allowed_chat_ids || []).join(", ")} placeholder="oc_…" onChange={(event) => { setAccessDraft((current) => ({ ...current, allowed_chat_ids: event.target.value.split(",").map((v) => v.trim()).filter(Boolean) })); markDirty(); }} /></Field>
            <Field label="Allowed user IDs" help="Empty = all users may ask read-only questions."><input value={(accessDraft.allowed_user_ids || []).join(", ")} placeholder="ou_…" onChange={(event) => { setAccessDraft((current) => ({ ...current, allowed_user_ids: event.target.value.split(",").map((v) => v.trim()).filter(Boolean) })); markDirty(); }} /></Field>
            <Field label="Mutation user IDs" help="Required for resolve / schedule update / delivery start. Fail-closed when empty."><input value={(accessDraft.mutation_allowed_user_ids || []).join(", ")} placeholder="ou_… required for mutations" onChange={(event) => { setAccessDraft((current) => ({ ...current, mutation_allowed_user_ids: event.target.value.split(",").map((v) => v.trim()).filter(Boolean) })); markDirty(); }} /></Field>
            <Field label="Admin user IDs" help="Admins can also mutate."><input value={(accessDraft.admin_user_ids || []).join(", ")} placeholder="ou_…" onChange={(event) => { setAccessDraft((current) => ({ ...current, admin_user_ids: event.target.value.split(",").map((v) => v.trim()).filter(Boolean) })); markDirty(); }} /></Field>
          </div>
          {accessMappings.length > 0 && (
            <div className="access-mapping-list">
              {accessMappings.map(([label, ids]) => (
                <div className="access-mapping-row" key={label}>
                  <span>{label}</span>
                  <div className="access-mapping-values">
                    {ids.map((id) => (
                      <em key={`${label}-${id}`}>
                        <strong>{feishuName(id) || "Unknown"}</strong>
                        <code title={id}>{shortFeishuId(id)}</code>
                      </em>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          {(recentPeople.length > 0 || recentChats.length > 0) && (
            <div className="access-identity-panel">
              {recentPeople.length > 0 && (
                <div className="access-identity-group">
                  <div className="access-identity-heading">
                    <span>Recent people</span>
                    <small>Click to add as mutation user</small>
                  </div>
                  <div className="access-identity-chips">
                    {recentPeople.map((person) => (
                      <button
                        type="button"
                        className="access-chip"
                        key={`user-${person.id}`}
                        onClick={() => addAccessId("mutation_allowed_user_ids", String(person.id))}
                        title={`Add ${feishuLabel(String(person.id))} to Mutation user IDs`}
                      >
                        <strong>{person.name || feishuName(String(person.id)) || "Unknown"}</strong>
                        <code>{shortFeishuId(String(person.id))}</code>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {recentChats.length > 0 && (
                <div className="access-identity-group">
                  <div className="access-identity-heading">
                    <span>Recent chats</span>
                    <small>Click to allow the chat</small>
                  </div>
                  <div className="access-identity-chips">
                    {recentChats.map((chat) => (
                      <button
                        type="button"
                        className="access-chip chat"
                        key={`chat-${chat.id}`}
                        onClick={() => addAccessId("allowed_chat_ids", String(chat.id))}
                        title={`Add ${feishuLabel(String(chat.id))} to Allowed chat IDs`}
                      >
                        <strong>{chat.name || feishuName(String(chat.id)) || "Chat"}</strong>
                        <code>{shortFeishuId(String(chat.id))}</code>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {recentPeople[0]?.id && (
                <button
                  type="button"
                  className="button ghost access-owner-button"
                  onClick={() => {
                    const id = String(recentPeople[0].id);
                    addAccessId("mutation_allowed_user_ids", id);
                    addAccessId("admin_user_ids", id);
                    addAccessId("allowed_user_ids", id);
                  }}
                >
                  Use {feishuName(String(recentPeople[0].id)) || "latest user"} as owner
                </button>
              )}
            </div>
          )}
          {recentPeople.length === 0 && (
            <p className="schedule-note access-empty-note">No recent Feishu people yet. Message Dylan or Mark once, then refresh Settings.</p>
          )}
        </div>
      </div>
      {agentDrafts.map((agent, index) => (
        <div className={`settings-section divider agent-role-section`} key={agent.id}>
          <div className="settings-copy">
            <div className="settings-heading"><div className="settings-title-stack"><h4>{agent.display_name}</h4><span className="muted">{agent.title}</span></div></div>
            <p>Role {agent.role} · workflow {agent.workflow}. Feishu credentials live in {text(agent.credentials_path, "~/.lumen/.env.local")}. SOUL overrides are at {text(agent.soul_override_path)} ({agent.soul_source}). Restart `lumen agents start` after changing App ID/Secret.</p>
            <p className="schedule-note">Security: exposure {text(agent.security?.exposure_mode, "restricted_team")} · dm_only {String(agent.security?.dm_only ?? false)} · host_read {text(agent.security?.host_read, "deny")} · runner {text(agent.security?.runner, "local_isolated")} · mutations {text(agent.security?.mutations, "brokered")} · sandbox {text(agent.security?.sandbox, "enabled")}</p>
          </div>
          <div className="settings-control wide">
            <div className="form-grid compact">
              <Field label="Feishu App ID"><input value={agent.app_id || ""} placeholder={agent.app_id_masked || "cli_…"} onChange={(event) => updateAgent(agent.id, { app_id: event.target.value })} /></Field>
              <Field label="Feishu App Secret" help={agent.app_secret_configured ? `Configured (${agent.app_secret_masked || "set"}). Leave blank to keep.` : "Required for Feishu client login."}><input type="password" value={agent.app_secret || ""} placeholder={agent.app_secret_configured ? "Leave blank to keep current secret" : "Enter app secret"} onChange={(event) => updateAgent(agent.id, { app_secret: event.target.value })} autoComplete="new-password" /></Field>
              <Field label="Conversation"><select value={agent.conversation_enabled ? "on" : "off"} onChange={(event) => updateAgent(agent.id, { conversation_enabled: event.target.value === "on" })}><option value="on">Enabled</option><option value="off">Paused</option></select></Field>
              <ModelField label="Cursor model" value={agent.model} onChange={(value) => updateAgent(agent.id, { model: value })} markDirty={markDirty} />
              <Field label="Soft timeout, seconds"><input type="number" min="10" max="3600" value={agent.soft_timeout_seconds} onChange={(event) => updateAgent(agent.id, { soft_timeout_seconds: Number(event.target.value) || 90 })} /></Field>
              <Field label="Hard timeout, seconds"><input type="number" min="30" max="7200" value={agent.hard_timeout_seconds} onChange={(event) => updateAgent(agent.id, { hard_timeout_seconds: Number(event.target.value) || 300 })} /></Field>
              <Field label="Typing reaction"><select value={agent.reaction_enabled ? "on" : "off"} onChange={(event) => updateAgent(agent.id, { reaction_enabled: event.target.value === "on" })}><option value="on">Enabled</option><option value="off">Off</option></select></Field>
              <Field label="Max concurrent jobs"><input type="number" min="1" max="32" value={agent.max_concurrent_jobs} onChange={(event) => updateAgent(agent.id, { max_concurrent_jobs: Number(event.target.value) || 3 })} /></Field>
              <Field label="SOUL version"><input value={agent.soul_version} onChange={(event) => updateAgent(agent.id, { soul_version: event.target.value })} /></Field>
              <Field label="Role id" help="Runtime identity is managed by the Agent registry."><input className="settings-readonly-field" value={agent.role} readOnly aria-readonly="true" /></Field>
              <Field label="Workflow" help="Workflow ownership is managed by the Agent registry."><input className="settings-readonly-field" value={agent.workflow} readOnly aria-readonly="true" /></Field>
            </div>
            <label className="field agent-soul-field"><span>SOUL.md</span><textarea rows={index === 0 ? 16 : 14} value={agent.soul} spellCheck={false} onChange={(event) => updateAgent(agent.id, { soul: event.target.value })} /></label>
          </div>
        </div>
      ))}
      {agentDrafts.length === 0 && <div className="settings-section divider"><Empty label="No agent roles available yet." /></div>}
      </Panel>
    </section>
    <section className="settings-cluster" id="settings-project">
      <div className="settings-cluster-heading"><div><span>03 · BUSINESS OUTPUT</span><h2>Project output</h2><p>Defaults used when Mark and Milchick turn a request into a testable Story.</p></div><a href="#settings-runtime">Next: Runtime &amp; integrations <ChevronRight size={13} /></a></div>
      <Panel title="Test Cases" action={<span className="muted">Mark · {project || "project"}</span>}>
      <div className="settings-section">
        <div className="settings-copy">
          <div className="settings-heading"><div className="settings-title-stack"><h4>Generation language</h4></div></div>
          <p>Controls the language Mark writes into the Feishu Spreadsheet for this project. Traditional Chinese is the default for mbpass.</p>
        </div>
        <div className="settings-control wide">
          <div className="form-grid compact">
            <Field label="Output language">
              <select
                value={testCaseDraft.language || "zh-Hant"}
                onChange={(event) => {
                  setTestCaseDraft((current) => ({ ...current, language: event.target.value }));
                  markDirty();
                }}
              >
                <option value="zh-Hant">Traditional Chinese (zh-Hant)</option>
                <option value="zh-Hans">Simplified Chinese (zh-Hans)</option>
                <option value="en">English</option>
              </select>
            </Field>
            <Field label="Spreadsheet tab name">
              <input
                value={testCaseDraft.table_name || "Sheet1"}
                onChange={(event) => {
                  setTestCaseDraft((current) => ({ ...current, table_name: event.target.value }));
                  markDirty();
                }}
              />
            </Field>
            <Field
              label="Spreadsheet token / URL"
              help={testCaseDraft.base_app_token_configured
                ? `Configured (${testCaseDraft.base_app_token_masked || "set"}). Leave blank to keep. Env: ${testCaseDraft.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN"}`
                : `Stored in ~/.lumen/.env.local as ${testCaseDraft.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN"}`}
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
          <p className="schedule-note">After changing language or sheet, ask Milchick/Mark to re-generate the story so new rows use the selected sheet.</p>
        </div>
      </div>
      </Panel>
    </section>
    <section className="settings-cluster" id="settings-runtime">
      <div className="settings-cluster-heading"><div><span>04 · OPERATING DETAILS</span><h2>Runtime &amp; integrations</h2><p>Model selection, publish behavior, notifications, and local secret values.</p></div><a href="#settings-automation">Back to Automation <ChevronLeft size={13} /></a></div>
      <Panel title="Execution Models"><div className="settings-section"><div className="settings-copy"><h4>Cursor model</h4><p>Choose a preset or enter a custom Cursor model ID. Custom values must be supported by Cursor; Lumen does not validate model availability.</p></div><div className="settings-control wide"><div className="form-grid compact"><ModelField label="Auto Scan model" value={scanModel} onChange={setScanModel} markDirty={markDirty} /><ModelField label="Auto Delivery model" value={deliveryModel} onChange={setDeliveryModel} markDirty={markDirty} /><ModelField label="Auto Patch model" value={patchModel} onChange={setPatchModel} markDirty={markDirty} /></div></div></div></Panel>
    <Panel title="Publish Policy"><div className="settings-section"><div className="settings-copy"><h4>Automation outcome</h4><p>Direct push uses the repository credentials already configured for Git; PR and Merge use GitHub CLI. Auto Scan keeps a PR review gate and does not support direct push.</p></div><div className="settings-control wide"><div className="form-grid compact"><Field label="Auto Scan"><select value={scanPublishMode} onChange={(event) => { setScanPublishMode(event.target.value); markDirty(); }}><option value="pr">Open pull request</option><option value="merge">Merge after pull request</option></select></Field><Field label="Auto Delivery"><select value={deliveryPublishMode} onChange={(event) => { setDeliveryPublishMode(event.target.value); markDirty(); }}><option value="pr">Open pull request</option><option value="merge">Merge after pull request</option><option value="direct">Push directly to main branch</option></select></Field><Field label="Auto Patch"><select value={patchPublishMode} onChange={(event) => { setPatchPublishMode(event.target.value); markDirty(); }}><option value="pr">Open pull request</option><option value="direct">Push directly to main branch</option></select></Field></div></div></div></Panel>
    <Panel title="Notifications"><div className="settings-section"><div className="settings-copy"><h4>Feishu notifications</h4><p>Control whether Scan and Delivery post cards to the configured Feishu webhook. The webhook URL still lives under Variable Keys.</p></div><div className="settings-toggle"><ScheduleToggle enabled={feishuEnabled} onChange={(enabled) => { setFeishuEnabled(enabled); markDirty(); }} /></div></div></Panel>
    <Panel title="Variable Keys" action={<span className="muted">Stored only in this workspace</span>}><div className="settings-section"><div className="settings-copy"><h4>Available keys</h4><p>Reveal a value to inspect it, or enter a replacement directly. Values are saved without display quotes.</p></div><div className="settings-control wide"><div className="secret-list">{configured.length ? configured.map((name: string) => { const value = changedSecrets[name] ?? secrets[name] ?? ""; return <div className="secret-row" key={name}><code>{name}</code><input type={secrets[name] || changedSecrets[name] !== undefined ? "text" : "password"} value={value} placeholder="Reveal or enter a replacement value" aria-label={`Value for ${name}`} onChange={(event) => { const next = event.target.value; setChangedSecrets((current) => ({ ...current, [name]: next })); markDirty(); }} /><div><IconButton label="Reveal value" onClick={() => void reveal(name)}>{secrets[name] ? <EyeOff size={15} /> : <Eye size={15} />}</IconButton><IconButton label="Copy value" onClick={() => void copy(name)}><Copy size={15} /></IconButton></div></div>; }) : <Empty label="No local integration keys configured." />}</div></div></div></Panel>
      </section>
    <footer className="settings-save-bar"><span className={dirty ? "settings-save-status unsaved" : "settings-save-status"}>{saving ? "Saving settings…" : dirty ? "You have unsaved changes" : "All changes saved"}</span><button className={`button primary${saving ? " is-busy" : ""}`} disabled={!dirty || saving} onClick={() => void saveAll()}>{saving ? <LoaderCircle size={15} className="spin" /> : <Save size={15} />}{saving ? "Saving…" : "Save changes"}</button></footer>
  </div>;
}

function ScheduleToggle({ enabled, onChange }: { enabled: boolean; onChange: (enabled: boolean) => void }) { return <label className="schedule-toggle"><input type="checkbox" checked={enabled} onChange={(event) => onChange(event.target.checked)} /><span aria-hidden="true" /><em>{enabled ? "Enabled" : "Paused"}</em></label>; }

createRoot(document.getElementById("root")!).render(<App />);
