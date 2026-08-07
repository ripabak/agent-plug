<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ChartData } from 'chart.js'

import { api } from '@/api/client'
import type { UsageLog, UsageResponse } from '@/api/types'
import UsageChart from '@/components/UsageChart.vue'
import { useAgentsStore } from '@/stores/agents'
import { useAuthStore } from '@/stores/auth'
import { PRIMARY, OUTPUT, formatCompact, requestChartData, tokenChartData } from '@/utils/chartjs'

const agentsStore = useAgentsStore()
const auth = useAuthStore()

const agent = computed(() => agentsStore.current)

const loading = ref(false)
const error = ref('')
const days = ref(30)
const page = ref(1)
const pageSize = 10
const data = ref<UsageResponse | null>(null)

const DAYS_OPTIONS = [7, 30, 90]

async function load() {
  if (!agent.value) return
  loading.value = true
  error.value = ''
  try {
    data.value = await api.getUsage(auth.token, agent.value.id, {
      days: days.value,
      page: page.value,
      pageSize,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load usage'
  } finally {
    loading.value = false
  }
}

function changeDays(d: number) {
  if (d === days.value) return
  days.value = d
  page.value = 1
  load()
}

function goPage(p: number) {
  if (p === page.value || p < 1 || p > (data.value?.pages ?? 1)) return
  page.value = p
  load()
}

const requestData = computed<ChartData<'bar'>>(() =>
  requestChartData(data.value?.summary.series ?? []),
)

const tokenData = computed<ChartData<'bar'>>(() => tokenChartData(data.value?.summary.series ?? []))

const hasData = computed(() => (data.value?.total ?? 0) > 0)

const topCountries = computed(() => data.value?.summary.countries ?? [])

const totalRequests = computed(() => data.value?.summary.total_requests ?? 0)

/** Share of ALL requests coming from this country (for bar widths). */
function share(country: { requests: number }): number {
  return totalRequests.value > 0 ? Math.round((country.requests / totalRequests.value) * 100) : 0
}

const regionNames = new Intl.DisplayNames(['en'], { type: 'region' })

/** 'ID' -> '🇮🇩' (flag emoji from the ISO alpha-2 code). */
function countryFlag(code: string): string {
  return code.toUpperCase().replace(/./g, (c) => String.fromCodePoint(127397 + c.charCodeAt(0)))
}

/** 'ID' -> 'Indonesia' (built-in Intl, no lookup table needed). */
function countryName(code: string): string {
  try {
    return regionNames.of(code) ?? code
  } catch {
    return code
  }
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function channelLabel(channel: UsageLog['channel']): string {
  return channel === 'widget' ? 'Widget' : 'Preview'
}

function statusClass(status: UsageLog['status']): string {
  return `usage-status usage-status-${status}`
}

function statusLabel(status: UsageLog['status']): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

onMounted(load)
</script>

<template>
  <div class="usage-tab">
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="loading" class="muted" style="padding: 8px 2px">Loading usage…</div>

    <template v-if="data">
      <!-- headline stats -->
      <div class="usage-summary">
        <div class="usage-stat">
          <div class="usage-stat-value">{{ data.summary.total_requests }}</div>
          <div class="usage-stat-label">Requests</div>
        </div>
        <div class="usage-stat">
          <div class="usage-stat-value">{{ formatCompact(data.summary.total_input_tokens) }}</div>
          <div class="usage-stat-label">Input tokens</div>
        </div>
        <div class="usage-stat">
          <div class="usage-stat-value">{{ formatCompact(data.summary.total_output_tokens) }}</div>
          <div class="usage-stat-label">Output tokens</div>
        </div>
        <div class="usage-stat">
          <div class="usage-stat-value">{{ formatCompact(data.summary.total_tokens) }}</div>
          <div class="usage-stat-label">Total tokens</div>
        </div>
      </div>

      <!-- charts -->
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

      <!-- top countries -->
      <div v-if="topCountries.length" class="card usage-countries">
        <div class="usage-chart-head">
          <h3 style="margin: 0">Top countries</h3>
          <span class="muted">share of all {{ totalRequests }} requests</span>
        </div>
        <ol class="usage-country-rank">
          <li v-for="(c, i) in topCountries" :key="c.country" class="usage-country-row">
            <span class="usage-rank">{{ i + 1 }}</span>
            <span class="usage-country-flag">{{ countryFlag(c.country) }}</span>
            <span class="usage-country-name">{{ countryName(c.country) }}</span>
            <span class="usage-country-bar">
              <span class="usage-country-bar-fill" :style="{ width: share(c) + '%' }" />
            </span>
            <span class="usage-country-count">{{ c.requests }}</span>
            <span class="usage-country-pct muted">{{ share(c) }}%</span>
          </li>
        </ol>
      </div>

      <!-- history -->
      <div class="card usage-history">
        <h3 style="margin: 0 0 12px">Usage history</h3>
        <p v-if="!hasData" class="muted" style="margin: 0">
          No usage yet — try a chat in the Preview tab or embed the widget on a site.
        </p>
        <template v-else>
          <div class="usage-table-scroll">
            <table class="usage-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Channel</th>
                  <th>Country</th>
                  <th>Model</th>
                  <th class="num">Input</th>
                  <th class="num">Output</th>
                  <th class="num">Total</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in data.items" :key="item.id">
                  <td class="usage-time">{{ fmtTime(item.created_at) }}</td>
                  <td>{{ channelLabel(item.channel) }}</td>
                  <td class="usage-country">
                    <template v-if="item.country"
                      >{{ countryFlag(item.country) }} {{ countryName(item.country) }}</template
                    >
                    <template v-else>—</template>
                  </td>
                  <td class="usage-model">{{ item.model || '—' }}</td>
                  <td class="num">{{ item.input_tokens.toLocaleString() }}</td>
                  <td class="num">{{ item.output_tokens.toLocaleString() }}</td>
                  <td class="num">
                    <strong>{{ item.total_tokens.toLocaleString() }}</strong>
                  </td>
                  <td>
                    <span :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="pagination">
            <button class="btn btn-ghost btn-sm" :disabled="page <= 1" @click="goPage(page - 1)">
              ← Prev
            </button>
            <span class="muted">Page {{ data.page }} of {{ data.pages }}</span>
            <button
              class="btn btn-ghost btn-sm"
              :disabled="page >= data.pages"
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
