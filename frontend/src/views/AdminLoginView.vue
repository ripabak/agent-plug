<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlugMark from '@/components/PlugMark.vue'
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()
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
    await admin.login(email.value, password.value)
    router.push((route.query.redirect as string) || '/admin')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Admin login failed'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page page-narrow">
    <div class="topbar">
      <RouterLink to="/" class="brand"
        ><span class="logo-mark"><PlugMark :size="17" /></span> Agent-Plug
        <span class="badge badge-admin">Admin</span></RouterLink
      >
    </div>
    <div class="card">
      <h1 style="margin-top: 0">Admin console</h1>
      <p class="muted">
        Sign in with admin credentials
      </p>
      <div v-if="error" class="error-box">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label for="admin-email">Email</label>
          <input id="admin-email" v-model="email" type="email" autocomplete="email" required />
        </div>
        <div class="form-group">
          <label for="admin-password">Password</label>
          <input
            id="admin-password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
          />
        </div>
        <button class="btn btn-block" type="submit" :disabled="busy">
          <span v-if="busy" class="spinner" /> Sign in as admin
        </button>
      </form>
      <p class="muted" style="margin-bottom: 0">
        Just a regular user? <RouterLink to="/login">Log in here</RouterLink>
      </p>
    </div>
  </div>
</template>
