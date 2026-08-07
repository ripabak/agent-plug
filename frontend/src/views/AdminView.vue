<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { ChartData } from 'chart.js'

import { api } from '@/api/client'
import type { AdminStats, AdminUsersResponse } from '@/api/types'
import PlugMark from '@/components/PlugMark.vue'
import UsageChart from '@/components/UsageChart.vue'
import { useAdminStore } from '@/stores/admin'
import { OUTPUT, PRIMARY, formatCompact, requestChartData, tokenChartData } from '@/utils/chartjs'

const admin = useAdminStore()
const router = useRouter()

const error = ref('')
const loading = ref(false)
const stats = ref<AdminStats | null>(null)
const users = ref<AdminUsersResponse | null>(null)

const days = ref(30)
const DAYS_OPTIONS = [7, 30, 90]
const q = ref('')
const page = ref(1)
const pageSize = 20

async function loadStats() {
  try {
    stats.value = await api.adminStats(admin.token, days.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load stats'
  }
}

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    users.value = await api.adminUsers(admin.token, {
      q: q.value.trim(),
      page: page.value,
      pageSize,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load users'
  } finally {
    loading.value = false
  }
}

function changeDays(d: number) {
  if (d === days.value) return
  days.value = d
  loadStats()
}

function goPage(p: number) {
  if (p === page.value || p < 1 || p > (users.value?.pages ?? 1)) return
  page.value = p
  loadUsers()
}

function search() {
  page.value = 1
  loadUsers()
}

function openUser(id: number) {
  router.push(`/admin/users/${id}`)
}

function logout() {
  admin.logout()
  router.push('/admin/login')
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

const requestData = computed<ChartData<'bar'>>(() =>
  requestChartData(stats.value?.series ?? []),
)
const tokenData = computed<ChartData<'bar'>>(() => tokenChartData(stats.value?.series ?? []))

const hasUsers = computed(() => (users.value?.total ?? 0) > 0)

onMounted(() => {
  loadStats()
  loadUsers()
})
</script>

<template>
  <div class="page">
    <div class="topbar">
      <span class="brand"
        ><span class="logo-mark"><PlugMark :size="17" /></span> Agent-Plug
        <span class="badge badge-admin">Admin</span></span
      >
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
        <span class="muted">{{ admin.email }}</span>
        <button class="btn btn-ghost btn-sm" @click="logout">Log out</button>
      </div>
    </div>

    <h2 style="margin: 0 0 4px">Platform overview</h2>
    <p class="muted" style="margin: 0 0 20px">
      Read-only monitoring: users, agents and token usage. Click a user to inspect their account.
    </p>

    <div v-if="error" class="error-box">{{ error }}</div>

    <!-- headline stats -->
    <div v-if="stats" class="usage-summary">
      <div class="usage-stat">
        <div class="usage-stat-value">{{ stats.total_users }}</div>
        <div class="usage-stat-label">Total users</div>
      </div>
      <div class="usage-stat">
        <div class="usage-stat-value">{{ stats.total_agents }}</div>
        <div class="usage-stat-label">Total agents</div>
      </div>
      <div class="usage-stat">
        <div class="usage-stat-value">{{ formatCompact(stats.total_requests) }}</div>
        <div class="usage-stat-label">Total requests</div>
      </div>
      <div class="usage-stat">
        <div class="usage-stat-value">{{ formatCompact(stats.total_tokens) }}</div>
        <div class="usage-stat-label">Total tokens</div>
      </div>
    </div>

    <!-- platform charts -->
    <template v-if="stats">
      <div class="usage-chart-toolbar">
        <div class="days-switch">
          <button
            v-for="d in DAYS_OPTIONS"
            :key="d"
            class="days-btn"
            :class="{ active: days === d }"
            @click="changeDays(d)"
          >
            {{ d }}d
          </button>
        </div>
      </div>

      <div class="usage-charts">
        <div class="card usage-chart-card">
          <div class="usage-chart-head">
            <h3 style="margin: 0">Requests</h3>
            <span class="muted">all agents</span>
          </div>
          <UsageChart :data="requestData" />
        </div>
        <div class="card usage-chart-card">
          <div class="usage-chart-head">
            <h3 style="margin: 0">Tokens</h3>
            <div class="chart-legend">
              <span class="legend-item"
                ><span class="legend-dot" :style="{ background: PRIMARY }" />Input</span
              >
              <span class="legend-item"
                ><span class="legend-dot" :style="{ background: OUTPUT }" />Output</span
              >
            </div>
          </div>
          <UsageChart :data="tokenData" />
        </div>
      </div>
    </template>

    <!-- users -->
    <div class="card">
      <div class="admin-list-head">
        <h3 style="margin: 0">Users</h3>
        <form class="admin-search" @submit.prevent="search">
          <input
            v-model="q"
            type="search"
            placeholder="Search by email or name…"
            aria-label="Search users"
          />
          <button class="btn btn-secondary btn-sm" type="submit">Search</button>
        </form>
      </div>

      <div v-if="loading" class="muted" style="padding: 8px 2px">Loading users…</div>

      <template v-else-if="users">
        <div class="usage-table-scroll">
          <table class="usage-table admin-users-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Created</th>
                <th class="num">Agents</th>
                <th class="num">Requests</th>
                <th class="num">Tokens</th>
                <th>Last active</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="u in users.items"
                :key="u.id"
                class="admin-user-row"
                @click="openUser(u.id)"
              >
                <td>
                  <div class="admin-user-name">{{ u.display_name }}</div>
                  <div class="admin-user-email muted">{{ u.email }}</div>
                </td>
                <td class="admin-date">{{ fmtDate(u.created_at) }}</td>
                <td class="num">{{ u.agent_count }}</td>
                <td class="num">{{ u.total_requests.toLocaleString() }}</td>
                <td class="num"><strong>{{ u.total_tokens.toLocaleString() }}</strong></td>
                <td class="admin-date">{{ fmtDate(u.last_active) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-if="!hasUsers" class="muted" style="margin: 8px 0 0">
          No users match your search.
        </p>

        <div class="pagination">
          <button class="btn btn-ghost btn-sm" :disabled="page <= 1" @click="goPage(page - 1)">
            ← Prev
          </button>
          <span class="muted">Page {{ users.page }} of {{ users.pages }}</span>
          <button
            class="btn btn-ghost btn-sm"
            :disabled="page >= users.pages"
            @click="goPage(page + 1)"
          >
            Next →
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
