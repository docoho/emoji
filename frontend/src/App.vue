<script setup>
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import { useAuth } from './composables/useAuth'
import { fetchCurrentUser } from './services/api'

const { token, user, isAuthenticated, setSession, signOut } = useAuth()

const initializeUser = async () => {
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

onMounted(() => {
  initializeUser()
})
</script>

<template>
  <div class="app-shell">
    <nav class="top-nav">
      <RouterLink class="brand" :to="{ name: 'home' }">Emoji Portal</RouterLink>

      <div class="nav-actions">
        <RouterLink class="link" :to="{ name: 'home' }">Home</RouterLink>
        <RouterLink v-if="!isAuthenticated" class="link" :to="{ name: 'login' }">
          Log in
        </RouterLink>
        <RouterLink v-if="!isAuthenticated" class="button" :to="{ name: 'register' }">
          Register
        </RouterLink>
        <div v-else class="user-block">
          <span class="welcome">Hi, {{ user?.display_name ?? user?.email }}</span>
          <button type="button" class="logout" @click="handleSignOut">Sign out</button>
        </div>
      </div>
    </nav>

    <RouterView />
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
  padding: 1rem 1.5rem;
  background: rgba(15, 23, 42, 0.85);
  color: #fff;
  gap: 1rem;
}

.brand {
  font-size: 1.25rem;
  font-weight: 700;
  color: #fff;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.link {
  color: #e0e7ff;
  font-weight: 500;
}

.button {
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  font-weight: 600;
}

.user-block {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.welcome {
  font-weight: 500;
}

.logout {
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 999px;
  padding: 0.35rem 0.8rem;
  background: transparent;
  color: #e2e8f0;
  cursor: pointer;
}

.logout:hover {
  background: rgba(255, 255, 255, 0.1);
}

@media (max-width: 640px) {
  .top-nav {
    flex-direction: column;
    align-items: flex-start;
  }

  .nav-actions {
    flex-wrap: wrap;
  }
}
</style>
