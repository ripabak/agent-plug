<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { AdminUserDetail, UsageLog, UsageResponse } from '@/api/types'
import PlugMark from '@/components/PlugMark.vue'
import { useAdminStore } from '@/stores/admin'
import { formatCompact } from '@/utils/chartjs'
import { agentHeaderColor } from '@/utils/themes'
import { isPageUrl, pageLabel } from '@/utils/usage'

const admin = useAdminStore()
const router = useRouter()
const route = useRoute()
const userId = Number(route.params.id)

const error = ref('')
const loading = ref(false)
const detail = ref<AdminUserDetail | null>(null)
const usage = ref<UsageResponse | null>(null)
const page = ref(1)
const pageSize = 10

async function loadDetail() {
  loading.value = true
  error.value = ''
  try {
    detail.value = await api.adminUserDetail(admin.token, userId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load user'
  } finally {
    loading.value = false
  }
}

async function loadUsage() {
  try {
    usage.value = await api.adminUserUsage(admin.token, userId, {
      page: page.value,
      pageSize,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load usage'
  }
}

function goPage(p: number) {
  if (p === page.value || p < 1 || p > (usage.value?.pages ?? 1)) return
  page.value = p
  loadUsage()
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function statusLabel(status: UsageLog['status']): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

const hasUsage = computed(() => (usage.value?.total ?? 0) > 0)

onMounted(() => {
  loadDetail()
  loadUsage()
})
</script>

<template>
  <div class="page">
    <div class="topbar">
      <span class="brand"
        ><span class="logo-mark"><PlugMark :size="17" /></span> Agent-Plug
        <span class="badge badge-admin">Admin</span></span
      >
      <button class="btn btn-ghost btn-sm" @click="router.push('/admin')">← Back to users</button>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="loading" class="muted" style="padding: 8px 2px">Loading user…</div>

    <template v-if="detail">
      <!-- user profile (read-only) -->
      <div class="card">
        <div class="admin-user-head">
          <span class="agent-avatar" style="background: var(--bg)">{{ detail.user.display_name.charAt(0).toUpperCase() }}</span>
          <div>
            <h2 style="margin: 0">{{ detail.user.display_name }}</h2>
            <div class="muted">{{ detail.user.email }} · joined {{ fmtDate(detail.user.created_at) }}</div>
          </div>
        </div>
        <div class="usage-summary" style="margin-top: 16px">
          <div class="usage-stat">
            <div class="usage-stat-value">{{ detail.user.agent_count }}</div>
            <div class="usage-stat-label">Agents</div>
          </div>
          <div class="usage-stat">
            <div class="usage-stat-value">{{ detail.user.total_requests.toLocaleString() }}</div>
            <div class="usage-stat-label">Requests</div>
          </div>
          <div class="usage-stat">
            <div class="usage-stat-value">{{ formatCompact(detail.user.total_tokens) }}</div>
            <div class="usage-stat-label">Tokens</div>
          </div>
          <div class="usage-stat">
            <div class="usage-stat-value admin-date">{{ fmtDate(detail.user.last_active) }}</div>
            <div class="usage-stat-label">Last active</div>
          </div>
        </div>
      </div>

      <!-- agents: clickable cards, dashboard style -->
      <div class="card">
        <h3 style="margin: 0 0 12px">Agents ({{ detail.agents.length }})</h3>
        <p class="muted" style="margin: 0 0 14px">
          Read-only view — click an agent to inspect its settings, knowledge, usage and embed
          snippet.
        </p>
        <div class="agent-grid">
          <RouterLink
            v-for="a in detail.agents"
            :key="a.id"
            :to="`/admin/agents/${a.id}`"
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
            <h3 style="margin: 0 0 4px">{{ a.name }}</h3>
            <p style="margin: 0 0 8px">{{ a.description || 'No description' }}</p>
            <div class="muted admin-card-stats">
              <span>{{ a.ready_sources }}/{{ a.source_count }} sources</span>
              <span>·</span>
              <span>{{ a.total_requests.toLocaleString() }} requests</span>
              <span>·</span>
              <span>{{ a.total_tokens.toLocaleString() }} tokens</span>
            </div>
          </RouterLink>
        </div>
        <p v-if="!detail.agents.length" class="muted" style="margin: 0">No agents yet.</p>
      </div>

      <!-- usage history (all agents) -->
      <div class="card">
        <h3 style="margin: 0 0 12px">Usage history</h3>
        <p v-if="!hasUsage" class="muted" style="margin: 0">
          No usage yet for this user's agents.
        </p>
        <template v-else>
          <div class="usage-table-scroll">
            <table class="usage-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Agent</th>
                  <th>Page</th>
                  <th>Model</th>
                  <th class="num">Input</th>
                  <th class="num">Output</th>
                  <th class="num">Total</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in usage?.items" :key="item.id">
                  <td class="admin-date">{{ fmtDate(item.created_at) }}</td>
                  <td>
                    <template v-if="item.agent_name">{{ item.agent_name }}</template>
                    <template v-else>—</template>
                  </td>
                  <td class="usage-page">
                    <a
                      v-if="isPageUrl(item.page_url)"
                      :href="item.page_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      :title="item.page_url"
                      >{{ pageLabel(item.page_url) }}</a
                    >
                    <template v-else>{{ pageLabel(item.page_url) }}</template>
                  </td>
                  <td class="usage-model">{{ item.model || '—' }}</td>
                  <td class="num">{{ item.input_tokens.toLocaleString() }}</td>
                  <td class="num">{{ item.output_tokens.toLocaleString() }}</td>
                  <td class="num"><strong>{{ item.total_tokens.toLocaleString() }}</strong></td>
                  <td>
                    <span :class="`usage-status usage-status-${item.status}`">{{
                      statusLabel(item.status)
                    }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="pagination">
            <button class="btn btn-ghost btn-sm" :disabled="page <= 1" @click="goPage(page - 1)">
              ← Prev
            </button>
            <span class="muted">Page {{ usage?.page }} of {{ usage?.pages }}</span>
            <button
              class="btn btn-ghost btn-sm"
              :disabled="page >= (usage?.pages ?? 1)"
              @click="goPage(page + 1)"
            >
              Next →
            </button>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>
