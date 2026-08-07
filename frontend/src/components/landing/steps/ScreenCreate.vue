<script setup lang="ts">
/** Step 1 screen — mirrors the real "create agent" form (AgentCreateView). */
</script>

<template>
  <div class="lp-win" aria-hidden="true">
    <div class="lp-win-bar">
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-title">New agent</span>
      <span class="lp-win-spacer" />
    </div>
    <div class="lp-win-body">
      <div class="lp-field">
        <span class="lp-field-label">Agent name</span>
        <span class="lp-input">Senja Coffee</span>
      </div>
      <div class="lp-field">
        <span class="lp-field-label">Description</span>
        <span class="lp-input">Answers questions about our menu, opening hours, and location.</span>
      </div>
      <div class="lp-field">
        <span class="lp-field-label">Welcome message</span>
        <span class="lp-input">Hi! Ask me anything about the café.</span>
      </div>
      <div class="lp-field" style="margin-bottom: 20px">
        <span class="lp-field-label">Avatar</span>
        <span class="lp-av-row">
          <span class="lp-av active">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="5.2" stroke="currentColor" stroke-width="1.5" />
            </svg>
          </span>
          <span class="lp-av">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect
                x="3.5"
                y="3.5"
                width="9"
                height="9"
                rx="1.5"
                stroke="currentColor"
                stroke-width="1.5"
              />
            </svg>
          </span>
          <span class="lp-av">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M8 3 13.5 13h-11L8 3Z"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linejoin="round"
              />
            </svg>
          </span>
          <span class="lp-av">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="m8 2 1.7 3.9L13.7 6 10.6 8.7l1.1 4.1L8 10.4l-3.7 2.4 1.1-4.1L2.3 6l4-.1L8 2Z"
                stroke="currentColor"
                stroke-width="1.4"
                stroke-linejoin="round"
              />
            </svg>
          </span>
        </span>
      </div>
      <span class="lp-btn lp-btn-ink" style="width: 100%">Create agent</span>
    </div>
  </div>
</template>
