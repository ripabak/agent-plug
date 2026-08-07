<script setup lang="ts">
/**
 * FAQ — plain-language answers grounded in how the product actually works
 * (see frontend/AGENTS.md, backend/app/widget/widget.js, services/embed.py).
 * Accordion: border-bottom separators only, sharp + / rotated to x, per the
 * minimalist-ui protocol.
 */
import { ref } from 'vue'

interface FaqItem {
  q: string
  a: string
}

const items: FaqItem[] = [
  {
    q: 'What does my agent know?',
    a: 'Only what you give it. Feed it URLs, PDFs, or pasted text, and it keeps its own indexed memory. Every answer comes back with the source it was drawn from.',
  },
  {
    q: 'Do I need to write code?',
    a: 'One line. The embed snippet is a single script tag. Everything else, from the welcome message to the theme, is configured in the dashboard.',
  },
  {
    q: 'Where do visitor conversations go?',
    a: 'Widget chats are per visitor and ephemeral on page reload, so a site never accumulates private history. Conversations started from your dashboard are stored and stay yours.',
  },
  {
    q: 'Can it match my brand?',
    a: 'Yes. Name, avatar, welcome message, six color presets, custom colors, and toggles to show or hide the agent\u2019s reasoning and tool calls.',
  },
  {
    q: 'How does it answer?',
    a: 'It retrieves from your indexed knowledge, then a reasoning agent built on LangChain and OpenRouter models writes the answer and cites its sources.',
  },
  {
    q: 'Is my data private?',
    a: 'Your knowledge lives in your own PostgreSQL database and object storage. Each agent\u2019s vectors sit in a separate collection, and the widget talks to the backend through a per-agent public token.',
  },
  {
    q: 'How fast is setup?',
    a: 'About two minutes: create the agent, add knowledge, copy the snippet. No credit card, no dev team, nothing to install.',
  },
]

const open = ref(0)

function toggle(i: number) {
  open.value = open.value === i ? -1 : i
}
</script>

<template>
  <div class="lp-faq-list">
    <div v-for="(item, i) in items" :key="item.q" class="lp-faq-item">
      <button
        class="lp-faq-q"
        type="button"
        :aria-expanded="open === i"
        :aria-controls="`lp-faq-panel-${i}`"
        @click="toggle(i)"
      >
        {{ item.q }}
        <span class="lp-faq-icon" :class="{ open: open === i }">
          <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path
              d="M6 1v10M1 6h10"
              stroke="currentColor"
              stroke-width="1.4"
              stroke-linecap="round"
            />
          </svg>
        </span>
      </button>
      <div
        class="lp-faq-panel"
        :class="{ open: open === i }"
        :id="`lp-faq-panel-${i}`"
        role="region"
      >
        <div class="lp-faq-panel-inner">
          <p class="lp-faq-a">{{ item.a }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
