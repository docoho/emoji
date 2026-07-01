import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { fetchCurrentUser } from '../services/api'

const RegisterView = () => import('../views/RegisterView.vue')
const ForgotPasswordView = () => import('../views/ForgotPasswordView.vue')
const ResetPasswordView = () => import('../views/ResetPasswordView.vue')
const OAuthCallbackView = () => import('../views/OAuthCallbackView.vue')
const UserProfileView = () => import('../views/UserProfileView.vue')
const CreatorDashboardView = () => import('../views/CreatorDashboardView.vue')
const CollectionsIndexView = () => import('../views/CollectionsIndexView.vue')
const CollectionsNewView = () => import('../views/CollectionsNewView.vue')
const CollectionDetailView = () => import('../views/CollectionDetailView.vue')
const CollectionEditView = () => import('../views/CollectionEditView.vue')
const AdminDashboardView = () => import('../views/AdminDashboardView.vue')
const AdminModerationView = () => import('../views/AdminModerationView.vue')

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: ForgotPasswordView,
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: ResetPasswordView,
  },
  {
    path: '/auth/google/callback',
    name: 'oauth-google-callback',
    component: OAuthCallbackView,
  },
  {
    path: '/creator',
    name: 'creator-dashboard',
    component: CreatorDashboardView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/collections',
    name: 'collections-index',
    component: CollectionsIndexView,
  },
  {
    path: '/collections/new',
    name: 'collections-new',
    component: CollectionsNewView,
  },
  {
    path: '/collections/:id',
    name: 'collection-detail',
    component: CollectionDetailView,
  },
  {
    path: '/collections/:id/edit',
    name: 'collection-edit',
    component: CollectionEditView,
  },
  {
    path: '/users/:id',
    name: 'user-profile',
    component: UserProfileView,
  },
  {
    path: '/admin',
    name: 'admin-dashboard',
    component: AdminDashboardView,
    meta: {
      requiresAuth: true,
      requiresSuperuser: true,
    },
  },
  {
    path: '/admin/moderation',
    name: 'admin-moderation',
    component: AdminModerationView,
    meta: {
      requiresAuth: true,
      requiresSuperuser: true,
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

async function resolveCurrentUser() {
  const { token, user, setSession } = useAuth()
  if (user.value) return user.value
  if (!token.value) return null
  const profile = await fetchCurrentUser(token.value)
  if (profile) {
    setSession({ token: token.value, user: profile })
  }
  return profile
}

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth && !sessionStorage.getItem('auth_token')) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.meta.requiresSuperuser) {
    const currentUser = await resolveCurrentUser()
    const { addToast } = useToast()

    if (currentUser && currentUser.is_superuser) {
      return true
    }

    if (currentUser) {
      addToast('You do not have access to that page.', 'error')
      return { name: 'home' }
    }

    useAuth().signOut()
    addToast('Your session has expired. Please sign in again.', 'error')
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  return true
})

export default router
