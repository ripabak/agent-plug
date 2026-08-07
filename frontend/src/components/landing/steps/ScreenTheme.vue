<script setup lang="ts">
/** Step 3 screen — mirrors the real preview panel (PreviewTab): theme
 *  presets (the real six), the Show thinking / Show tools toggles, and a
 *  mini live chat preview. "Monochrome" is preselected to match the brand. */
const presets = [
  { name: 'Monochrome', swatches: ['#211f1b', '#a9502a'], active: true },
  { name: 'Indigo', swatches: ['#4f46e5', '#4f46e5'] },
  { name: 'Emerald', swatches: ['#059669', '#059669'] },
  { name: 'Rose', swatches: ['#e11d48', '#e11d48'] },
  { name: 'Amber', swatches: ['#d97706', '#d97706'] },
  { name: 'Slate', swatches: ['#0f172a', '#0ea5e9'] },
  { name: 'Ocean', swatches: ['#0d9488', '#0d9488'] },
]
</script>

<template>
  <div class="lp-win" aria-hidden="true">
    <div class="lp-win-bar">
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-title">Preview</span>
      <span class="lp-win-spacer" />
    </div>
    <div class="lp-win-body">
      <div class="lp-theme-list">
        <div v-for="p in presets" :key="p.name" class="lp-theme-row" :class="{ active: p.active }">
          <span class="lp-theme-swatch" :style="{ background: p.swatches[0] }" />
          <span class="lp-theme-name">{{ p.name }}</span>
          <span v-if="p.active" class="lp-theme-check">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path
                d="M2 6.2 4.8 9 10 3.4"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </span>
        </div>
      </div>

      <div class="lp-toggle-row">
        <span class="lp-toggle-label">Show thinking</span>
        <span class="lp-toggle" />
      </div>
      <div class="lp-toggle-row" style="border-bottom: none">
        <span class="lp-toggle-label">Show tool calls</span>
        <span class="lp-toggle" />
      </div>

      <div class="lp-minichat">
        <div class="lp-minichat-head">
          <span class="lp-minichat-avatar">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
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
          <span class="lp-minichat-title">Senja Coffee</span>
        </div>
        <div class="lp-minichat-body">
          <span class="lp-mini-bubble bot">Hi! Ask me anything about the café.</span>
          <span class="lp-mini-bubble user">What time do you close?</span>
          <span class="lp-mini-bubble bot">We close at 10pm on weekdays and 11pm on weekends.</span>
        </div>
      </div>
    </div>
  </div>
</template>
