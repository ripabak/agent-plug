/**
 * Chat display-config store: theme (preset + custom colors) and the
 * Show thinking / Show tools toggles for the chat widget.
 *
 * The preview embeds the REAL widget (backend/app/widget/widget.js) for the
 * conversation itself, so there is no SSE/message state here — this store only
 * holds the display config that is set from the preview panel and persisted to
 * the Agent (the live widget reads it via the public /config endpoint).
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import type { Agent } from '@/api/types'
import { findPreset, THEME_PRESETS, type ChatColorKey, type ChatTheme } from '@/utils/themes'
import { useAgentsStore } from './agents'

const SETTINGS_KEY = 'ap_chat_settings'
const THEME_KEY = 'ap_chat_theme'

interface ChatSettings {
  showThinking: boolean
  showTools: boolean
}

/**
 * Persisted theme selection: a base preset + per-token overrides.
 * `touched` is false until the user explicitly picks a preset or tweaks a
 * color — until then the preview keeps the legacy behavior of following the
 * agent's theme_color for the header.
 */
export interface ChatThemeState {
  preset: string
  custom: Partial<ChatTheme>
  touched: boolean
}

function loadThemeState(): ChatThemeState {
  const fallback: ChatThemeState = { preset: THEME_PRESETS[0]!.name, custom: {}, touched: false }
  try {
    const raw = localStorage.getItem(THEME_KEY)
    if (raw) return { ...fallback, ...(JSON.parse(raw) as Partial<ChatThemeState>) }
  } catch {
    /* ignore */
  }
  return fallback
}

function loadSettings(): ChatSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (raw) return { showThinking: true, showTools: true, ...JSON.parse(raw) }
  } catch {
    /* ignore */
  }
  return { showThinking: true, showTools: true }
}

export const useChatStore = defineStore('chat', () => {
  const settings = ref<ChatSettings>(loadSettings())

  // ---- theme (preset + custom colors), persisted so the preview survives refresh
  const themeState = ref<ChatThemeState>(loadThemeState())

  /**
   * Server persistence (debounced): the display config lives on the Agent so
   * the LIVE widget picks it up via the public /config endpoint. Preview is
   * the only place it can be adjusted — the chat itself has no controls.
   */
  let saveTimer: ReturnType<typeof setTimeout> | null = null

  async function persistDisplayConfig() {
    const agents = useAgentsStore()
    if (!agents.current) return
    try {
      await agents.update({
        chat_theme: JSON.stringify(themeState.value),
        show_thinking: settings.value.showThinking,
        show_tools: settings.value.showTools,
      })
    } catch {
      // Display config is best-effort — the preview keeps working offline.
    }
  }

  function schedulePersist() {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => void persistDisplayConfig(), 400)
  }

  /** Flush any pending debounced save immediately (e.g. on tab unmount). */
  function flushPersist() {
    if (!saveTimer) return
    clearTimeout(saveTimer)
    saveTimer = null
    void persistDisplayConfig()
  }

  /**
   * Initialize display config from the agent (server truth) when the preview
   * switches agents. Falls back to the localStorage mirror for themes saved
   * before the config was stored on the agent (smooth migration).
   */
  function initFromAgent(agent: Agent) {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    settings.value = {
      showThinking: agent.show_thinking ?? loadSettings().showThinking,
      showTools: agent.show_tools ?? loadSettings().showTools,
    }
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings.value))
    let next = loadThemeState()
    if (agent.chat_theme) {
      try {
        const parsed = JSON.parse(agent.chat_theme) as Partial<ChatThemeState>
        if (parsed && typeof parsed === 'object') {
          next = {
            preset: parsed.preset ?? THEME_PRESETS[0]!.name,
            custom: parsed.custom ?? {},
            touched: parsed.touched ?? false,
          }
        }
      } catch {
        // ignore malformed agent theme
      }
    }
    themeState.value = next
    saveThemeState()
  }

  /** Base preset + custom overrides merged into a concrete theme. */
  const themeColors = computed<ChatTheme>(() => {
    const preset = findPreset(themeState.value.preset) ?? THEME_PRESETS[0]!
    return { ...preset, ...themeState.value.custom }
  })
  const themePresetName = computed(() => themeState.value.preset)
  const themeCustomized = computed(() => themeState.value.touched)

  function saveThemeState() {
    localStorage.setItem(THEME_KEY, JSON.stringify(themeState.value))
  }

  /** Apply a full preset — replaces any custom color overrides. */
  function setThemePreset(name: string) {
    themeState.value = { preset: name, custom: {}, touched: true }
    saveThemeState()
    schedulePersist()
  }

  /** Override a single color token on top of the current preset. */
  function setThemeColor(key: ChatColorKey, value: string) {
    setThemeColors({ [key]: value })
  }

  /**
   * Override several tokens at once (e.g. merged chip border+text, plus a
   * derived soft background) — one state write, one debounced persist.
   */
  function setThemeColors(values: Partial<Record<ChatColorKey, string>>) {
    themeState.value = { ...themeState.value, touched: true }
    for (const [key, value] of Object.entries(values)) {
      if (value !== undefined) themeState.value.custom[key as ChatColorKey] = value
    }
    saveThemeState()
    schedulePersist()
  }

  /** Back to the default theme, untouched (header follows agent theme_color again). */
  function resetTheme() {
    themeState.value = { preset: THEME_PRESETS[0]!.name, custom: {}, touched: false }
    saveThemeState()
    schedulePersist()
  }

  function setSetting(key: keyof ChatSettings, value: boolean) {
    settings.value[key] = value
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings.value))
    schedulePersist()
  }

  return {
    settings,
    setSetting,
    initFromAgent,
    flushPersist,
    themeColors,
    themePresetName,
    themeCustomized,
    setThemePreset,
    setThemeColor,
    setThemeColors,
    resetTheme,
  }
})
