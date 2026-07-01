<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import ToastContainer from './components/ToastContainer.vue'
import { useAuth } from './composables/useAuth'
import { useTheme } from './composables/useTheme'
import { fetchCurrentUser } from './services/api'

const { token, user, isAuthenticated, setSession, signOut, checkExpiry } = useAuth()
const { theme, isDark, toggleTheme } = useTheme()
const showBackToTop = ref(false)

const initializeUser = async () => {
  if (checkExpiry()) return
  if (token.value && !user.value) {
    const profile = await fetchCurrentUser(token.value)
    if (profile) {
      setSession({ token: token.value, user: profile })
    } else {
      signOut()
    }
  }
}

const handleSignOut = () => {
  signOut()
}

const updateBackToTopVisibility = () => {
  showBackToTop.value = window.scrollY > 280
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  initializeUser()
  updateBackToTopVisibility()
  window.addEventListener('scroll', updateBackToTopVisibility, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', updateBackToTopVisibility)
})
</script>

<template>
  <div class="app-shell">
    <nav class="top-nav">
      <RouterLink class="brand" :to="{ name: 'home' }">I love emojis very much</RouterLink>

      <div class="nav-actions">
        <RouterLink class="link" :to="{ name: 'home' }">Home</RouterLink>
        <RouterLink class="link" :to="{ name: 'collections-index' }">Collections</RouterLink>
        <RouterLink v-if="isAuthenticated" class="link" :to="{ name: 'creator-dashboard' }">
          Creator
        </RouterLink>
        <RouterLink v-if="user?.is_superuser" class="link" :to="{ name: 'admin-dashboard' }">
          Admin
        </RouterLink>
        <RouterLink v-if="!isAuthenticated" class="link" :to="{ name: 'login' }">
          Log in
        </RouterLink>
        <RouterLink v-if="!isAuthenticated" class="button" :to="{ name: 'register' }">
          Register
        </RouterLink>
        <div v-else class="user-block">
          <RouterLink v-if="user" class="welcome" :to="{ name: 'user-profile', params: { id: user.id } }">
            {{ user.display_name ?? user.email }}
          </RouterLink>
          <span v-else class="welcome">Loading...</span>
          <button type="button" class="logout" @click="handleSignOut">Sign out</button>
        </div>
        <button type="button" class="theme-toggle" @click="toggleTheme" :title="theme === 'system' ? 'System theme (auto)' : theme === 'light' ? 'Light theme' : 'Dark theme'">
          {{ theme === 'system' ? '\uD83D\uDCBB' : theme === 'light' ? '\u2600\uFE0F' : '\uD83C\uDF19' }}
        </button>
      </div>
    </nav>

    <RouterView />
    <ToastContainer />
    <button
      v-show="showBackToTop"
      type="button"
      class="back-to-top"
      aria-label="Back to top"
      @click="scrollToTop"
    >
      ↑ Top
    </button>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--color-bg-nav);
  color: #fff;
  gap: 0.5rem;
  flex-wrap: wrap;
}

@media (min-width: 640px) {
  .top-nav {
    padding: 1rem 1.5rem;
    gap: 1rem;
    flex-wrap: nowrap;
  }
}

.brand {
  font-size: clamp(1.1rem, 3vw, 1.25rem);
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-left: auto;
  justify-content: flex-end;
}

@media (min-width: 640px) {
  .nav-actions {
    gap: 0.75rem;
    flex-wrap: nowrap;
  }
}

.link {
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 999px;
  padding: 0.3rem 0.7rem;
  background: transparent;
  color: #e2e8f0;
  font-weight: 600;
  font-size: clamp(0.85rem, 2vw, 0.95rem);
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.2s;
}

.link:hover {
  background: rgba(255, 255, 255, 0.1);
}

.button {
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  font-weight: 600;
  font-size: clamp(0.9rem, 2vw, 1rem);
  white-space: nowrap;
}

@media (min-width: 640px) {
  .button {
    padding: 0.45rem 0.9rem;
  }
}

.user-block {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

@media (min-width: 640px) {
  .user-block {
    gap: 0.75rem;
    flex-wrap: nowrap;
  }
}

.welcome {
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 999px;
  padding: 0.3rem 0.7rem;
  background: transparent;
  color: #e2e8f0;
  font-weight: 600;
  font-size: clamp(0.85rem, 2vw, 0.95rem);
  white-space: nowrap;
  text-decoration: none;
  transition: background 0.2s;
}

.welcome:hover {
  background: rgba(255, 255, 255, 0.1);
}

.logout {
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 999px;
  padding: 0.3rem 0.7rem;
  background: transparent;
  color: #e2e8f0;
  cursor: pointer;
  font-size: clamp(0.85rem, 2vw, 0.95rem);
  white-space: nowrap;
}

@media (min-width: 640px) {
  .logout,
  .link,
  .welcome {
    padding: 0.35rem 0.8rem;
  }
}

.logout:hover {
  background: rgba(255, 255, 255, 0.1);
}

.theme-toggle {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  width: 2.2rem;
  height: 2.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.1rem;
  padding: 0;
  transition: all 0.2s;
  flex-shrink: 0;
}

.theme-toggle:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.5);
}

.back-to-top {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  z-index: 40;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
  background: var(--color-bg-surface-solid);
  color: var(--color-text);
  box-shadow: var(--shadow-elevated);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.back-to-top:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.18);
}

@media (min-width: 768px) {
  .back-to-top {
    right: 1.5rem;
    bottom: 1.5rem;
  }
}
</style>
