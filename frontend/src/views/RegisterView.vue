<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await auth.register({ display_name: name.value, email: email.value, password: password.value })
    router.push('/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Registration failed'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page page-narrow">
    <div class="topbar">
      <RouterLink to="/" class="brand"><span class="logo-mark">🤖</span> Agent-Plug</RouterLink>
    </div>
    <div class="card">
      <h1 style="margin-top: 0">Create your account</h1>
      <p class="muted">Start building an AI agent your website visitors can talk to.</p>
      <div v-if="error" class="error-box">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label for="name">Display name</label>
          <input id="name" v-model="name" type="text" autocomplete="name" required />
        </div>
        <div class="form-group">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" autocomplete="email" required />
        </div>
        <div class="form-group">
          <label for="password">Password (min 6 chars)</label>
          <input id="password" v-model="password" type="password" autocomplete="new-password" required minlength="6" />
        </div>
        <button class="btn btn-block" type="submit" :disabled="busy">
          <span v-if="busy" class="spinner" /> Sign up
        </button>
      </form>
      <p class="muted" style="margin-bottom: 0">
        Already have an account? <RouterLink to="/login">Log in</RouterLink>
      </p>
    </div>
  </div>
</template>
