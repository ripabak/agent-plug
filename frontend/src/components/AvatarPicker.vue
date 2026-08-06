<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

/** Preset avatar emojis offered by the picker (default 🤖 first). */
const AVATAR_EMOJIS = [
  '🤖', '🦾', '🧠', '💬', '🚀', '✨', '🎯', '🔧', '📚', '🧩',
  '🎨', '⚡', '🦉', '🐙', '🌟', '🤝', '🐱', '🐶', '🦄', '🌍',
]

/** Keep a legacy custom emoji (from the old free-text input) visible and
 *  selected, so existing agents don't silently lose their avatar. */
const options = computed(() =>
  AVATAR_EMOJIS.includes(props.modelValue) ? AVATAR_EMOJIS : [...AVATAR_EMOJIS, props.modelValue],
)
</script>

<template>
  <div class="avatar-picker">
    <button
      v-for="emoji in options"
      :key="emoji"
      type="button"
      class="avatar-option"
      :class="{ active: modelValue === emoji }"
      :title="emoji"
      @click="emit('update:modelValue', emoji)"
    >
      {{ emoji }}
    </button>
  </div>
</template>
