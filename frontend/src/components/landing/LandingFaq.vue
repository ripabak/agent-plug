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
    a: 'Only what you teach it: your website pages, documents, or notes. It answers from those, and shows the page it used.',
  },
  {
    q: 'Do I need to know how to code?',
    a: 'No. One line of code, as easy as pasting a video into your site. Everything else is done with clicks.',
  },
  {
    q: 'Does this replace my customer service team?',
    a: 'No. It answers the everyday questions so visitors stay on your page and get unstuck. Anything complex or personal still goes to your team, exactly as before.',
  },
  {
    q: 'Can it match my brand?',
    a: 'Yes: name, greeting, avatar, colors, and how much detail it shows. A live preview lets you check everything before you publish.',
  },
  {
    q: 'Where do visitor conversations go?',
    a: 'Chats on your website are private per visitor and cleared when the page reloads. Conversations you start from your dashboard are kept for you.',
  },
  {
    q: 'Is my information safe?',
    a: 'Your materials stay in your own database. Each agent works only with what you gave it, and nothing is shared with other users.',
  },
  {
    q: 'How long does setup take?',
    a: 'About two minutes: create, teach, install. No credit card to start.',
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
