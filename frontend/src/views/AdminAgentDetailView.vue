<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ChartData } from 'chart.js'

import { API_BASE, api } from '@/api/client'
import type { AdminAgentDetail, Source, UsageLog, UsageResponse } from '@/api/types'
import StatusBadge from '@/components/StatusBadge.vue'
import UsageChart from '@/components/UsageChart.vue'
import { useAdminStore } from '@/stores/admin'
import { OUTPUT, PRIMARY, formatCompact, requestChartData, tokenChartData } from '@/utils/chartjs'
import { agentHeaderColor } from '@/utils/themes'
import {
  applyThemeOverrides,
  defaultTheme,
  findPreset,
  type ChatTheme,
} from '@/utils/themes'
import type { WidgetBridge } from '@/utils/widgetBridge'
import { isPageUrl, pageLabel } from '@/utils/usage'
import { findPersonaTemplate } from '@/utils/personaTemplates'

const admin = useAdminStore()
const route = useRoute()
const router = useRouter()
const agentId = computed(() => Number(route.params.id))

const error = ref('')
const loading = ref(true)
const detail = ref<AdminAgentDetail | null>(null)

const sources = ref<Source[]>([])
const sourcesLoading = ref(false)

const usage = ref<UsageResponse | null>(null)
const days = ref(30)
const DAYS_OPTIONS = [7, 30, 90]
const page = ref(1)
const pageSize = 10

const embedHtml = ref('')
const copied = ref(false)

/** Background for the agent avatar — the same header color the widget uses. */
const headerColor = computed(() =>
  detail.value ? agentHeaderColor(detail.value.agent) : 'var(--bg)',
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

function setTab(tab: Tab) {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

async function loadAgent() {
  loading.value = true
  error.value = ''
  try {
    detail.value = await api.adminAgent(admin.token, agentId.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load agent'
  } finally {
    loading.value = false
  }
}

async function loadSources() {
  sourcesLoading.value = true
  try {
    sources.value = await api.adminAgentSources(admin.token, agentId.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load sources'
  } finally {
    sourcesLoading.value = false
  }
}

async function loadUsage() {
  try {
    usage.value = await api.adminAgentUsage(admin.token, agentId.value, {
      days: days.value,
      page: page.value,
      pageSize,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load usage'
  }
}

function changeDays(d: number) {
  if (d === days.value) return
  days.value = d
  page.value = 1
  loadUsage()
}

function goPage(p: number) {
  if (p === page.value || p < 1 || p > (usage.value?.pages ?? 1)) return
  page.value = p
  loadUsage()
}

async function loadEmbed() {
  if (embedHtml.value) return
  try {
    const res = await api.adminAgentEmbed(admin.token, agentId.value)
    embedHtml.value = res.html
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load embed snippet'
  }
}

// Lazy-load tab data (sources on demand; usage/embed only when opened).
watch(
  activeTab,
  (t) => {
    if (t === 'knowledge' && !sources.value.length) loadSources()
    if (t === 'usage' && !usage.value) loadUsage()
    if (t === 'embed') loadEmbed()
  },
  { immediate: true },
)

// --- preview: embed the REAL widget (read-only — no config panel) ---
const widgetHost = ref<HTMLDivElement | null>(null)
const previewReady = computed(() => activeTab.value === 'preview' && !!detail.value)

function widgetBridge(): WidgetBridge | undefined {
  const id = detail.value?.agent.id
  return id !== undefined ? window.__apwWidgets?.[String(id)] : undefined
}

function mountWidget() {
  const a = detail.value?.agent
  if (!a || !widgetHost.value) return
  widgetHost.value.innerHTML = ''
  const s = document.createElement('script')
  s.src = `${API_BASE}/api/public/widget.js`
  s.setAttribute('data-agent-id', String(a.id))
  s.setAttribute('data-token', a.public_token)
  s.setAttribute('data-base-url', API_BASE)
  s.setAttribute('data-auto-open', 'desktop')
  widgetHost.value.appendChild(s)
}

// flush: 'post' — run AFTER the template renders the host div (the tab
// content is v-if'd, so the ref is only set after the DOM update).
watch(
  previewReady,
  (ready) => {
    if (ready) mountWidget()
  },
  { flush: 'post' },
)

// The widget attaches its launcher/panel to document.body (floating) —
// remove it via the bridge when leaving the tab or the page.
watch(activeTab, (t) => {
  if (t !== 'preview') widgetBridge()?.destroy?.()
})

onBeforeUnmount(() => {
  widgetBridge()?.destroy?.()
})

// --- embed helpers ---
const demoUrl = computed(
  () =>
    `${window.location.origin}/demo.html?agent=${detail.value?.agent.id ?? ''}&token=${detail.value?.agent.public_token ?? ''}&base=${encodeURIComponent(API_BASE)}`,
)

async function copySnippet() {
  try {
    await navigator.clipboard.writeText(embedHtml.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    /* clipboard unavailable */
  }
}

// --- formatting ---
function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function channelLabel(channel: UsageLog['channel']): string {
  return channel === 'widget' ? 'Widget' : 'Preview'
}

function statusLabel(status: UsageLog['status']): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

// --- countries (parity with the dashboard Usage tab) ---
const topCountries = computed(() => usage.value?.summary.countries ?? [])
const totalRequests = computed(() => usage.value?.summary.total_requests ?? 0)

function share(country: { requests: number }): number {
  return totalRequests.value > 0
    ? Math.round((country.requests / totalRequests.value) * 100)
    : 0
}

const regionNames = new Intl.DisplayNames(['en'], { type: 'region' })

function countryFlag(code: string): string {
  return code
    .toUpperCase()
    .replace(/./g, (c) => String.fromCodePoint(127397 + c.charCodeAt(0)))
}

function countryName(code: string): string {
  try {
    return regionNames.of(code) ?? code
  } catch {
    return code
  }
}

// --- configure (read-only parity) ---
const persona = computed(() => {
  const prompt = detail.value?.agent.persona_prompt
  if (!prompt) return null
  const t = findPersonaTemplate(prompt)
  return t ? { label: `${t.emoji} ${t.label}`, prompt } : { label: null, prompt }
})

// --- preview (read-only mirror of the dashboard config panel) ---
const theme = computed<ChatTheme>(() => {
  let base = defaultTheme()
  const raw = detail.value?.agent.chat_theme
  if (raw) {
    try {
      const saved = JSON.parse(raw) as {
        preset?: string
        custom?: Partial<ChatTheme>
      } | null
      const preset = saved?.preset ? findPreset(saved.preset) : undefined
      if (preset) base = { ...preset }
      if (saved?.custom) base = applyThemeOverrides(base, saved.custom)
    } catch {
      /* malformed chat_theme — keep the default */
    }
  }
  return base
})

const themePresetName = computed(() => {
  const raw = detail.value?.agent.chat_theme
  if (!raw) return null
  try {
    const saved = JSON.parse(raw) as { preset?: string } | null
    const preset = saved?.preset ? findPreset(saved.preset) : undefined
    return preset?.label ?? null
  } catch {
    return null
  }
})

const themeCustomized = computed(() => {
  const raw = detail.value?.agent.chat_theme
  if (!raw) return false
  try {
    const saved = JSON.parse(raw) as { touched?: boolean } | null
    return saved?.touched === true
  } catch {
    return false
  }
})

const requestData = computed<ChartData<'bar'>>(() =>
  requestChartData(usage.value?.summary.series ?? []),
)
const tokenData = computed<ChartData<'bar'>>(() => tokenChartData(usage.value?.summary.series ?? []))

const hasUsage = computed(() => (usage.value?.total ?? 0) > 0)

onMounted(loadAgent)
</script>

<template>
  <div class="page">
    <div class="topbar">
      <button class="btn btn-ghost btn-sm" @click="router.push(`/admin/users/${detail?.user.id ?? ''}`)">
        ← Back to user
      </button>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="loading" class="muted" style="padding: 8px 2px">Loading agent…</div>

    <template v-if="detail">
      <div class="topbar" style="margin-bottom: 8px">
        <div class="agent-head">
          <img
            v-if="detail.agent.avatar_url"
            :src="detail.agent.avatar_url"
            class="agent-avatar"
            :style="{ background: headerColor }"
            alt=""
          />
          <span v-else class="agent-avatar" :style="{ background: headerColor }">
            {{ detail.agent.avatar_emoji }}
          </span>
          <div class="agent-head-info">
            <h2>{{ detail.agent.name }}</h2>
            <span class="muted"
              >{{ detail.agent.description || 'No description' }} · owned by
              {{ detail.user.display_name }}</span
            >
          </div>
        </div>
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

      <!-- Configure (read-only, mirrors the dashboard ConfigureTab) -->
      <div v-if="activeTab === 'configure'">
        <div class="card">
          <h3 style="margin-top: 0">Personalization</h3>

          <div class="ro-field" style="margin-bottom: 16px">
            <div class="ro-label">Avatar</div>
            <div class="ro-value">
              <img
                v-if="detail.agent.avatar_url"
                :src="detail.agent.avatar_url"
                class="agent-avatar"
                :style="{ background: headerColor }"
                alt="Agent photo"
              />
              <span v-else class="agent-avatar" :style="{ background: headerColor }">{{
                detail.agent.avatar_emoji
              }}</span>
              <span class="muted" style="margin-left: 8px">
                {{ detail.agent.avatar_url ? 'Uploaded photo/logo' : 'Emoji avatar' }}
              </span>
            </div>
          </div>

          <div class="ro-grid">
            <div class="ro-field">
              <div class="ro-label">Agent name</div>
              <div class="ro-value">{{ detail.agent.name }}</div>
            </div>
            <div class="ro-field">
              <div class="ro-label">Welcome message</div>
              <div class="ro-value">{{ detail.agent.welcome_message }}</div>
            </div>
            <div class="ro-field ro-wide">
              <div class="ro-label">Description (shown to visitors under the bot name)</div>
              <div class="ro-value">{{ detail.agent.description || '—' }}</div>
            </div>
            <div class="ro-field ro-wide">
              <div class="ro-label">Agent personality (optional)</div>
              <div class="ro-value" style="margin-bottom: 4px">
                <span v-if="persona?.label" class="badge badge-ready">{{ persona.label }}</span>
                <span v-else class="muted">No persona template</span>
              </div>
              <div v-if="persona" class="ro-value ro-pre">{{ persona.prompt }}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <h3 style="margin-top: 0">Agent info</h3>
          <div class="ro-grid">
            <div class="ro-field">
              <div class="ro-label">Header color</div>
              <div class="ro-value">
                <span class="ro-swatch" :style="{ background: agentHeaderColor(detail.agent) }" />{{
                  agentHeaderColor(detail.agent)
                }}
              </div>
            </div>
            <div class="ro-field">
              <div class="ro-label">Display</div>
              <div class="ro-value">
                <span v-if="detail.agent.show_thinking" class="badge badge-ready">Thinking on</span>
                <span v-else class="badge">Thinking off</span>
                <span v-if="detail.agent.show_tools" class="badge badge-ready">Tools on</span>
                <span v-else class="badge">Tools off</span>
              </div>
            </div>
            <div class="ro-field">
              <div class="ro-label">Created / Updated</div>
              <div class="ro-value">
                {{ fmtDate(detail.agent.created_at) }} · {{ fmtDate(detail.agent.updated_at) }}
              </div>
            </div>
            <div class="ro-field ro-wide">
              <div class="ro-label">Public token</div>
              <div class="ro-value">
                <code style="word-break: break-all">{{ detail.agent.public_token }}</code>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Knowledge (read-only) -->
      <div v-else-if="activeTab === 'knowledge'">
        <div class="card">
          <div class="admin-list-head">
            <h3 style="margin: 0">Knowledge base ({{ sources.length }})</h3>
            <button class="btn btn-ghost btn-sm" :disabled="sourcesLoading" @click="loadSources">
              <span v-if="sourcesLoading" class="spinner" style="margin-right: 4px" /> Refresh
            </button>
          </div>

          <div v-if="sourcesLoading" class="muted" style="padding: 8px 2px">
            Loading sources…
          </div>
          <div v-else-if="sources.length" class="row-list">
            <div v-for="s in sources" :key="s.id" class="row">
              <div class="row-main">
                <div class="row-title">
                  <span v-if="s.kind === 'pdf'" class="kind-badge" title="PDF file">PDF</span>
                  <span v-else-if="s.kind === 'text'" class="kind-badge" title="Pasted text">TEXT</span>
                  <span v-else class="kind-badge" title="Web page">URL</span>
                  <template v-if="s.kind === 'text'">{{ s.title || 'Pasted text' }}</template>
                  <a v-else :href="s.url" target="_blank" rel="noopener noreferrer">{{
                    s.title || s.url
                  }}</a>
                </div>
                <div class="row-sub">
                  <span v-if="s.kind === 'pdf'">{{ s.file_name }}</span>
                  <span v-else-if="s.kind === 'text'"
                    >Pasted text<span v-if="s.chunk_count"> · {{ s.chunk_count }} chunks</span></span
                  >
                  <a v-else :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.url }}</a>
                  <span v-if="s.kind !== 'text' && s.chunk_count">
                    · {{ s.chunk_count }} chunks</span
                  >
                </div>
                <div v-if="s.error" class="row-sub" style="color: var(--danger)">{{ s.error }}</div>
              </div>
              <StatusBadge :status="s.status" />
            </div>
          </div>
          <p v-else class="muted" style="margin: 0">No sources yet.</p>
        </div>
      </div>

      <!-- Preview (read-only mirror of the dashboard preview: display config + real widget) -->
      <div v-else-if="activeTab === 'preview'">
        <div class="card chat-config" style="margin-bottom: 16px">
          <div class="chat-config-section">
            <div class="chat-config-title">Display</div>
            <div class="ro-value">
              <span v-if="detail.agent.show_thinking" class="badge badge-ready">Thinking on</span>
              <span v-else class="badge">Thinking off</span>
              <span v-if="detail.agent.show_tools" class="badge badge-ready">Tools on</span>
              <span v-else class="badge">Tools off</span>
            </div>
          </div>
          <div class="chat-config-section">
            <div class="chat-config-title">Theme</div>
            <div class="ro-value" style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap">
              <span class="theme-swatches">
                <span class="theme-swatch" :style="{ background: theme.headerBg }" />
                <span class="theme-swatch" :style="{ background: theme.msgsBg }" />
                <span class="theme-swatch" :style="{ background: theme.aiBubbleBg }" />
                <span class="theme-swatch" :style="{ background: theme.userBubbleBg }" />
              </span>
              <span>{{ themePresetName || 'Default' }}</span>
              <span v-if="themeCustomized" class="badge badge-ready">Customized</span>
            </div>
          </div>
        </div>
        <p class="preview-widget-hint">
          Chat preview = live widget (floating). Auto-opens on desktop; on mobile, tap the launcher
          at the bottom-right.
        </p>
        <div ref="widgetHost" class="preview-widget-host" />
      </div>

      <!-- Usage -->
      <div v-else-if="activeTab === 'usage'">
        <div class="usage-tab">
          <template v-if="usage">
            <div class="usage-summary">
              <div class="usage-stat">
                <div class="usage-stat-value">{{ usage.summary.total_requests }}</div>
                <div class="usage-stat-label">Requests</div>
              </div>
              <div class="usage-stat">
                <div class="usage-stat-value">{{ formatCompact(usage.summary.total_input_tokens) }}</div>
                <div class="usage-stat-label">Input tokens</div>
              </div>
              <div class="usage-stat">
                <div class="usage-stat-value">{{ formatCompact(usage.summary.total_output_tokens) }}</div>
                <div class="usage-stat-label">Output tokens</div>
              </div>
              <div class="usage-stat">
                <div class="usage-stat-value">{{ formatCompact(usage.summary.total_tokens) }}</div>
                <div class="usage-stat-label">Total tokens</div>
              </div>
            </div>

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

            <!-- top countries (parity with the dashboard Usage tab) -->
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

            <div class="card usage-history">
              <h3 style="margin: 0 0 12px">Usage history</h3>
              <p v-if="!hasUsage" class="muted" style="margin: 0">No usage yet.</p>
              <template v-else>
                <div class="usage-table-scroll">
                  <table class="usage-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Channel</th>
                        <th>Page</th>
                        <th>Model</th>
                        <th class="num">Input</th>
                        <th class="num">Output</th>
                        <th class="num">Total</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="item in usage.items" :key="item.id">
                        <td class="admin-date">{{ fmtDate(item.created_at) }}</td>
                        <td>{{ channelLabel(item.channel) }}</td>
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
                  <span class="muted">Page {{ usage.page }} of {{ usage.pages }}</span>
                  <button
                    class="btn btn-ghost btn-sm"
                    :disabled="page >= usage.pages"
                    @click="goPage(page + 1)"
                  >
                    Next →
                  </button>
                </div>
              </template>
            </div>
          </template>
        </div>
      </div>

      <!-- Embed (read-only) -->
      <div v-else class="card">
        <h3 style="margin-top: 0">Embed snippet</h3>
        <p class="muted">The snippet this agent embeds on websites (read-only).</p>
        <pre class="code-block" data-testid="admin-embed-code">{{ embedHtml || 'Loading…' }}</pre>
        <div style="display: flex; gap: 10px; flex-wrap: wrap">
          <button class="btn" :disabled="!embedHtml" @click="copySnippet">
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
          <li>
            <code>data-token</code> — secret key that authenticates the widget (keep it
            private).
          </li>
          <li><code>data-base-url</code> — where the widget script + API live.</li>
        </ul>
        <p class="muted" style="font-size: 12px; margin-bottom: 0">
          React / Vue SDKs are planned. For now the snippet works on any plain HTML page.
        </p>
      </div>
    </template>
  </div>
</template>
