<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentsStore } from '@/stores/agents'
import { validateAvatarFile } from '@/utils/avatar'
import { AVATAR_TEMPLATES, type AvatarTemplate } from '@/utils/avatarTemplates'
import AvatarPicker from './AvatarPicker.vue'
import { PERSONA_TEMPLATES, findPersonaTemplate, type PersonaTemplate } from '@/utils/personaTemplates'

const agentsStore = useAgentsStore()
const router = useRouter()

const form = reactive({
  name: '',
  description: '',
  persona_prompt: '',
  welcome_message: '',
  avatar_emoji: '🤖',
})

/** Id of the template currently filling the persona textarea ('' = custom). */
const personaTemplateId = ref('')

const saved = ref(false)
const error = ref('')
const busy = ref(false)
const deleting = ref(false)

const photoBusy = ref(false)
const photoError = ref('')
const photoSaved = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

/** True when a photo/logo is uploaded — emoji picking is disabled until removed. */
const hasPhoto = computed(() => !!agentsStore.current?.avatar_url)

async function pickPhoto(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // allow re-picking the same file
  if (!file) return
  photoError.value = ''
  const check = validateAvatarFile(file)
  if (!check.ok) {
    photoError.value = check.error ?? 'Invalid image'
    return
  }
  photoBusy.value = true
  try {
    await agentsStore.uploadAvatar(file, 'photo')
    photoSaved.value = true
    setTimeout(() => (photoSaved.value = false), 2000)
  } catch (err) {
    photoError.value = err instanceof Error ? err.message : 'Upload failed'
  } finally {
    photoBusy.value = false
  }
}

async function removePhoto() {
  if (!confirm('Remove the uploaded photo? The avatar will fall back to the emoji.')) return
  photoError.value = ''
  photoBusy.value = true
  try {
    await agentsStore.removeAvatar()
  } catch (err) {
    photoError.value = err instanceof Error ? err.message : 'Failed to remove photo'
  } finally {
    photoBusy.value = false
  }
}

/** Apply a bundled GIF template: fetch it and upload through the normal pipeline. */
async function pickTemplate(t: AvatarTemplate) {
  photoError.value = ''
  photoBusy.value = true
  try {
    const res = await fetch(t.url)
    if (!res.ok) throw new Error(`Failed to load template (${res.status})`)
    const blob = await res.blob()
    const file = new File([blob], `${t.id}.gif`, { type: 'image/gif' })
    await agentsStore.uploadAvatar(file, 'template')
    photoSaved.value = true
    setTimeout(() => (photoSaved.value = false), 2000)
  } catch (err) {
    photoError.value = err instanceof Error ? err.message : 'Failed to apply template'
  } finally {
    photoBusy.value = false
  }
}

function syncForm() {
  const a = agentsStore.current
  if (!a) return
  form.name = a.name
  form.description = a.description
  form.persona_prompt = a.persona_prompt ?? ''
  personaTemplateId.value = findPersonaTemplate(a.persona_prompt)?.id ?? ''
  form.welcome_message = a.welcome_message
  form.avatar_emoji = a.avatar_emoji
}

/** Fill the persona textarea with a template (additive, editable). */
function selectPersonaTemplate(t: PersonaTemplate) {
  form.persona_prompt = t.prompt
  personaTemplateId.value = t.id
}

watch(() => agentsStore.current, syncForm, { immediate: true })

async function save() {
  error.value = ''
  busy.value = true
  try {
    await agentsStore.update({ ...form, persona_prompt: form.persona_prompt || null })
    saved.value = true
    setTimeout(() => (saved.value = false), 2000)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save'
  } finally {
    busy.value = false
  }
}

async function regenerateToken() {
  if (
    !confirm(
      'Regenerate the public token? Existing embed snippets will stop working until updated.',
    )
  )
    return
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
      <label for="c-persona">Agent personality <span class="muted">(optional)</span></label>
      <p class="muted" style="font-size: 12px; margin: 0 0 8px">
        Pick a persona template or write your own. It is added on top of the default
        instructions — it never replaces them. Leave it empty for the default tone.
      </p>
      <div class="persona-templates">
        <button
          v-for="t in PERSONA_TEMPLATES"
          :key="t.id"
          type="button"
          class="persona-template"
          :class="{ active: personaTemplateId === t.id }"
          :title="t.prompt"
          @click="selectPersonaTemplate(t)"
        >
          <span class="persona-emoji">{{ t.emoji }}</span>
          <span class="persona-label">{{ t.label }}</span>
          <span class="persona-desc">{{ t.description }}</span>
        </button>
      </div>
      <textarea
        id="c-persona"
        v-model="form.persona_prompt"
        rows="5"
        placeholder="e.g. Be very casual, use emojis, and keep it short…"
        @input="personaTemplateId = ''"
      />
    </div>
    <div class="form-group">
      <label>Avatar — an emoji <em>or</em> an uploaded photo/logo</label>
      <div style="display: flex; align-items: center; gap: 14px">
        <img
          v-if="hasPhoto"
          :src="agentsStore.current?.avatar_url ?? undefined"
          class="agent-avatar"
          alt="Agent photo"
        />
        <span v-else class="agent-avatar" style="background: #4f46e522">{{
          form.avatar_emoji
        }}</span>
        <div style="display: flex; gap: 8px; flex-wrap: wrap">
          <input
            ref="fileInput"
            type="file"
            accept="image/gif,image/jpeg,image/png,image/webp"
            hidden
            @change="pickPhoto"
          />
          <button
            class="btn btn-secondary btn-sm"
            :disabled="photoBusy"
            @click="fileInput?.click()"
          >
            <span v-if="photoBusy" class="spinner" />
            {{ hasPhoto ? 'Replace photo' : 'Upload photo' }}
          </button>
          <button
            v-if="hasPhoto"
            class="btn btn-danger btn-sm"
            :disabled="photoBusy"
            @click="removePhoto"
          >
            Remove photo
          </button>
          <span v-if="photoSaved" style="color: #d1fae5">✓</span>
        </div>
      </div>
      <p v-if="photoError" class="error-box" style="margin: 8px 0 0">{{ photoError }}</p>
      <p v-else class="muted" style="font-size: 12px; margin: 6px 0 0">
        {{
          hasPhoto
            ? 'Emoji picker below is disabled while a photo is set — remove the photo to pick an emoji again.'
            : 'Supported: GIF, PNG, JPG (or WebP) · max 5 MB. Transparent PNG/GIF keep their transparency and animated GIFs stay animated; images are compressed and resized automatically.'
        }}
      </p>
    </div>
    <div class="form-group">
      <label>Or pick a GIF template</label>
      <div class="avatar-templates">
        <button
          v-for="t in AVATAR_TEMPLATES"
          :key="t.id"
          type="button"
          class="avatar-template"
          :title="t.label"
          :disabled="photoBusy"
          @click="pickTemplate(t)"
        >
          <img :src="t.url" :alt="t.label" />
        </button>
      </div>
      <p class="muted" style="font-size: 12px; margin: 6px 0 0">
        Animated avatars — click one to apply it (replaces the current photo, if any).
      </p>
    </div>
    <div class="form-group">
      <label>Avatar emoji</label>
      <AvatarPicker v-model="form.avatar_emoji" :disabled="hasPhoto" />
    </div>
    <button class="btn" :disabled="busy || !form.name.trim()" @click="save">
      <span v-if="busy" class="spinner" /> Save changes
      <span v-if="saved" style="color: #d1fae5">✓</span>
    </button>

    <hr style="border: none; border-top: 1px solid var(--border); margin: 20px 0" />

    <h3 style="margin-top: 0">Danger zone</h3>
    <div style="display: flex; gap: 10px; flex-wrap: wrap">
      <button class="btn btn-secondary btn-sm" @click="regenerateToken">
        Regenerate public token
      </button>
      <button class="btn btn-danger btn-sm" :disabled="deleting" @click="removeAgent">
        <span v-if="deleting" class="spinner" /> Delete agent
      </button>
    </div>
    <p class="muted" style="margin-bottom: 0; margin-top: 10px; font-size: 12px">
      Public token:
      <code style="word-break: break-all">{{ agentsStore.current?.public_token }}</code>
    </p>
  </div>
</template>
