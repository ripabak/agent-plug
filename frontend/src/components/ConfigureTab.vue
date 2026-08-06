<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentsStore } from '@/stores/agents'
import AvatarPicker from './AvatarPicker.vue'

const agentsStore = useAgentsStore()
const router = useRouter()

const form = reactive({
  name: '',
  description: '',
  system_prompt: '',
  welcome_message: '',
  avatar_emoji: '🤖',
})

const saved = ref(false)
const error = ref('')
const busy = ref(false)
const deleting = ref(false)

function syncForm() {
  const a = agentsStore.current
  if (!a) return
  form.name = a.name
  form.description = a.description
  form.system_prompt = a.system_prompt ?? ''
  form.welcome_message = a.welcome_message
  form.avatar_emoji = a.avatar_emoji
}

watch(() => agentsStore.current, syncForm, { immediate: true })

async function save() {
  error.value = ''
  busy.value = true
  try {
    await agentsStore.update({ ...form, system_prompt: form.system_prompt || null })
    saved.value = true
    setTimeout(() => (saved.value = false), 2000)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save'
  } finally {
    busy.value = false
  }
}

async function regenerateToken() {
  if (!confirm('Regenerate the public token? Existing embed snippets will stop working until updated.')) return
  await agentsStore.regenerateToken()
}

async function removeAgent() {
  if (!agentsStore.current) return
  if (!confirm(`Delete "${agentsStore.current.name}"? This cannot be undone.`)) return
  deleting.value = true
  try {
    await agentsStore.remove(agentsStore.current.id)
    router.push('/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to delete'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="card">
    <h3 style="margin-top: 0">Personalization</h3>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div class="form-group">
      <label for="c-name">Agent name</label>
      <input id="c-name" v-model="form.name" type="text" />
    </div>
    <div class="form-group">
      <label for="c-desc">Description (shown to visitors under the bot name)</label>
      <textarea id="c-desc" v-model="form.description" rows="2" />
    </div>
    <div class="form-group">
      <label for="c-welcome">Welcome message</label>
      <input id="c-welcome" v-model="form.welcome_message" type="text" />
    </div>
    <div class="form-group">
      <label for="c-prompt">System prompt (advanced — overrides the default instructions)</label>
      <textarea id="c-prompt" v-model="form.system_prompt" rows="5"
        placeholder="Leave empty to use the default prompt (knowledge base + citation rules)." />
    </div>
    <div class="form-group">
      <label>Avatar emoji</label>
      <AvatarPicker v-model="form.avatar_emoji" />
    </div>
    <button class="btn" :disabled="busy || !form.name.trim()" @click="save">
      <span v-if="busy" class="spinner" /> Save changes
      <span v-if="saved" style="color: #d1fae5">✓</span>
    </button>

    <hr style="border: none; border-top: 1px solid var(--border); margin: 20px 0" />

    <h3 style="margin-top: 0">Danger zone</h3>
    <div style="display: flex; gap: 10px; flex-wrap: wrap">
      <button class="btn btn-secondary btn-sm" @click="regenerateToken">Regenerate public token</button>
      <button class="btn btn-danger btn-sm" :disabled="deleting" @click="removeAgent">
        <span v-if="deleting" class="spinner" /> Delete agent
      </button>
    </div>
    <p class="muted" style="margin-bottom: 0; margin-top: 10px; font-size: 12px">
      Public token: <code style="word-break: break-all">{{ agentsStore.current?.public_token }}</code>
    </p>
  </div>
</template>
