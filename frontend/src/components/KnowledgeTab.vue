<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useAgentsStore } from '@/stores/agents'
import type { SourceStatus } from '@/api/types'
import { RUNNING_SOURCE_STATUSES } from '@/api/types'
import StatusBadge from './StatusBadge.vue'

const agentsStore = useAgentsStore()
const auth = useAuthStore()
const agentId = computed(() => agentsStore.current?.id ?? 0)

const urlsText = ref('')
const busy = ref(false)
const error = ref('')
const notice = ref('')
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
  await agentsStore.deleteSource(agentId.value, sourceId)
}

// ---- PDF replace (PUT /sources/{id}/file — same key, re-indexed) ----
const replaceInput = ref<HTMLInputElement | null>(null)
const replacingId = ref<number | null>(null)
const replacing = ref(false)

function startReplace(sourceId: number) {
  if (replacing.value) return
  replacingId.value = sourceId
  replaceInput.value?.click()
}

async function onReplaceChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  const sourceId = replacingId.value
  if (sourceId === null) return
  input.value = ''
  replacingId.value = null
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    error.value = 'Only .pdf files are supported.'
    return
  }
  replacing.value = true
  error.value = ''
  notice.value = ''
  try {
    const updated = await api.replaceSourceFile(auth.token, agentId.value, sourceId, file)
    notice.value = `Replaced ${updated.file_name} — re-indexing started.`
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Replace failed'
  } finally {
    replacing.value = false
  }
}

async function reindex(onlyFailed = false) {
  notice.value = 'Re-indexing… statuses update automatically.'
  await agentsStore.reindex(agentId.value, onlyFailed)
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
    await api.addTextSource(auth.token, agentId.value, {
      title: textTitle.value.trim() || 'Pasted text',
      content,
    })
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

      <!-- input mode switcher -->
      <div class="source-modes">
        <button class="source-mode" :class="{ active: inputMode === 'url' }" @click="inputMode = 'url'">🌐 URLs</button>
        <button class="source-mode" :class="{ active: inputMode === 'pdf' }" @click="inputMode = 'pdf'">📄 PDF</button>
        <button class="source-mode" :class="{ active: inputMode === 'text' }" @click="inputMode = 'text'">📝 Text</button>
      </div>

      <!-- URLs mode -->
      <template v-if="inputMode === 'url'">
        <p class="muted" style="margin-top: 0">
          Paste one URL per line. Agent-Plug will fetch each page, clean the HTML, and index it so
          the agent can answer from it.
        </p>
        <textarea v-model="urlsText" rows="4" placeholder="https://example.com/docs&#10;https://example.com/pricing" />
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
          <div class="upload-zone-icon">📄</div>
          <div>
            <strong>{{ uploading ? 'Uploading…' : 'Upload PDFs' }}</strong>
            <div class="muted" style="font-size: 12px">
              Click to choose or drag &amp; drop (up to 5 files, 10MB each)
            </div>
          </div>
          <input ref="fileInput" type="file" accept=".pdf,application/pdf" multiple hidden @change="onFileChange" />
          <input ref="replaceInput" type="file" accept=".pdf,application/pdf" hidden @change="onReplaceChange" />
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
          <textarea id="text-content" v-model="textContent" rows="8" placeholder="Paste your content here…" />
        </div>
        <button class="btn" :disabled="busy || textContent.trim().length < 10" @click="addText">
          <span v-if="busy" class="spinner" /> Add text
        </button>
      </template>

      <div style="margin-top: 12px">
        <button class="btn btn-secondary btn-sm" :disabled="agentsStore.sources.length === 0" @click="reindex(false)">
          Re-index all
        </button>
      </div>
    </div>

    <div class="card" v-if="agentsStore.sources.length">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px">
        <h3 style="margin: 0">Sources ({{ agentsStore.sources.length }})</h3>
        <button class="btn btn-ghost btn-sm" :disabled="!hasRunning" @click="load">
          <span v-if="hasRunning" class="spinner" style="margin-right: 4px" /> Refresh
        </button>
      </div>

      <div class="row-list">
        <div v-for="s in agentsStore.sources" :key="s.id" class="row">
          <div class="row-main">
            <div class="row-title">
              <span v-if="s.kind === 'pdf'" class="kind-badge" title="PDF file">📄 PDF</span>
              <span v-else-if="s.kind === 'text'" class="kind-badge" title="Pasted text">📝 TEXT</span>
              <span v-else class="kind-badge" title="Web page">🌐 URL</span>
              {{ s.title || (s.kind === 'pdf' ? s.file_name : s.url) }}
            </div>
            <div class="row-sub">
              <span v-if="s.kind === 'pdf'">{{ s.file_name }}<span v-if="s.file_size"> · {{ (s.file_size / 1024).toFixed(0) }} KB</span></span>
              <span v-else-if="s.kind === 'text'">Pasted text<span v-if="s.chunk_count"> · {{ s.chunk_count }} chunks</span></span>
              <a v-else :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.url }}</a>
              <span v-if="s.kind !== 'text' && s.chunk_count"> · {{ s.chunk_count }} chunks</span>
            </div>
            <div v-if="s.error" class="row-sub" style="color: var(--danger)">{{ s.error }}</div>
          </div>
          <StatusBadge :status="statusOf(s)" />
          <button v-if="s.kind === 'pdf'" class="btn btn-ghost btn-sm" :disabled="replacing" @click="startReplace(s.id)">
            <span v-if="replacing && replacingId === s.id" class="spinner" style="margin-right: 4px" />
            {{ replacing && replacingId === s.id ? 'Replacing…' : 'Replace' }}
          </button>
          <button class="btn btn-ghost btn-sm" @click="removeSource(s.id)">Remove</button>
        </div>
      </div>

      <button v-if="agentsStore.sources.some((s) => s.status === 'failed')" class="btn btn-secondary btn-sm" style="margin-top: 12px" @click="reindex(true)">
        Retry failed
      </button>
    </div>

    <div v-else class="card empty-state">
      <div class="emoji">📚</div>
      <div>No sources yet. Add URLs above to give your agent knowledge.</div>
    </div>
  </div>
</template>
