import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { auth: true },
    },
    {
      path: '/agents/new',
      name: 'agent-create',
      component: () => import('@/views/AgentCreateView.vue'),
      meta: { auth: true },
    },
    {
      path: '/agents/:id',
      name: 'agent-detail',
      component: () => import('@/views/AgentDetailView.vue'),
      meta: { auth: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.user && auth.isAuthenticated) await auth.bootstrap()
  if (to.meta.auth && !auth.isAuthenticated)
    return { name: 'login', query: { redirect: to.fullPath } }
  if (to.meta.guest && auth.isAuthenticated) return { name: 'dashboard' }
  return true
})

export default router
