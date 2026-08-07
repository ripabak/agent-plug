<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { API_BASE, api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useAgentsStore } from '@/stores/agents'

const agentsStore = useAgentsStore()
const auth = useAuthStore()
const agent = computed(() => agentsStore.current)

const embedHtml = ref('')
const copied = ref(false)
const error = ref('')

const demoUrl = computed(
  () =>
    `${window.location.origin}/demo.html?agent=${agent.value?.id ?? ''}&token=${agent.value?.public_token ?? ''}&base=${encodeURIComponent(API_BASE)}`,
)

onMounted(async () => {
  if (!agent.value) return
  try {
    const res = await api.getEmbed(auth.token, agent.value.id)
    embedHtml.value = res.html
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load embed snippet'
  }
})

async function copy() {
  try {
    await navigator.clipboard.writeText(embedHtml.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    /* clipboard unavailable */
  }
}
</script>

<template>
  <div class="card">
    <h3 style="margin-top: 0">Embed on your website</h3>
    <p class="muted">
      Copy this snippet and paste it anywhere in your website's HTML (<code>&lt;body&gt;</code>).
      Visitors will see a floating chat button at the bottom-right.
    </p>

    <div v-if="error" class="error-box">{{ error }}</div>

    <pre class="code-block" data-testid="embed-code">{{ embedHtml }}</pre>

    <div style="display: flex; gap: 10px; flex-wrap: wrap">
      <button class="btn" :disabled="!embedHtml" @click="copy">
        {{ copied ? 'Copied ✓' : 'Copy snippet' }}
      </button>
      <a class="btn btn-secondary" :href="demoUrl" target="_blank" rel="noopener noreferrer"
        >Open demo page</a
      >
    </div>

    <hr style="border: none; border-top: 1px solid var(--border); margin: 20px 0" />

    <h4 style="margin: 0 0 8px">What's inside</h4>
    <ul class="muted" style="margin: 0; padding-left: 18px">
      <li><code>data-agent-id</code> — identifies the agent.</li>
      <li><code>data-token</code> — secret key that authenticates the widget (keep it private).</li>
      <li><code>data-base-url</code> — where the widget script + API live.</li>
    </ul>
    <p class="muted" style="font-size: 12px; margin-bottom: 0">
      React / Vue SDKs are planned. For now the snippet works on any plain HTML page.
    </p>
  </div>
</template>
