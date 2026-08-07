<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useAgentsStore } from '@/stores/agents'
import type { Source, SourceStatus } from '@/api/types'
import { RUNNING_SOURCE_STATUSES } from '@/api/types'
import StatusBadge from './StatusBadge.vue'

const agentsStore = useAgentsStore()
const auth = useAuthStore()
const agentId = computed(() => agentsStore.current?.id ?? 0)

const urlsText = ref('')
const busy = ref(false)
const error = ref('')
const notice = ref('')
const refreshing = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

const hasRunning = computed(() =>
  agentsStore.sources.some((s) => RUNNING_SOURCE_STATUSES.includes(s.status)),
)

async function load() {
  if (!agentId.value) return
  try {
    await agentsStore.fetchSources(agentId.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load sources'
  }
}

/** Manual refresh — always clickable (unlike the old `:disabled="!hasRunning"`
 *  gate, which froze the button once all sources were idle/ready) and shows
 *  busy feedback on the button itself. */
async function refresh() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await agentsStore.fetchSources(agentId.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load sources'
  } finally {
    refreshing.value = false
  }
}

function parseUrls(text: string): string[] {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
}

async function addUrls() {
  const urls = parseUrls(urlsText.value)
  if (!urls.length) return
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    const created = await agentsStore.addSources(agentId.value, urls)
    urlsText.value = ''
    notice.value = created.length
      ? `Added ${created.length} URL(s) — indexing started. You can keep this page open; statuses update automatically.`
      : 'Those URLs are already in this agent.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to add URLs'
  } finally {
    busy.value = false
  }
}

// ---- PDF upload ----
const fileInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const uploading = ref(false)
const openingPdf = ref(false)

function pickFiles() {
  fileInput.value?.click()
}

async function uploadFiles(files: FileList | File[]) {
  const list = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.pdf'))
  if (!list.length) {
    error.value = 'Only .pdf files are supported.'
    return
  }
  uploading.value = true
  error.value = ''
  notice.value = ''
  try {
    const created = await api.uploadSourceFiles(auth.token, agentId.value, list)
    agentsStore.prependSources(created)
    notice.value = `Uploaded ${created.length} PDF(s) — indexing started.`
    if (fileInput.value) fileInput.value.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Upload failed'
  } finally {
    uploading.value = false
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) uploadFiles(input.files)
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files.length) uploadFiles(e.dataTransfer.files)
}

async function removeSource(sourceId: number) {
  if (!confirm('Remove this source from the knowledge base?')) return
  error.value = ''
  try {
    await agentsStore.deleteSource(agentId.value, sourceId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to remove source'
  }
}

/** Open an uploaded PDF in a new tab (fetched with the auth header as a blob). */
async function openPdf(s: Source) {
  if (openingPdf.value) return
  openingPdf.value = true
  error.value = ''
  try {
    const blob = await api.getSourceFile(auth.token, agentId.value, s.id)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to open document'
  } finally {
    openingPdf.value = false
  }
}

async function reindex(onlyFailed = false) {
  error.value = ''
  // Optimistically mark the affected sources as pending ("Queued") before the
  // request goes out: hasRunning is derived from this local list, so this keeps
  // the 3s status poll running and the list reflects the job immediately — no
  // manual Refresh needed while the backend re-indexes.
  for (const s of agentsStore.sources) {
    if (!onlyFailed || s.status === 'failed') s.status = 'pending'
  }
  notice.value = 'Re-indexing… statuses update automatically.'
  try {
    await agentsStore.reindex(agentId.value, onlyFailed)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Re-index failed'
  }
  await load() // backend re-index runs inline — fetch the final statuses
}

onMounted(() => {
  load()
  pollTimer = setInterval(() => {
    if (hasRunning.value || agentsStore.sources.length === 0) load()
  }, 3000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const statusOf = (s: { status: SourceStatus }) => s.status

// ---- input mode (URLs | PDF | Text) ----
const inputMode = ref<'url' | 'pdf' | 'text'>('url')
const textTitle = ref('')
const textContent = ref('')

async function addText() {
  const content = textContent.value.trim()
  if (content.length < 10) {
    error.value = 'Text is too short (min 10 characters).'
    return
  }
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    const created = await api.addTextSource(auth.token, agentId.value, {
      title: textTitle.value.trim() || 'Pasted text',
      content,
    })
    agentsStore.prependSources(created)
    textContent.value = ''
    textTitle.value = ''
    notice.value = 'Text added — indexing started.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to add text'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div>
    <div class="card">
      <h3 style="margin-top: 0">Add knowledge sources</h3>
      <div v-if="error" class="error-box">{{ error }}</div>
      <div v-if="notice" class="hint">{{ notice }}</div>

      <div class="source-modes">
        <button
          class="source-mode"
          :class="{ active: inputMode === 'url' }"
          @click="inputMode = 'url'"
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
            style="vertical-align: -2px; margin-right: 5px"
          >
            <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4" />
            <path
              d="M2.5 8h11M8 2c2 1.6 3 3.6 3 6s-1 4.4-3 6c-2-1.6-3-3.6-3-6s1-4.4 3-6Z"
              stroke="currentColor"
              stroke-width="1.4"
            />
          </svg>
          URLs
        </button>
        <button
          class="source-mode"
          :class="{ active: inputMode === 'pdf' }"
          @click="inputMode = 'pdf'"
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
            style="vertical-align: -2px; margin-right: 5px"
          >
            <path
              d="M3 2.5h6l4 4v7H3v-11Z"
              stroke="currentColor"
              stroke-width="1.4"
              stroke-linejoin="round"
            />
            <path
              d="M9 2.5v4h4M5 8.5h6M5 11h4"
              stroke="currentColor"
              stroke-width="1.4"
              stroke-linecap="round"
            />
          </svg>
          PDF
        </button>
        <button
          class="source-mode"
          :class="{ active: inputMode === 'text' }"
          @click="inputMode = 'text'"
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
            style="vertical-align: -2px; margin-right: 5px"
          >
            <path
              d="M3 3h10M3 6.5h10M3 10h7M3 13h5"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
          Text
        </button>
      </div>

      <!-- URLs mode -->
      <template v-if="inputMode === 'url'">
        <p class="muted" style="margin-top: 0">
          Paste one URL per line. Agent-Plug will fetch each page, clean the HTML, and index it so
          the agent can answer from it.
        </p>
        <textarea
          v-model="urlsText"
          rows="4"
          placeholder="https://example.com/docs&#10;https://example.com/pricing"
        />
        <div style="margin-top: 10px">
          <button class="btn" :disabled="busy || !urlsText.trim()" @click="addUrls">
            <span v-if="busy" class="spinner" /> Add & index
          </button>
        </div>
      </template>

      <!-- PDF mode -->
      <template v-if="inputMode === 'pdf'">
        <div
          class="upload-zone"
          :class="{ 'drag-over': dragOver }"
          @click="pickFiles"
          @dragover.prevent="dragOver = true"
          @dragleave="dragOver = false"
          @drop.prevent="onDrop"
        >
          <div class="upload-zone-icon">
            <svg width="26" height="26" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M3 2.5h6l4 4v7H3v-11Z"
                stroke="currentColor"
                stroke-width="1.4"
                stroke-linejoin="round"
              />
              <path
                d="M9 2.5v4h4M5 8.5h6M5 11h4"
                stroke="currentColor"
                stroke-width="1.4"
                stroke-linecap="round"
              />
            </svg>
          </div>
          <div>
            <strong>{{ uploading ? 'Uploading…' : 'Upload PDFs' }}</strong>
            <div class="muted" style="font-size: 12px">
              Click to choose or drag &amp; drop (up to 5 files, 10MB each)
            </div>
          </div>
          <input
            ref="fileInput"
            type="file"
            accept=".pdf,application/pdf"
            multiple
            hidden
            @change="onFileChange"
          />
        </div>
      </template>

      <!-- Text mode -->
      <template v-if="inputMode === 'text'">
        <p class="muted" style="margin-top: 0">
          Paste long-form text (docs, notes, policies…). It will be chunked and indexed like any
          other source.
        </p>
        <div class="form-group">
          <label for="text-title">Title</label>
          <input id="text-title" v-model="textTitle" type="text" placeholder="e.g. FAQ internal" />
        </div>
        <div class="form-group">
          <label for="text-content">Content (min 10 characters)</label>
          <textarea
            id="text-content"
            v-model="textContent"
            rows="8"
            placeholder="Paste your content here…"
          />
        </div>
        <button class="btn" :disabled="busy || textContent.trim().length < 10" @click="addText">
          <span v-if="busy" class="spinner" /> Add text
        </button>
      </template>

      <div style="margin-top: 12px">
        <button
          class="btn btn-secondary btn-sm"
          :disabled="agentsStore.sources.length === 0"
          @click="reindex(false)"
        >
          Re-index all
        </button>
      </div>
    </div>

    <div class="card" v-if="agentsStore.sources.length">
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        "
      >
        <h3 style="margin: 0">Sources ({{ agentsStore.sources.length }})</h3>
        <button
          class="btn btn-ghost btn-sm"
          :disabled="refreshing"
          :title="refreshing ? 'Refreshing…' : 'Reload the source list'"
          @click="refresh"
        >
          <span v-if="refreshing" class="spinner" style="margin-right: 4px" /> Refresh
        </button>
      </div>

      <div class="row-list">
        <div v-for="s in agentsStore.sources" :key="s.id" class="row">
          <div class="row-main">
            <div class="row-title">
              <span v-if="s.kind === 'pdf'" class="kind-badge" title="PDF file">PDF</span>
              <span v-else-if="s.kind === 'text'" class="kind-badge" title="Pasted text">TEXT</span>
              <span v-else class="kind-badge" title="Web page">URL</span>
              <a
                v-if="s.kind === 'pdf'"
                class="doc-link"
                :title="'Open ' + (s.file_name || 'document')"
                @click.prevent="openPdf(s)"
              >
                {{ s.title || s.file_name }} ↗
              </a>
              <template v-else-if="s.kind === 'text'">{{ s.title || 'Pasted text' }}</template>
              <a v-else :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.url }}</a>
            </div>
            <div class="row-sub">
              <span v-if="s.kind === 'pdf'"
                >{{ s.file_name
                }}<span v-if="s.file_size"> · {{ (s.file_size / 1024).toFixed(0) }} KB</span></span
              >
              <span v-else-if="s.kind === 'text'"
                >Pasted text<span v-if="s.chunk_count"> · {{ s.chunk_count }} chunks</span></span
              >
              <a v-else :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.url }}</a>
              <span v-if="s.kind !== 'text' && s.chunk_count"> · {{ s.chunk_count }} chunks</span>
            </div>
            <div v-if="s.error" class="row-sub" style="color: var(--danger)">{{ s.error }}</div>
          </div>
          <StatusBadge :status="statusOf(s)" />
          <button class="btn btn-ghost btn-sm" @click="removeSource(s.id)">Remove</button>
        </div>
      </div>

      <button
        v-if="agentsStore.sources.some((s) => s.status === 'failed')"
        class="btn btn-secondary btn-sm"
        style="margin-top: 12px"
        @click="reindex(true)"
      >
        Retry failed
      </button>
    </div>

    <div v-else class="card empty-state">
      <div class="emoji">📚</div>
      <div>No sources yet. Add URLs above to give your agent knowledge.</div>
    </div>
  </div>
</template>
