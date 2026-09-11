import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Locale = "en" | "zh-CN" | "zh-TW";

const defaultLocale: Locale = "zh-CN";
const localeStorageKey = "lumon.locale";

const zhCN = {
  "app.documentTitle": "Lumon 控制台",
  "app.loading": "正在加载 Lumon 控制台…",
  "app.dashboardSections": "控制台区域",
  "app.currentWorkspace": "当前工作区",
  "app.overview": "总览",
  "app.settings": "配置",
  "app.slogan": "让工程清晰可见。",
  "app.workspaceConsole": "工作区控制台",
  "app.active": "当前",
  "app.localService": "本机服务",
  "app.localOnly": "仅限本机",
  "app.unsavedWorkspaceConfirm": "当前配置尚未保存，确定要切换工作区吗？",
  "app.unsavedViewConfirm": "当前配置尚未保存，确定要离开配置页吗？",
  "app.workspaceReady": "工作区「{name}」已准备完成。",
  "app.settingsSaved": "飞书 Webhook 配置已保存。",
  "app.workspaceRefreshed": "工作区数据已刷新。",
  "app.readingWorkspace": "正在读取工作区…",
  "app.dashboardRequestFailed": "控制台请求失败，请稍后重试。",
  "app.close": "关闭",
  "app.brandAlt": "Lumon",
  "app.companyLogoAlt": "公司 Logo",
  "language.label": "界面语言",
  "language.english": "English",
  "language.simplifiedChinese": "简体中文",
  "language.traditionalChinese": "繁體中文",
  "picker.currentWorkspace": "当前工作区",
  "picker.needsCheck": "需要检查",
  "health.available": "可用",
  "health.pathMissing": "路径不存在",
  "health.invalidConfig": "配置异常",
  "onboarding.localEyebrow": "本机工作区控制台",
  "onboarding.title": "先连接一个工作区",
  "onboarding.copy": "控制台会把工作区列表和配置保存在当前用户的 Lumon 目录中。",
  "onboarding.operationAria": "工作区操作",
  "onboarding.initializeNew": "初始化新的",
  "onboarding.addExisting": "添加已有的",
  "onboarding.workspacePath": "工作区路径",
  "onboarding.workspacePathPlaceholder": "例如：/Users/me/Projects/my-workspace",
  "onboarding.nameOptional": "名称（可选）",
  "onboarding.namePlaceholder": "默认使用目录名称",
  "onboarding.repositoryUrlOptional": "代码仓库 URL（可选，每行一个）",
  "onboarding.repositoryPlaceholder": "git@github.com:org/product.git",
  "onboarding.authHelp": "私有代码仓库认证继续使用系统 Git、SSH Agent 或 credential helper。",
  "onboarding.chooseFolder": "选择文件夹",
  "onboarding.chooseFolderAria": "选择 Workspace 文件夹",
  "onboarding.folderSelectionFailed": "无法打开文件夹选择器，请手动输入路径。",
  "onboarding.processing": "处理中…",
  "onboarding.initializeAction": "初始化工作区",
  "onboarding.addAction": "添加工作区",
  "onboarding.pathRequired": "请先输入工作区路径。",
  "onboarding.reloadFailed": "工作区已初始化，但未能重新加载注册信息。",
  "onboarding.operationFailed": "工作区操作失败。",
  "overview.eyebrow": "工作区总览",
  "overview.refresh": "刷新",
  "overview.repositories": "代码仓库",
  "overview.registeredRepositories": "已登记代码仓库",
  "overview.status": "工作区状态",
  "overview.initialized": "已初始化",
  "overview.version": "Lumon {version}",
  "overview.id": "工作区 ID",
  "overview.createdAt": "创建于 {date}",
  "overview.mappingEyebrow": "代码仓库映射",
  "overview.repositoriesTitle": "代码仓库",
  "overview.emptyTitle": "还没有代码仓库",
  "overview.emptyCopy": "可以通过命令行的 init 流程添加代码仓库。",
  "overview.healthNormal": "正常",
  "overview.healthAbnormal": "异常",
  "settings.eyebrow": "工作区配置",
  "settings.title": "配置",
  "settings.subtitle": "只影响当前选中的工作区。",
  "settings.unsaved": "有未保存更改",
  "settings.notifications": "通知",
  "settings.feishu": "飞书 Webhook",
  "settings.configured": "已配置",
  "settings.notConfigured": "未配置",
  "settings.description": "保存后，未来的工作流可以使用此 Webhook 发送通知。已保存地址会在输入框中以脱敏形式展示。",
  "settings.enabled": "已启用",
  "settings.disabled": "已停用",
  "settings.toggleAria": "启用飞书通知",
  "settings.legend": "飞书 Webhook 配置",
  "settings.webhookUrl": "Webhook URL",
  "settings.replacePlaceholder": "输入新地址以替换",
  "settings.newPlaceholder": "https://open.feishu.cn/open-apis/bot/v2/hook/...",
  "settings.security": "已保存地址会在输入框中脱敏展示，完整 URL 只保存在当前用户的 Lumon profile 中。",
  "settings.test": "测试 Webhook",
  "settings.save": "保存配置",
  "settings.testSuccess": "飞书 Webhook 测试消息已发送。",
  "settings.futureEyebrow": "未来配置",
  "settings.futureTitle": "可扩展配置域",
  "settings.futureCopy": "Auto Delivery 等能力会以独立的类型化设置加入，不会变成一个不可校验的通用键值编辑器。",
} as const;

type MessageKey = keyof typeof zhCN;
type MessageSet = Record<MessageKey, string>;

const messages: Record<Locale, MessageSet> = {
  "zh-CN": zhCN,
  "zh-TW": {
    "app.documentTitle": "Lumon 控制台",
    "app.loading": "正在載入 Lumon 控制台…",
    "app.dashboardSections": "控制台區域",
    "app.currentWorkspace": "目前工作區",
    "app.overview": "總覽",
    "app.settings": "設定",
    "app.slogan": "讓工程清晰可見。",
    "app.workspaceConsole": "工作區控制台",
    "app.active": "目前",
    "app.localService": "本機服務",
    "app.localOnly": "僅限本機",
    "app.unsavedWorkspaceConfirm": "目前設定尚未儲存，確定要切換工作區嗎？",
    "app.unsavedViewConfirm": "目前設定尚未儲存，確定要離開設定頁嗎？",
    "app.workspaceReady": "工作區「{name}」已準備完成。",
    "app.settingsSaved": "飛書 Webhook 設定已儲存。",
    "app.workspaceRefreshed": "工作區資料已重新整理。",
    "app.readingWorkspace": "正在讀取工作區…",
    "app.dashboardRequestFailed": "控制台請求失敗，請稍後再試。",
    "app.close": "關閉",
    "app.brandAlt": "Lumon",
    "app.companyLogoAlt": "公司 Logo",
    "language.label": "介面語言",
    "language.english": "English",
    "language.simplifiedChinese": "簡體中文",
    "language.traditionalChinese": "繁體中文",
    "picker.currentWorkspace": "目前工作區",
    "picker.needsCheck": "需要檢查",
    "health.available": "可用",
    "health.pathMissing": "路徑不存在",
    "health.invalidConfig": "設定異常",
    "onboarding.localEyebrow": "本機工作區控制台",
    "onboarding.title": "先連接一個工作區",
    "onboarding.copy": "控制台會將工作區清單和設定儲存在目前使用者的 Lumon 目錄中。",
    "onboarding.operationAria": "工作區操作",
    "onboarding.initializeNew": "初始化新的",
    "onboarding.addExisting": "新增已有的",
    "onboarding.workspacePath": "工作區路徑",
    "onboarding.workspacePathPlaceholder": "例如：/Users/me/Projects/my-workspace",
    "onboarding.nameOptional": "名稱（選填）",
    "onboarding.namePlaceholder": "預設使用目錄名稱",
    "onboarding.repositoryUrlOptional": "程式碼儲存庫 URL（選填，每行一個）",
    "onboarding.repositoryPlaceholder": "git@github.com:org/product.git",
    "onboarding.authHelp": "私有程式碼儲存庫認證會繼續使用系統 Git、SSH Agent 或 credential helper。",
    "onboarding.chooseFolder": "選擇資料夾",
    "onboarding.chooseFolderAria": "選擇 Workspace 資料夾",
    "onboarding.folderSelectionFailed": "無法開啟資料夾選擇器，請手動輸入路徑。",
    "onboarding.processing": "處理中…",
    "onboarding.initializeAction": "初始化工作區",
    "onboarding.addAction": "新增工作區",
    "onboarding.pathRequired": "請先輸入工作區路徑。",
    "onboarding.reloadFailed": "工作區已初始化，但無法重新載入登錄資訊。",
    "onboarding.operationFailed": "工作區操作失敗。",
    "overview.eyebrow": "工作區總覽",
    "overview.refresh": "重新整理",
    "overview.repositories": "儲存庫",
    "overview.registeredRepositories": "已登錄儲存庫",
    "overview.status": "工作區狀態",
    "overview.initialized": "已初始化",
    "overview.version": "Lumon {version}",
    "overview.id": "工作區 ID",
    "overview.createdAt": "建立於 {date}",
    "overview.mappingEyebrow": "儲存庫對應",
    "overview.repositoriesTitle": "程式碼儲存庫",
    "overview.emptyTitle": "尚無儲存庫",
    "overview.emptyCopy": "可透過命令列的 init 流程新增程式碼儲存庫。",
    "overview.healthNormal": "正常",
    "overview.healthAbnormal": "異常",
    "settings.eyebrow": "工作區設定",
    "settings.title": "設定",
    "settings.subtitle": "只影響目前選取的工作區。",
    "settings.unsaved": "有未儲存變更",
    "settings.notifications": "通知",
    "settings.feishu": "飛書 Webhook",
    "settings.configured": "已設定",
    "settings.notConfigured": "未設定",
    "settings.description": "儲存後，未來的工作流程可以使用此 Webhook 傳送通知。已儲存地址會在輸入框中以遮罩形式顯示。",
    "settings.enabled": "已啟用",
    "settings.disabled": "已停用",
    "settings.toggleAria": "啟用飛書通知",
    "settings.legend": "飛書 Webhook 設定",
    "settings.webhookUrl": "Webhook URL",
    "settings.replacePlaceholder": "輸入新地址以替換",
    "settings.newPlaceholder": "https://open.feishu.cn/open-apis/bot/v2/hook/...",
    "settings.security": "已儲存地址會在輸入框中以遮罩形式顯示，完整 URL 只儲存在目前使用者的 Lumon profile 中。",
    "settings.test": "測試 Webhook",
    "settings.save": "儲存設定",
    "settings.testSuccess": "飛書 Webhook 測試訊息已傳送。",
    "settings.futureEyebrow": "未來設定",
    "settings.futureTitle": "可擴充設定域",
    "settings.futureCopy": "Auto Delivery 等能力會以獨立的型別化設定加入，不會變成不可驗證的通用鍵值編輯器。",
  },
  en: {
    "app.documentTitle": "Lumon Dashboard",
    "app.loading": "Loading Lumon Dashboard…",
    "app.dashboardSections": "Dashboard sections",
    "app.currentWorkspace": "Current workspace",
    "app.overview": "Overview",
    "app.settings": "Settings",
    "app.slogan": "Engineering, made legible.",
    "app.workspaceConsole": "Workspace console",
    "app.active": "ACTIVE",
    "app.localService": "Local service",
    "app.localOnly": "Local only",
    "app.unsavedWorkspaceConfirm": "Current settings are unsaved. Switch workspaces anyway?",
    "app.unsavedViewConfirm": "Current settings are unsaved. Leave the settings page anyway?",
    "app.workspaceReady": "Workspace “{name}” is ready.",
    "app.settingsSaved": "Feishu Webhook settings saved.",
    "app.workspaceRefreshed": "Workspace data refreshed.",
    "app.readingWorkspace": "Reading workspace…",
    "app.dashboardRequestFailed": "Dashboard request failed. Please try again.",
    "app.close": "Close",
    "app.brandAlt": "Lumon",
    "app.companyLogoAlt": "Company logo",
    "language.label": "Interface language",
    "language.english": "English",
    "language.simplifiedChinese": "简体中文",
    "language.traditionalChinese": "繁體中文",
    "picker.currentWorkspace": "Current workspace",
    "picker.needsCheck": "needs review",
    "health.available": "Available",
    "health.pathMissing": "Path missing",
    "health.invalidConfig": "Invalid configuration",
    "onboarding.localEyebrow": "Local workspace console",
    "onboarding.title": "Connect a workspace first",
    "onboarding.copy": "The Dashboard keeps your workspace list and settings in the current user's Lumon directory.",
    "onboarding.operationAria": "Workspace actions",
    "onboarding.initializeNew": "Initialize new",
    "onboarding.addExisting": "Add existing",
    "onboarding.workspacePath": "Workspace path",
    "onboarding.workspacePathPlaceholder": "e.g. /Users/me/Projects/my-workspace",
    "onboarding.nameOptional": "Name (optional)",
    "onboarding.namePlaceholder": "Uses the directory name by default",
    "onboarding.repositoryUrlOptional": "Repository URL (optional, one per line)",
    "onboarding.repositoryPlaceholder": "git@github.com:org/product.git",
    "onboarding.authHelp": "Private repository authentication continues to use system Git, SSH Agent, or a credential helper.",
    "onboarding.chooseFolder": "Choose folder",
    "onboarding.chooseFolderAria": "Choose a Workspace folder",
    "onboarding.folderSelectionFailed": "The folder selector could not be opened. Enter the path manually.",
    "onboarding.processing": "Processing…",
    "onboarding.initializeAction": "Initialize workspace",
    "onboarding.addAction": "Add workspace",
    "onboarding.pathRequired": "Enter a workspace path first.",
    "onboarding.reloadFailed": "Workspace initialized, but its registry entry could not be reloaded.",
    "onboarding.operationFailed": "Workspace operation failed.",
    "overview.eyebrow": "Workspace overview",
    "overview.refresh": "Refresh",
    "overview.repositories": "Repositories",
    "overview.registeredRepositories": "Registered repositories",
    "overview.status": "Workspace status",
    "overview.initialized": "Initialized",
    "overview.version": "Lumon {version}",
    "overview.id": "Workspace ID",
    "overview.createdAt": "Created {date}",
    "overview.mappingEyebrow": "Repository mapping",
    "overview.repositoriesTitle": "Repositories",
    "overview.emptyTitle": "No repositories yet",
    "overview.emptyCopy": "Add repositories through the CLI init flow.",
    "overview.healthNormal": "Healthy",
    "overview.healthAbnormal": "Unhealthy",
    "settings.eyebrow": "Workspace settings",
    "settings.title": "Settings",
    "settings.subtitle": "Only affects the selected workspace.",
    "settings.unsaved": "Unsaved changes",
    "settings.notifications": "Notifications",
    "settings.feishu": "Feishu Webhook",
    "settings.configured": "Configured",
    "settings.notConfigured": "Not configured",
    "settings.description": "Once saved, future workflows can use this Webhook for notifications. The saved address is shown masked in the input.",
    "settings.enabled": "Enabled",
    "settings.disabled": "Disabled",
    "settings.toggleAria": "Enable Feishu notifications",
    "settings.legend": "Feishu Webhook settings",
    "settings.webhookUrl": "Webhook URL",
    "settings.replacePlaceholder": "Enter a new address to replace it",
    "settings.newPlaceholder": "https://open.feishu.cn/open-apis/bot/v2/hook/...",
    "settings.security": "The saved address is displayed masked in the input; the complete URL is stored only in the current user's Lumon profile.",
    "settings.test": "Test Webhook",
    "settings.save": "Save settings",
    "settings.testSuccess": "Feishu Webhook test message sent.",
    "settings.futureEyebrow": "Future settings",
    "settings.futureTitle": "Extensible settings domains",
    "settings.futureCopy": "Capabilities such as Auto Delivery will be added as typed settings domains, not as an unvalidated generic key-value editor.",
  },
};

export const localeOptions: readonly {
  value: Locale;
  labelKey: "language.english" | "language.simplifiedChinese" | "language.traditionalChinese";
}[] = [
  { value: "en", labelKey: "language.english" },
  { value: "zh-CN", labelKey: "language.simplifiedChinese" },
  { value: "zh-TW", labelKey: "language.traditionalChinese" },
];

export type Translator = (
  key: MessageKey,
  values?: Record<string, string | number>,
) => string;

export function translate(
  locale: Locale,
  key: MessageKey,
  values?: Record<string, string | number>,
): string {
  const template = messages[locale][key] ?? messages[defaultLocale][key];
  return template.replace(/\{(\w+)\}/g, (placeholder, name: string) => {
    const value = values?.[name];
    return value === undefined ? placeholder : String(value);
  });
}

interface I18nContextValue {
  locale: Locale;
  localeOptions: typeof localeOptions;
  setLocale: (locale: Locale) => void;
  t: Translator;
  formatDate: (value: string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [locale, setLocaleState] = useState<Locale>(() => readInitialLocale());

  const setLocale = useCallback((nextLocale: Locale): void => {
    setLocaleState(nextLocale);
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(localeStorageKey, locale);
    } catch {
      // A locked-down browser may not expose localStorage; the session still works.
    }
    document.documentElement.lang = locale;
    document.title = translate(locale, "app.documentTitle");
  }, [locale]);

  const t = useCallback<Translator>(
    (key, values) => translate(locale, key, values),
    [locale],
  );

  const formatDate = useCallback(
    (value: string): string => {
      const date = new Date(value);
      if (Number.isNaN(date.valueOf())) return value;
      const dateLocale = locale === "en" ? "en-US" : locale;
      return date.toLocaleDateString(dateLocale);
    },
    [locale],
  );

  const contextValue = useMemo<I18nContextValue>(
    () => ({ locale, localeOptions, setLocale, t, formatDate }),
    [formatDate, locale, setLocale, t],
  );

  return <I18nContext.Provider value={contextValue}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used within I18nProvider.");
  return context;
}

export function LanguagePicker({ className }: { className?: string }): React.JSX.Element {
  const { locale, localeOptions, setLocale, t } = useI18n();
  const classes = className ? `language-picker ${className}` : "language-picker";

  return (
    <label className={classes}>
      <span className="sr-only">{t("language.label")}</span>
      <select
        aria-label={t("language.label")}
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
      >
        {localeOptions.map((option) => <option key={option.value} value={option.value}>{t(option.labelKey)}</option>)}
      </select>
    </label>
  );
}

function readInitialLocale(): Locale {
  try {
    const stored = window.localStorage.getItem(localeStorageKey);
    if (isLocale(stored)) return stored;
  } catch {
    // Fall back to the browser language when localStorage is unavailable.
  }

  const browserLanguage = navigator.language.toLowerCase();
  if (browserLanguage.startsWith("zh-tw") || browserLanguage.startsWith("zh-hk")) {
    return "zh-TW";
  }
  if (browserLanguage.startsWith("zh")) return "zh-CN";
  return "en";
}

function isLocale(value: string | null): value is Locale {
  return value === "en" || value === "zh-CN" || value === "zh-TW";
}
