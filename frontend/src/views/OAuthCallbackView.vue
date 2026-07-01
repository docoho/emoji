<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { exchangeOAuthCode, fetchCurrentUser } from '../services/api'

const route = useRoute()
const router = useRouter()
const { setSession } = useAuth()
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  const code = typeof route.query.code === 'string' ? route.query.code : ''
  const errorMsg = typeof route.query.error === 'string' ? route.query.error : ''
  const redirectTo = typeof route.query.redirect === 'string' ? route.query.redirect : '/'

  if (code || errorMsg) {
    await router.replace({
      name: 'oauth-google-callback',
      query: redirectTo === '/' ? {} : { redirect: redirectTo },
    })
  }

  if (errorMsg) {
    error.value = errorMsg
    loading.value = false
    setTimeout(() => router.push('/login'), 3000)
    return
  }

  if (!code) {
    error.value = 'No authentication code received'
    loading.value = false
    setTimeout(() => router.push('/login'), 3000)
    return
  }

  try {
    const { access_token: token } = await exchangeOAuthCode(code)
    const user = await fetchCurrentUser(token)
    setSession({ token, user })
    router.push(redirectTo)
  } catch (err) {
    error.value = 'Failed to complete login'
    loading.value = false
    setTimeout(() => router.push('/login'), 3000)
  }
})
</script>

<template>
  <main class="callback-page">
    <div class="card">
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>Completing sign in...</p>
      </div>
      <div v-else class="error">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="#DC2626" stroke-width="2"/>
          <path d="M12 8v4M12 16h.01" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <p class="error-msg">{{ error }}</p>
        <p class="redirect-msg">Redirecting to login...</p>
      </div>
    </div>
  </main>
</template>

<style scoped>
.callback-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem;
  background: radial-gradient(circle at top, #ede9fe, #ecfeff);
}

.card {
  width: min(420px, 100%);
  padding: 3rem 2.5rem;
  text-align: center;
  border-radius: 1.5rem;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(209, 213, 219, 0.6);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
}

.loading,
.error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f4f6;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading p {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 500;
  color: #1f2937;
}

.error-msg {
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
  color: #dc2626;
}

.redirect-msg {
  margin: 0.5rem 0 0 0;
  font-size: 0.875rem;
  color: #6b7280;
}
</style>
