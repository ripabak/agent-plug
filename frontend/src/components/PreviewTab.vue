<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAgentsStore } from '@/stores/agents'
import { useChatStore } from '@/stores/chat'
import { API_BASE } from '@/api/client'
import {
  THEME_PRESETS,
  softenColor,
  themeToCssVars,
  type ChatColorKey,
  type ChatTheme,
} from '@/utils/themes'
import ColorPreview from '@/components/ColorPreview.vue'

/** Bridge exposed by backend/app/widget/widget.js after it initializes. */
interface PreviewWidgetBridge {
  setTheme?: (theme: ChatTheme) => void
  setOpts?: (showThinking: boolean, showTools: boolean) => void
  destroy?: () => void
}

declare global {
  interface Window {
    __apwWidgets?: Record<string, PreviewWidgetBridge>
  }
}

/** One color control; `keys` sets extra tokens to the same value (merged
 *  chip border+text), `softKey` derives a soft background from the value. */
interface ColorControl {
  key: ChatColorKey
  label: string
  keys?: ChatColorKey[]
  softKey?: ChatColorKey
}

/**
 * Color controls grouped by component. Each group shows a realistic mockup of
 * the component (ColorPreview) plus the color pickers for its tokens — the
 * mockup uses the SAME tokens as the real chat component. The tools bubble
 * follows the AI bubble colors; only the chip itself has its own controls.
 */
interface ColorGroup {
  title: string
  preview: string
  controls: ColorControl[]
}

const COLOR_GROUPS: ColorGroup[] = [
  {
    title: 'Header',
    preview: 'header',
    controls: [
      { key: 'headerBg', label: 'Header color' },
      { key: 'headerText', label: 'Text color' },
    ],
  },
  {
    title: 'Chat background',
    preview: 'chat',
    controls: [{ key: 'msgsBg', label: 'Background' }],
  },
  {
    title: 'AI bubble',
    preview: 'aiBubble',
    controls: [
      { key: 'aiBubbleBg', label: 'Bubble color' },
      { key: 'aiBubbleBorder', label: 'Bubble border' },
      { key: 'aiBubbleText', label: 'Text color' },
    ],
  },
  {
    title: 'User bubble',
    preview: 'userBubble',
    controls: [
      { key: 'userBubbleBg', label: 'Bubble color' },
      { key: 'userBubbleText', label: 'Text color' },
    ],
  },
  {
    title: 'Thinking',
    preview: 'thinking',
    controls: [
      { key: 'thinkingBg', label: 'Bubble color' },
      { key: 'thinkingBorder', label: 'Bubble border' },
      { key: 'thinkingText', label: 'Text color' },
    ],
  },
  {
    title: 'Tools',
    preview: 'tools',
    controls: [
      // Chip border + text are merged into one color; the background is
      // derived automatically (soft version of the same color).
      {
        key: 'toolSuccessBorder',
        label: 'Chip',
        keys: ['toolSuccessText'],
        softKey: 'toolSuccessBg',
      },
      {
        key: 'toolErrorBorder',
        label: 'Chip error',
        keys: ['toolErrorText'],
        softKey: 'toolErrorBg',
      },
    ],
  },
  {
    title: 'Input & send',
    preview: 'toolbar',
    controls: [
      { key: 'toolbarBg', label: 'Toolbar' },
      { key: 'toolbarBorder', label: 'Toolbar border' },
      { key: 'inputBg', label: 'Input background' },
      { key: 'inputBorder', label: 'Input border' },
      { key: 'inputText', label: 'Input text' },
      { key: 'btnBg', label: 'Send button' },
      { key: 'btnText', label: 'Send button text' },
    ],
  },
]

const agentsStore = useAgentsStore()
const chat = useChatStore()

const agent = computed(() => agentsStore.current)
const widgetHost = ref<HTMLDivElement | null>(null)

/**
 * Effective theme: the store's preset + overrides, with one legacy special
 * case — until the user picks a theme/tweaks a color, the header follows the
 * agent's theme_color (the pre-theming preview behavior).
 */
const effectiveTheme = computed<ChatTheme>(() => {
  const t = chat.themeColors
  if (chat.themeCustomized) return t
  const accent = agent.value?.theme_color || t.accent
  return { ...t, headerBg: accent }
})

/** CSS variables applied to the config panel card (accent-color, opt colors). */
const chatVars = computed(() => themeToCssVars(effectiveTheme.value))

function widgetBridge(): PreviewWidgetBridge | undefined {
  return agent.value ? window.__apwWidgets?.[String(agent.value.id)] : undefined
}

/**
 * Reuse the real embeddable widget (backend/app/widget/widget.js) as the
 * floating chat preview — the exact same launcher + panel as the live embed.
 * The current theme is passed via data-theme so the first paint matches the
 * panel; later changes are pushed live through the widget bridge.
 */
function mountWidget() {
  const a = agent.value
  if (!a || !widgetHost.value) return
  widgetBridge()?.destroy?.()
  widgetHost.value.innerHTML = ''
  const s = document.createElement('script')
  s.src = `${API_BASE}/api/public/widget.js`
  s.setAttribute('data-agent-id', String(a.id))
  s.setAttribute('data-token', a.public_token)
  s.setAttribute('data-base-url', API_BASE)
  s.setAttribute('data-auto-open', 'desktop')
  s.setAttribute('data-theme', JSON.stringify(effectiveTheme.value))
  widgetHost.value.appendChild(s)
}

// Display config (theme + show thinking/tools) is initialized from the agent —
// the preview is the ONLY place it can be adjusted; the chat has no ⚙ menu.
watch(
  () => agent.value?.id,
  () => {
    if (!agent.value) return
    chat.initFromAgent(agent.value)
    // On the first run the host is not mounted yet — onMounted covers it.
    if (widgetHost.value) mountWidget()
  },
  { immediate: true },
)

onMounted(() => {
  if (agent.value && widgetHost.value) mountWidget()
})

// Push theme/display changes into the running widget live (no re-mount).
watch(effectiveTheme, (t) => widgetBridge()?.setTheme?.(t))
watch(
  () => [chat.settings.showThinking, chat.settings.showTools] as const,
  ([showThinking, showTools]) => widgetBridge()?.setOpts?.(showThinking, showTools),
)

// Flush any pending debounced theme/toggle save + tear down the widget.
onBeforeUnmount(() => {
  chat.flushPersist()
  widgetBridge()?.destroy?.()
})

/** Apply a color control: set the main token + merged tokens + derived soft bg. */
function onColorInput(e: Event, c: ColorControl) {
  const v = (e.target as HTMLInputElement).value
  const values: Partial<Record<ChatColorKey, string>> = { [c.key]: v }
  for (const k of c.keys ?? []) values[k] = v
  if (c.softKey) values[c.softKey] = softenColor(v)
  chat.setThemeColors(values)
}
</script>

<template>
  <div>
    <!-- Theme + display configuration — mirrors the widget's data-theme-* support -->
    <div class="card chat-config" :style="chatVars">
      <div class="chat-config-section">
        <div class="chat-config-title">Display</div>
        <div class="chat-config-toggles">
          <label class="chat-opt">
            <input
              type="checkbox"
              :checked="chat.settings.showThinking"
              @change="chat.setSetting('showThinking', ($event.target as HTMLInputElement).checked)"
            />
            Show thinking
          </label>
          <label class="chat-opt">
            <input
              type="checkbox"
              :checked="chat.settings.showTools"
              @change="chat.setSetting('showTools', ($event.target as HTMLInputElement).checked)"
            />
            Show tools
          </label>
        </div>
      </div>

      <div class="chat-config-section">
        <div class="chat-config-title">Theme presets</div>
        <div class="theme-presets">
          <button
            v-for="p in THEME_PRESETS"
            :key="p.name"
            type="button"
            class="theme-chip"
            :class="{ active: chat.themePresetName === p.name }"
            @click="chat.setThemePreset(p.name)"
          >
            <span class="theme-swatches">
              <span class="theme-swatch" :style="{ background: p.headerBg }" />
              <span class="theme-swatch" :style="{ background: p.msgsBg }" />
              <span class="theme-swatch" :style="{ background: p.aiBubbleBg }" />
              <span class="theme-swatch" :style="{ background: p.userBubbleBg }" />
            </span>
            {{ p.label }}
          </button>
        </div>
      </div>

      <div class="chat-config-section">
        <div class="chat-config-title">Colors</div>
        <div class="chat-color-groups">
          <div v-for="g in COLOR_GROUPS" :key="g.title" class="chat-color-group">
            <div class="chat-color-group-mock">
              <ColorPreview :kind="g.preview" :theme="effectiveTheme" />
            </div>
            <div class="chat-color-group-controls">
              <label v-for="c in g.controls" :key="c.key" class="chat-color-control">
                <span class="chat-color-label">{{ c.label }}</span>
                <input
                  type="color"
                  :value="effectiveTheme[c.key]"
                  @input="onColorInput($event, c)"
                />
              </label>
            </div>
          </div>
        </div>
        <button
          v-if="chat.themeCustomized"
          type="button"
          class="btn btn-ghost btn-sm chat-config-reset"
          @click="chat.resetTheme()"
        >
          Reset theme
        </button>
      </div>
    </div>

    <!-- Floating chat preview: reuses the real embeddable widget — the same
         launcher + panel as the live embed. Auto-opens on desktop; on mobile
         the launcher button (bottom-right) opens it. -->
    <p class="preview-widget-hint">
      Chat preview = live widget (floating). Auto-opens on desktop; on mobile, tap the launcher at
      the bottom-right.
    </p>
    <div ref="widgetHost" class="preview-widget-host" />
  </div>
</template>
