/** Admin store: token + email for the env-configured platform admin.

The admin is a SEPARATE principal from regular users (login via
ADMIN_EMAIL/ADMIN_PASSWORD in env), so it gets its own localStorage key and
is never mixed with the user auth store.
*/
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api/client'

const ADMIN_TOKEN_KEY = 'ap_admin_token'

export const useAdminStore = defineStore('admin', () => {
  const token = ref(localStorage.getItem(ADMIN_TOKEN_KEY) ?? '')
  const email = ref('')

  const isAuthenticated = computed(() => Boolean(token.value))

  async function login(emailIn: string, password: string) {
    const res = await api.adminLogin({ email: emailIn, password })
    token.value = res.access_token
    email.value = res.email
    localStorage.setItem(ADMIN_TOKEN_KEY, res.access_token)
  }

  /** Restore the admin session on app load (if an admin token exists). */
  async function bootstrap() {
    if (!token.value) return
    try {
      const res = await api.adminMe(token.value)
      email.value = res.email
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    email.value = ''
    localStorage.removeItem(ADMIN_TOKEN_KEY)
  }

  return { token, email, isAuthenticated, login, bootstrap, logout }
})
