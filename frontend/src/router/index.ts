import { createRouter, createWebHistory } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/LandingView.vue'),
    },
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
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('@/views/AdminLoginView.vue'),
      meta: { adminGuest: true },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { admin: true },
    },
    {
      path: '/admin/users/:id',
      name: 'admin-user',
      component: () => import('@/views/AdminUserView.vue'),
      meta: { admin: true },
    },
    {
      path: '/admin/agents/:id',
      name: 'admin-agent',
      component: () => import('@/views/AdminAgentDetailView.vue'),
      meta: { admin: true },
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
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const admin = useAdminStore()
  if (!auth.user && auth.isAuthenticated) await auth.bootstrap()
  if (admin.isAuthenticated && !admin.email) await admin.bootstrap()
  if (to.meta.admin && !admin.isAuthenticated)
    return { name: 'admin-login', query: { redirect: to.fullPath } }
  if (to.meta.adminGuest && admin.isAuthenticated) return { name: 'admin' }
  if (to.meta.auth && !auth.isAuthenticated)
    return { name: 'login', query: { redirect: to.fullPath } }
  if (to.meta.guest && auth.isAuthenticated) return { name: 'dashboard' }
  return true
})

export default router
