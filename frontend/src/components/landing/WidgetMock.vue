<script setup lang="ts">
/**
 * WidgetMock — a faithful HTML/CSS preview of the real embeddable widget
 * (backend/app/widget/widget.js): same anatomy (header with avatar + name,
 * message list, thinking block, tool chips, sources, toolbar), rendered in
 * the landing's warm monochrome palette. Plays a scripted conversation when
 * it scrolls into view; honours prefers-reduced-motion by rendering the full
 * conversation instantly.
 *
 * This is a decorative component preview, not a second chat implementation:
 * it mirrors the real product so the landing story stays truthful.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import PlugMark from './PlugMark.vue'

interface Planned {
  kind: 'user' | 'bot' | 'thinking' | 'tools' | 'sources'
  text?: string
  full?: string
  delay: number
}

const BRIEF: Planned[] = [
  { kind: 'user', text: 'Do you ship to Indonesia?', delay: 500 },
  { kind: 'thinking', text: 'looking up shipping policy', delay: 420 },
  { kind: 'tools', text: 'search_knowledge_base', delay: 380 },
  {
    kind: 'bot',
    full: 'Yes. We ship worldwide. Orders over $75 ship free; standard delivery to Indonesia takes 7 to 10 business days.',
    delay: 300,
  },
]

const FULL: Planned[] = [
  { kind: 'user', text: 'Do you ship to Indonesia?', delay: 400 },
  { kind: 'thinking', text: 'checking shipping policy and FAQ', delay: 400 },
  { kind: 'tools', text: 'search_knowledge_base', delay: 340 },
  {
    kind: 'bot',
    full: 'Yes, we ship worldwide. Orders over $75 ship free; standard delivery to Indonesia takes 7 to 10 business days.',
    delay: 300,
  },
  { kind: 'sources', text: 'shipping-policy / faq', delay: 260 },
  { kind: 'user', text: 'Can I return a used item?', delay: 700 },
  { kind: 'thinking', text: 'checking returns policy', delay: 360 },
  {
    kind: 'bot',
    full: 'Returns are accepted within 30 days of delivery. Items must be unused and in original packaging; we email you a prepaid label.',
    delay: 300,
  },
]

interface Msg {
  kind: Planned['kind']
  text: string
  typing?: boolean
}

const props = withDefaults(defineProps<{ mode?: 'brief' | 'full' }>(), {
  mode: 'brief',
})

const plan = props.mode === 'full' ? FULL : BRIEF

const msgs = ref<Msg[]>([])
const typingId = ref(-1)
const rootEl = ref<HTMLElement | null>(null)

let alive = true
let played = false
let observer: IntersectionObserver | null = null

const TYPE_MS = 13
const TYPE_CHUNK = 2 // chars per tick (keeps short bot messages quick)

function prefersReducedMotion(): boolean {
  try {
    return (
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    )
  } catch {
    return false
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

function renderInstant() {
  for (const step of plan) {
    msgs.value.push({
      kind: step.kind,
      text: step.kind === 'bot' && step.full ? step.full : (step.text ?? ''),
    })
  }
}

async function play() {
  for (const step of plan) {
    if (!alive) return
    await sleep(step.delay)
    if (!alive) return

    if (step.kind === 'bot' && step.full) {
      // typewriter effect
      const idx = msgs.value.length
      const msg: Msg = { kind: 'bot', text: '', typing: true }
      msgs.value.push(msg)
      typingId.value = idx
      let chars = 0
      while (chars < step.full.length) {
        if (!alive) return
        await sleep(TYPE_MS)
        chars = Math.min(chars + TYPE_CHUNK, step.full.length)
        msg.text = step.full.slice(0, chars)
      }
      msg.typing = false
      typingId.value = -1
    } else {
      msgs.value.push({ kind: step.kind, text: step.text ?? '' })
    }
  }
}

function start() {
  if (played) return
  played = true
  if (prefersReducedMotion()) {
    renderInstant()
    return
  }
  void play()
}

onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') {
    start()
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        start()
        observer?.disconnect()
      }
    },
    { threshold: 0.35 },
  )
  if (rootEl.value) observer.observe(rootEl.value)
})

onBeforeUnmount(() => {
  alive = false
  observer?.disconnect()
})
</script>

<template>
  <div ref="rootEl" class="lp-widget" aria-hidden="true">
    <div class="lp-widget-head">
      <span class="lp-widget-avatar"><PlugMark :size="17" /></span>
      <span class="lp-widget-titles">
        <span class="lp-widget-name">Meridian Supply Co.</span>
        <span class="lp-widget-sub">Shipping, returns, and product help</span>
      </span>
      <span class="lp-widget-close">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path
            d="M2 2l8 8M10 2l-8 8"
            stroke="currentColor"
            stroke-width="1.4"
            stroke-linecap="round"
          />
        </svg>
      </span>
    </div>

    <div class="lp-widget-msgs">
      <template v-for="(m, i) in msgs" :key="i">
        <div v-if="m.kind === 'user'" class="lp-wm-bubble user">{{ m.text }}</div>

        <div v-else-if="m.kind === 'bot'" class="lp-wm-bubble bot">
          {{ m.text }}<span v-if="i === typingId" class="lp-wm-caret" />
        </div>

        <div v-else-if="m.kind === 'thinking'" class="lp-wm-think">
          <div class="lp-wm-think-label">Reasoning</div>
          <div class="lp-wm-think-text">{{ m.text }}</div>
        </div>

        <div v-else-if="m.kind === 'tools'" class="lp-wm-tools">
          <span class="lp-wm-tool">
            <svg width="9" height="9" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path
                d="M2 6.2 4.8 9 10 3.4"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            {{ m.text }}
          </span>
        </div>

        <div v-else class="lp-wm-sources">
          <div class="lp-wm-sources-label">Sources</div>
          <a class="lp-wm-source" href="#" @click.prevent>[1] shipping-policy</a>
          <a class="lp-wm-source" href="#" @click.prevent>[2] faq</a>
        </div>
      </template>
    </div>

    <div class="lp-widget-toolbar">
      <span class="lp-widget-input">Type your message…</span>
      <span class="lp-widget-send">Send</span>
    </div>
  </div>
</template>
