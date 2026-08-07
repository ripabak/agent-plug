<script setup lang="ts">
/** Step 2 screen — mirrors the real knowledge tab (KnowledgeTab): three
 *  input modes (web pages / PDF / notes) plus ready source rows. */
</script>

<template>
  <div class="lp-win" aria-hidden="true">
    <div class="lp-win-bar">
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-title">Knowledge</span>
      <span class="lp-win-spacer" />
    </div>
    <div class="lp-win-body">
      <div class="lp-modes">
        <span class="lp-mode active">URL</span>
        <span class="lp-mode">PDF</span>
        <span class="lp-mode">Text</span>
      </div>
      <div class="lp-field" style="margin-bottom: 0">
        <span class="lp-field-label">Add a page from your website</span>
        <span class="lp-input mono">senja.coffee/menu</span>
      </div>

      <div class="lp-src-list">
        <div class="lp-src-row">
          <span class="lp-src-icon">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4" />
              <path
                d="M2.5 8h11M8 2c2 1.6 3 3.6 3 6s-1 4.4-3 6c-2-1.6-3-3.6-3-6s1-4.4 3-6Z"
                stroke="currentColor"
                stroke-width="1.4"
              />
            </svg>
          </span>
          <span class="lp-src-name">senja.coffee/menu</span>
          <span class="lp-chip lp-chip-good">
            <svg width="9" height="9" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path
                d="M2 6.2 4.8 9 10 3.4"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            Ready
          </span>
        </div>
        <div class="lp-src-row">
          <span class="lp-src-icon">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4" />
              <path
                d="M2.5 8h11M8 2c2 1.6 3 3.6 3 6s-1 4.4-3 6c-2-1.6-3-3.6-3-6s1-4.4 3-6Z"
                stroke="currentColor"
                stroke-width="1.4"
              />
            </svg>
          </span>
          <span class="lp-src-name">senja.coffee/opening-hours</span>
          <span class="lp-chip lp-chip-good">
            <svg width="9" height="9" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path
                d="M2 6.2 4.8 9 10 3.4"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            Ready
          </span>
        </div>
        <div class="lp-src-row">
          <span class="lp-src-icon">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M3 2.5h6l4 4v7H3v-11Z"
                stroke="currentColor"
                stroke-width="1.4"
                stroke-linejoin="round"
              />
              <path
                d="M9 2.5v4h4M5 8.5h6M5 11h4"
                stroke="currentColor"
                stroke-width="1.4"
                stroke-linecap="round"
              />
            </svg>
          </span>
          <span class="lp-src-name">our-story.pdf</span>
          <span class="lp-chip lp-chip-good">
            <svg width="9" height="9" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path
                d="M2 6.2 4.8 9 10 3.4"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            Ready
          </span>
        </div>
        <div class="lp-src-row" style="border-bottom: none">
          <span class="lp-src-icon">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M8 3v10M3 8h10"
                stroke="currentColor"
                stroke-width="1.4"
                stroke-linecap="round"
              />
            </svg>
          </span>
          <span class="lp-src-name" style="color: var(--lp-muted)">Add another page</span>
          <span class="lp-chip lp-chip-muted">Pages / files / notes</span>
        </div>
      </div>
    </div>
    <div class="lp-win-foot">
      <span class="lp-mono-meta" style="color: var(--lp-muted)">3 pages · ready to answer</span>
    </div>
  </div>
</template>
