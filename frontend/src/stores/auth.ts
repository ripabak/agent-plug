/** Auth store: token + user, persisted in localStorage, restored via /me. */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api/client'
import type { User } from '@/api/types'

const TOKEN_KEY = 'ap_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) ?? '')
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => Boolean(token.value))

  function persist(t: string) {
    token.value = t
    localStorage.setItem(TOKEN_KEY, t)
  }

  async function login(email: string, password: string) {
    const res = await api.login({ email, password })
    persist(res.access_token)
    user.value = res.user
  }

  async function register(data: { email: string; display_name: string; password: string }) {
    const res = await api.register(data)
    persist(res.access_token)
    user.value = res.user
  }

  /** Restore the session on app load (if a token exists). */
  async function bootstrap() {
    if (!token.value) return
    try {
      user.value = await api.me(token.value)
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  return { token, user, isAuthenticated, login, register, bootstrap, logout }
})
