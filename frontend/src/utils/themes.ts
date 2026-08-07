/**
 * Chat theming — shared color tokens for the dashboard preview.
 *
 * Every chat surface (header, bubbles, thinking/tools blocks, toolbar,
 * input, send button, sources, markdown internals) is driven by ONE set of
 * tokens. The preview applies them as CSS variables (`--chat-*`) on the chat
 * shell; the embeddable widget (`backend/app/widget/widget.js`) carries the
 * SAME keys/defaults in its own theme object so both sides stay in parity.
 *
 * Keep the token list and the preset values in sync with:
 *   - `frontend/src/assets/main.css`  (:root `--chat-*` defaults)
 *   - `backend/app/widget/widget.js`  (DEFAULT_THEME / THEME_PRESETS)
 */

export const THEME_COLOR_KEYS = [
  'headerBg',
  'headerText',
  'msgsBg',
  'aiBubbleBg',
  'aiBubbleText',
  'aiBubbleBorder',
  'userBubbleBg',
  'userBubbleText',
  'thinkingBg',
  'thinkingText',
  'thinkingBorder',
  'toolsBg',
  'toolsText',
  'toolsBorder',
  'toolBg',
  'btnBg',
  'btnText',
  'inputBg',
  'inputBorder',
  'inputText',
  'toolbarBg',
  'toolbarBorder',
  'accent',
  'accentSoft',
  'muted',
  'link',
  'codeBg',
  'preBg',
  'preBorder',
  'tableBorder',
  'blockquoteText',
  'sourcesLabel',
  'toolSuccessText',
  'toolSuccessBg',
  'toolSuccessBorder',
  'toolErrorText',
  'toolErrorBg',
  'toolErrorBorder',
  'errBg',
  'errText',
  'errBorder',
] as const

export type ChatColorKey = (typeof THEME_COLOR_KEYS)[number]

/** A fully-specified chat color theme (every token has a concrete color). */
export type ChatTheme = Record<ChatColorKey, string>

/** A named, ready-to-use palette. */
export interface ThemePreset extends ChatTheme {
  /** Machine id, e.g. 'indigo' (used by the widget's data-theme-name). */
  name: string
  /** Human label shown in the preview panel. */
  label: string
}

/** Default values — identical to the pre-theming look (and to the widget defaults). */
const DEFAULT: ChatTheme = {
  headerBg: '#211f1b',
  headerText: '#f6f5f1',
  msgsBg: '#f1efe9',
  aiBubbleBg: '#ffffff',
  aiBubbleText: '#211f1b',
  aiBubbleBorder: '#e6e3da',
  userBubbleBg: '#211f1b',
  userBubbleText: '#f6f5f1',
  thinkingBg: '#f6f5f1',
  thinkingText: '#6f6b64',
  thinkingBorder: '#e6e3da',
  toolsBg: '#f6f5f1',
  toolsText: '#211f1b',
  toolsBorder: '#e6e3da',
  toolBg: '#ffffff',
  btnBg: '#211f1b',
  btnText: '#f6f5f1',
  inputBg: '#ffffff',
  inputBorder: '#d6d2c6',
  inputText: '#211f1b',
  toolbarBg: '#ffffff',
  toolbarBorder: '#e6e3da',
  accent: '#a9502a',
  accentSoft: '#f4e8de',
  muted: '#6f6b64',
  link: '#a9502a',
  codeBg: '#f1efe9',
  preBg: '#f6f5f1',
  preBorder: '#e6e3da',
  tableBorder: '#e6e3da',
  blockquoteText: '#45423b',
  sourcesLabel: '#211f1b',
  toolSuccessText: '#3c5a39',
  toolSuccessBg: '#edf3ec',
  toolSuccessBorder: '#cfe0cc',
  toolErrorText: '#a3321f',
  toolErrorBg: '#fdecec',
  toolErrorBorder: '#f5d0cc',
  errBg: '#fdecec',
  errText: '#8d3f1e',
  errBorder: '#f5d0cc',
}

function buildPreset(name: string, label: string, overrides: Partial<ChatTheme>): ThemePreset {
  return { ...DEFAULT, ...overrides, name, label }
}

/** Ready-to-use palettes. `platform` is the default (brand) theme — fresh
 *  agents are created with chat_theme baked to this preset. */
export const THEME_PRESETS: ThemePreset[] = [
  buildPreset('platform', 'Platform', {}),
  buildPreset('indigo', 'Indigo', {
    headerBg: '#4f46e5',
    userBubbleBg: '#4f46e5',
    btnBg: '#4f46e5',
    accent: '#4f46e5',
    accentSoft: '#eef2ff',
    link: '#2563eb',
  }),
  buildPreset('emerald', 'Emerald', {
    headerBg: '#059669',
    userBubbleBg: '#059669',
    btnBg: '#059669',
    accent: '#059669',
    accentSoft: '#d1fae5',
  }),
  buildPreset('rose', 'Rose', {
    headerBg: '#e11d48',
    userBubbleBg: '#e11d48',
    btnBg: '#e11d48',
    accent: '#e11d48',
    accentSoft: '#ffe4e6',
  }),
  buildPreset('amber', 'Amber', {
    headerBg: '#d97706',
    userBubbleBg: '#d97706',
    btnBg: '#d97706',
    accent: '#d97706',
    accentSoft: '#fef3c7',
  }),
  buildPreset('slate', 'Slate Dark', {
    headerBg: '#0f172a',
    msgsBg: '#1e293b',
    aiBubbleBg: '#334155',
    aiBubbleText: '#e2e8f0',
    aiBubbleBorder: '#475569',
    userBubbleBg: '#0ea5e9',
    thinkingBg: '#334155',
    thinkingText: '#94a3b8',
    thinkingBorder: '#475569',
    toolsBg: '#334155',
    toolsText: '#cbd5e1',
    toolsBorder: '#475569',
    toolBg: '#475569',
    btnBg: '#0ea5e9',
    inputBg: '#0f172a',
    inputBorder: '#475569',
    inputText: '#e2e8f0',
    toolbarBg: '#1e293b',
    toolbarBorder: '#334155',
    accent: '#38bdf8',
    accentSoft: '#0c4a6e',
    muted: '#94a3b8',
    link: '#38bdf8',
    codeBg: '#1e293b',
    preBg: '#1e293b',
    preBorder: '#334155',
    tableBorder: '#334155',
    blockquoteText: '#94a3b8',
    sourcesLabel: '#cbd5e1',
    toolSuccessText: '#4ade80',
    toolSuccessBg: '#14532d',
    toolSuccessBorder: '#166534',
    toolErrorText: '#f87171',
    toolErrorBg: '#7f1d1d',
    toolErrorBorder: '#b91c1c',
    errBg: '#7f1d1d',
    errText: '#fecaca',
    errBorder: '#b91c1c',
  }),
  buildPreset('ocean', 'Ocean', {
    headerBg: '#0d9488',
    userBubbleBg: '#0d9488',
    btnBg: '#0d9488',
    accent: '#0d9488',
    accentSoft: '#ccfbf1',
  }),
]

export function findPreset(name: string): ThemePreset | undefined {
  return THEME_PRESETS.find((p) => p.name === name)
}

/**
 * Effective chat header color for an agent — what the widget's launcher and
 * header actually use (mirrors widget.js resolveTheme precedence): a saved
 * custom.headerBg wins, then the saved preset's headerBg, then the platform
 * default. There is no legacy theme_color column anymore — every agent is
 * created with chat_theme baked to the `platform` preset.
 */
export function agentHeaderColor(agent: { chat_theme?: string | null }): string {
  if (agent.chat_theme) {
    try {
      const saved = JSON.parse(agent.chat_theme) as {
        preset?: string
        custom?: Partial<Record<string, string>>
      } | null
      if (saved && typeof saved === 'object') {
        if (saved.custom?.headerBg) return saved.custom.headerBg
        const preset = saved.preset ? findPreset(saved.preset) : undefined
        if (preset) return preset.headerBg
      }
    } catch {
      /* malformed chat_theme — fall through to the platform default */
    }
  }
  return defaultTheme().headerBg
}

/** The default (monochrome) theme as a plain ChatTheme — safe to mutate. */
export function defaultTheme(): ChatTheme {
  const t = {} as ChatTheme
  for (const key of THEME_COLOR_KEYS) t[key] = DEFAULT[key]
  return t
}

/** Merge partial overrides on top of a base theme. */
export function applyThemeOverrides(base: ChatTheme, overrides: Partial<ChatTheme>): ChatTheme {
  return { ...base, ...overrides }
}

/**
 * Soften a hex color into an rgba string (used for chip backgrounds derived
 * from the chip's border/text color). Handles 3- and 6-digit hex.
 */
export function softenColor(hex: string, alpha = 0.12): string {
  let h = String(hex).trim().replace(/^#/, '')
  if (h.length === 3)
    h = h
      .split('')
      .map((c) => c + c)
      .join('')
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return hex
  const n = parseInt(h, 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function kebab(key: string): string {
  return key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)
}

/** CSS variable name for a token, e.g. 'headerBg' → '--chat-header-bg'. */
export function cssVarName(key: ChatColorKey): string {
  return `--chat-${kebab(key)}`
}

/** Map a theme to the `--chat-*` CSS variables the preview consumes. */
export function themeToCssVars(theme: ChatTheme): Record<string, string> {
  const vars: Record<string, string> = {}
  for (const key of THEME_COLOR_KEYS) vars[cssVarName(key)] = theme[key]
  return vars
}
