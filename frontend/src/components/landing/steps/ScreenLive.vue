<script setup lang="ts">
/** Step 5 screen — the result: the widget live on a real-looking page.
 *  A browser frame with skeleton content, the launcher button, and the
 *  full widget conversation embedded bottom-right (exactly where the real
 *  embed snippet renders it). */
import WidgetMock from '../WidgetMock.vue'
</script>

<template>
  <div class="lp-browser" aria-hidden="true">
    <div class="lp-browser-bar">
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M8 2.5v3M5 4h6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
      </svg>
      <span class="lp-urlbar">senja.coffee</span>
      <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.4" />
        <path d="M8 2.5v11M2.5 8h11" stroke="currentColor" stroke-width="1.2" />
      </svg>
    </div>
    <div class="lp-browser-body">
      <div class="lp-browser-skel block" />
      <div class="lp-browser-skel" />
      <div class="lp-browser-skel short" />
      <div class="lp-browser-skel" />
      <div class="lp-browser-skel tiny" />
      <div class="lp-browser-skel" />
      <div class="lp-browser-skel short" />

      <span class="lp-browser-launcher">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 4.5h16a1.8 1.8 0 0 1 1.8 1.8v9.4a1.8 1.8 0 0 1-1.8 1.8h-9.4l-2.6 3.2v-3.2H4a1.8 1.8 0 0 1-1.8-1.8V6.3A1.8 1.8 0 0 1 4 4.5Z"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linejoin="round"
          />
          <rect x="8.6" y="8.8" width="2.2" height="5.6" rx="1.1" fill="currentColor" />
          <rect x="13.2" y="8.8" width="2.2" height="5.6" rx="1.1" fill="currentColor" />
        </svg>
      </span>

      <WidgetMock class="lp-browser-embed" mode="full" />
    </div>
  </div>
</template>
