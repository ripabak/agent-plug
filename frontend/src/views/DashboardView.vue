<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAgentsStore } from '@/stores/agents'
import PlugMark from '@/components/PlugMark.vue'
import { agentHeaderColor } from '@/utils/themes'

const auth = useAuthStore()
const agentsStore = useAgentsStore()
const router = useRouter()
const error = ref('')

onMounted(async () => {
  try {
    await agentsStore.fetchAgents()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load agents'
  }
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="page">
    <div class="topbar">
      <span class="brand"
        ><span class="logo-mark"><PlugMark :size="17" /></span> Agent-Plug</span
      >
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
        <span class="muted">Hi, {{ auth.user?.display_name }}</span>
        <button class="btn btn-ghost btn-sm" @click="logout">Log out</button>
      </div>
    </div>

    <h2 style="margin: 0 0 4px">Your agents</h2>
    <p class="muted" style="margin: 0 0 20px">
      Create an agent, feed it your URLs, then embed it on your website.
    </p>

    <div v-if="error" class="error-box">{{ error }}</div>

    <div class="agent-grid">
      <RouterLink
        v-for="a in agentsStore.agents"
        :key="a.id"
        :to="`/agents/${a.id}?tab=knowledge`"
        class="card agent-card"
      >
        <img
          v-if="a.avatar_url"
          :src="a.avatar_url"
          class="agent-avatar"
          :style="{ background: agentHeaderColor(a) }"
          alt=""
        />
        <span v-else class="agent-avatar" :style="{ background: agentHeaderColor(a) }">{{
          a.avatar_emoji
        }}</span>
        <h3>{{ a.name }}</h3>
        <p>{{ a.description || 'No description' }}</p>
      </RouterLink>

      <RouterLink
        to="/agents/new"
        class="card agent-card"
        style="border-style: dashed; text-align: center"
      >
        <span class="agent-avatar" style="background: var(--bg)">
          <svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path
              d="M8 3v10M3 8h10"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
            />
          </svg>
        </span>
        <h3>New Agent</h3>
        <p>Create your first AI agent</p>
      </RouterLink>
    </div>
  </div>
</template>
