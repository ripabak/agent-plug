<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import PlugMark from '@/components/PlugMark.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await auth.login(email.value, password.value)
    router.push((route.query.redirect as string) || '/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Login failed'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page page-narrow">
    <div class="topbar">
      <RouterLink to="/" class="brand"
        ><span class="logo-mark"><PlugMark :size="17" /></span> Agent-Plug</RouterLink
      >
    </div>
    <div class="card">
      <h1 style="margin-top: 0">Welcome back</h1>
      <p class="muted">Log in to manage your agents.</p>
      <div v-if="error" class="error-box">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" autocomplete="email" required />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
          />
        </div>
        <button class="btn btn-block" type="submit" :disabled="busy">
          <span v-if="busy" class="spinner" /> Log in
        </button>
      </form>
      <p class="muted" style="margin-bottom: 0">
        No account yet? <RouterLink to="/register">Create one</RouterLink>
      </p>
    </div>
  </div>
</template>
