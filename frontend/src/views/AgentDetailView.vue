<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentsStore } from '@/stores/agents'
import ConfigureTab from '@/components/ConfigureTab.vue'
import KnowledgeTab from '@/components/KnowledgeTab.vue'
import PreviewTab from '@/components/PreviewTab.vue'
import EmbedTab from '@/components/EmbedTab.vue'
import UsageTab from '@/components/UsageTab.vue'
import PlugMark from '@/components/PlugMark.vue'
import { agentHeaderColor } from '@/utils/themes'

const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()

const agentId = computed(() => Number(route.params.id))
const error = ref('')
const showCreatedHint = ref(false)

/** Background for the agent avatar — the same header color the widget button uses. */
const headerColor = computed(() =>
  agentsStore.current ? agentHeaderColor(agentsStore.current) : 'var(--bg)',
)

type Tab = 'configure' | 'knowledge' | 'preview' | 'usage' | 'embed'
const tabs: { key: Tab; label: string }[] = [
  { key: 'configure', label: 'Configure' },
  { key: 'knowledge', label: 'Knowledge' },
  { key: 'preview', label: 'Preview' },
  { key: 'usage', label: 'Usage' },
  { key: 'embed', label: 'Embed' },
]

const activeTab = ref<Tab>((route.query.tab as Tab) || 'configure')

watch(
  () => route.query.tab,
  (t) => {
    if (t) activeTab.value = t as Tab
  },
)

function setTab(tab: Tab) {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

onMounted(async () => {
  try {
    await agentsStore.fetchAgent(agentId.value)
    showCreatedHint.value = route.query.created === '1'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load agent'
  }
})
</script>

<template>
  <div class="page">
    <div class="topbar">
      <RouterLink to="/dashboard" class="brand"
        ><span class="logo-mark"><PlugMark :size="17" /></span> Agent-Plug</RouterLink
      >
      <RouterLink to="/dashboard" class="btn btn-ghost btn-sm">← All agents</RouterLink>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>
    <template v-else-if="agentsStore.current">
      <div class="topbar" style="margin-bottom: 8px">
        <div class="agent-head">
          <img
            v-if="agentsStore.current.avatar_url"
            :src="agentsStore.current.avatar_url"
            class="agent-avatar"
            :style="{ background: headerColor }"
            alt=""
          />
          <span v-else class="agent-avatar" :style="{ background: headerColor }">
            {{ agentsStore.current.avatar_emoji }}
          </span>
          <div class="agent-head-info">
            <h2>{{ agentsStore.current.name }}</h2>
            <span class="muted">{{ agentsStore.current.description || 'No description' }}</span>
          </div>
        </div>
      </div>

      <div v-if="showCreatedHint" class="hint">
        <svg
          width="13"
          height="13"
          viewBox="0 0 14 14"
          fill="none"
          aria-hidden="true"
          style="vertical-align: -2px; margin-right: 6px"
        >
          <path
            d="M2.5 7.4 5.4 10.3 11.5 3.8"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        Agent created! Now add your website pages to the knowledge base, and the helper answers from
        them once it finishes reading.
      </div>

      <div class="tabs">
        <button
          v-for="t in tabs"
          :key="t.key"
          class="tab"
          :class="{ active: activeTab === t.key }"
          @click="setTab(t.key)"
        >
          {{ t.label }}
        </button>
      </div>

      <ConfigureTab v-if="activeTab === 'configure'" />
      <KnowledgeTab v-else-if="activeTab === 'knowledge'" />
      <PreviewTab v-else-if="activeTab === 'preview'" />
      <UsageTab v-else-if="activeTab === 'usage'" />
      <EmbedTab v-else />
    </template>
  </div>
</template>
