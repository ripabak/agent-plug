<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentsStore } from '@/stores/agents'
import AvatarPicker from '@/components/AvatarPicker.vue'

const agentsStore = useAgentsStore()
const router = useRouter()

const form = reactive({
  name: '',
  description: '',
  welcome_message: 'Hi! How can I help you?',
  avatar_emoji: '🤖',
})

const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const agent = await agentsStore.create({ ...form })
    router.push({ path: `/agents/${agent.id}`, query: { tab: 'knowledge', created: '1' } })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to create agent'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page page-narrow">
    <div class="topbar">
      <RouterLink to="/dashboard" class="brand"><span class="logo-mark">🤖</span> Agent-Plug</RouterLink>
      <RouterLink to="/dashboard" class="btn btn-ghost btn-sm">← Back</RouterLink>
    </div>

    <div class="card">
      <h1 style="margin-top: 0">Create an agent</h1>
      <div class="hint">
        <strong>3 steps:</strong> name your agent → add your URLs (knowledge) → preview & embed.
      </div>
      <div v-if="error" class="error-box">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label for="name">Agent name *</label>
          <input id="name" v-model="form.name" type="text" placeholder="e.g. Acme Support Bot" required />
        </div>
        <div class="form-group">
          <label for="desc">Description</label>
          <textarea id="desc" v-model="form.description" rows="2" placeholder="What does this agent do?" />
        </div>
        <div class="form-group">
          <label for="welcome">Welcome message</label>
          <input id="welcome" v-model="form.welcome_message" type="text" />
        </div>
        <div class="form-group">
          <label>Avatar emoji</label>
          <AvatarPicker v-model="form.avatar_emoji" />
        </div>
        <button class="btn btn-block" type="submit" :disabled="busy || !form.name.trim()">
          <span v-if="busy" class="spinner" /> Create agent
        </button>
      </form>
    </div>
  </div>
</template>
