<script setup lang="ts">
/**
 * PlugMark — the Agent-Plug brand mark.
 *
 * Concept (brandkit): "plug an agent into your website". A chat bubble whose
 * body carries two socket slots: the place where the agent plugs in. Drawn
 * as a single geometric stroke mark so it works as a nav logo, widget
 * avatar, favicon, and footer mark at any size, light or dark.
 */
withDefaults(
  defineProps<{
    /** size in px (square) */
    size?: number
    /** aria-hidden for purely decorative uses */
    decorative?: boolean
  }>(),
  { size: 24, decorative: true },
)
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    :aria-hidden="decorative || undefined"
    :role="decorative ? undefined : 'img'"
  >
    <!-- chat bubble outline -->
    <path
      d="M4 4.5h16a1.8 1.8 0 0 1 1.8 1.8v9.4a1.8 1.8 0 0 1-1.8 1.8h-9.4l-2.6 3.2v-3.2H4a1.8 1.8 0 0 1-1.8-1.8V6.3A1.8 1.8 0 0 1 4 4.5Z"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linejoin="round"
    />
    <!-- socket slots -->
    <rect x="8.6" y="8.8" width="2.2" height="5.6" rx="1.1" fill="currentColor" />
    <rect x="13.2" y="8.8" width="2.2" height="5.6" rx="1.1" fill="currentColor" />
  </svg>
</template>
