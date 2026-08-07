<script setup lang="ts">
/**
 * Realistic mockup of ONE chat component for the config panel. Each kind
 * renders the component at near-real size using the SAME theme tokens the
 * real chat uses, so the color picker always references the right part:
 *   header     → header bar (bg headerBg, content headerText)
 *   chat       → message area (msgsBg) with AI + user bubbles
 *   aiBubble   → AI bubble (aiBubbleBg/aiBubbleBorder/aiBubbleText)
 *   userBubble → user bubble (userBubbleBg/userBubbleText)
 *   thinking   → thinking bubble (thinkingBg/thinkingBorder/thinkingText)
 *   tools      → tools chip bubble (toolsBg/toolsBorder/toolsText)
 *   btn        → send button (btnBg/btnText)
 *   input      → input field (inputBg/inputBorder/inputText)
 *   toolbar    → toolbar strip (toolbarBg/toolbarBorder) with input + send
 *   accent     → accent swatch (accent)
 */
import type { ChatTheme } from '@/utils/themes'

defineProps<{ kind: string; theme: ChatTheme }>()
</script>

<template>
  <span class="cvp" :data-kind="kind">
    <!-- Header -->
    <template v-if="kind === 'header'">
      <span class="cvp-header" :style="{ background: theme.headerBg, color: theme.headerText }">
        <span class="cvp-avatar">🤖</span>
        <span class="cvp-header-text">
          <span class="cvp-name" :style="{ background: theme.headerText }" />
          <span class="cvp-sub" :style="{ background: theme.headerText }" />
        </span>
        <span class="cvp-close">✕</span>
      </span>
    </template>

    <!-- Chat message area -->
    <template v-else-if="kind === 'chat'">
      <span class="cvp-chat" :style="{ background: theme.msgsBg }">
        <span
          class="cvp-bubble cvp-left"
          :style="{
            background: theme.aiBubbleBg,
            borderColor: theme.aiBubbleBorder,
            color: theme.aiBubbleText,
          }"
        >
          Halo! Ada yang bisa saya bantu?
        </span>
        <span
          class="cvp-bubble cvp-right"
          :style="{ background: theme.userBubbleBg, color: theme.userBubbleText }"
        >
          Jelaskan tentang paket
        </span>
      </span>
    </template>

    <!-- AI bubble -->
    <template v-else-if="kind === 'aiBubble'">
      <span
        class="cvp-bubble cvp-left"
        :style="{
          background: theme.aiBubbleBg,
          borderColor: theme.aiBubbleBorder,
          color: theme.aiBubbleText,
        }"
      >
        Halo! Ada yang bisa saya bantu?
      </span>
    </template>

    <!-- User bubble -->
    <template v-else-if="kind === 'userBubble'">
      <span
        class="cvp-bubble cvp-right"
        :style="{ background: theme.userBubbleBg, color: theme.userBubbleText }"
      >
        Jelaskan tentang paket
      </span>
    </template>

    <!-- Thinking bubble -->
    <template v-else-if="kind === 'thinking'">
      <span
        class="cvp-think"
        :style="{
          background: theme.thinkingBg,
          borderColor: theme.thinkingBorder,
          color: theme.thinkingText,
        }"
      >
        <span class="cvp-think-summary">🧠 Reasoning…</span>
        <span class="cvp-think-line" :style="{ background: theme.thinkingText }" />
        <span class="cvp-think-line short" :style="{ background: theme.thinkingText }" />
      </span>
    </template>

    <!-- Tools bubble (bubble follows the AI bubble colors; chips have their own) -->
    <template v-else-if="kind === 'tools'">
      <span
        class="cvp-tools"
        :style="{
          background: theme.aiBubbleBg,
          borderColor: theme.aiBubbleBorder,
          color: theme.aiBubbleText,
        }"
      >
        <span
          class="cvp-tool"
          :style="{
            borderColor: theme.toolSuccessBorder,
            color: theme.toolSuccessText,
            background: theme.toolSuccessBg,
          }"
        >
          ✓ search_knowledge_base
        </span>
        <span
          class="cvp-tool"
          :style="{
            borderColor: theme.toolErrorBorder,
            color: theme.toolErrorText,
            background: theme.toolErrorBg,
          }"
        >
          ✕ fetch_page
        </span>
      </span>
    </template>

    <!-- Send button -->
    <template v-else-if="kind === 'btn'">
      <span class="cvp-send" :style="{ background: theme.btnBg, color: theme.btnText }">Send</span>
    </template>

    <!-- Input field -->
    <template v-else-if="kind === 'input'">
      <span
        class="cvp-input"
        :style="{
          background: theme.inputBg,
          borderColor: theme.inputBorder,
          color: theme.inputText,
        }"
      >
        Type your message…
      </span>
    </template>

    <!-- Toolbar (input + send) -->
    <template v-else-if="kind === 'toolbar'">
      <span
        class="cvp-toolbar"
        :style="{ background: theme.toolbarBg, borderColor: theme.toolbarBorder }"
      >
        <span
          class="cvp-input"
          :style="{
            background: theme.inputBg,
            borderColor: theme.inputBorder,
            color: theme.inputText,
          }"
        >
          Type your message…
        </span>
        <span class="cvp-send" :style="{ background: theme.btnBg, color: theme.btnText }"
          >Send</span
        >
      </span>
    </template>

    <!-- Accent swatch -->
    <template v-else-if="kind === 'accent'">
      <span class="cvp-accent" :style="{ background: theme.accent }" />
    </template>
  </span>
</template>
