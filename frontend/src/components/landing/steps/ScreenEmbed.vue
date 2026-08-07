<script setup lang="ts">
/**
 * Step 4 screen — the embed snippet (same shape as the real
 * build_embed_snippet output), with example values.
 *
 * The snippet is a static, hand-authored, pre-escaped string rendered with
 * v-html (never touches external data), so Prettier/Vue whitespace handling
 * cannot collapse the line breaks.
 */
const snippet =
  '<span class="tag">&lt;script</span> <span class="attr">src</span>=<span class="str">"https://api.agent-plug.app/api/public/widget.js"</span>\n' +
  '  <span class="attr">data-agent-id</span>=<span class="str">"42"</span>\n' +
  '  <span class="attr">data-token</span>=<span class="str">"pub_9f2c4a…"</span>\n' +
  '  <span class="attr">data-base-url</span>=<span class="str">"https://api.agent-plug.app"</span><span class="tag">&gt;&lt;/script&gt;</span>'
</script>

<template>
  <div class="lp-win" aria-hidden="true">
    <div class="lp-win-bar">
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-title">Embed</span>
      <span class="lp-win-spacer" />
    </div>
    <div class="lp-win-body">
      <div class="lp-code">
        <span class="lp-code-chip">
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <rect
              x="4"
              y="4"
              width="7"
              height="7"
              rx="1"
              stroke="currentColor"
              stroke-width="1.2"
            />
            <path d="M8.5 4V3a2.5 2.5 0 0 0-5 0v1" stroke="currentColor" stroke-width="1.2" />
          </svg>
          Copy
        </span>
        <span v-html="snippet" />
      </div>
      <div class="lp-code-caption">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M3 2.5h6l4 4v7H3v-11Z"
            stroke="currentColor"
            stroke-width="1.3"
            stroke-linejoin="round"
          />
          <path d="M9 2.5v4h4" stroke="currentColor" stroke-width="1.3" />
        </svg>
        Paste this into your website, anywhere on the page
      </div>
    </div>
    <div class="lp-win-foot">
      <span class="lp-mono-meta" style="color: var(--lp-muted)"
        >Floating button · works on any website</span
      >
      <span class="lp-chip lp-chip-accent">Live in seconds</span>
    </div>
  </div>
</template>
