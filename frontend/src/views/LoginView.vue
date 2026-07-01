<script setup>
import { reactive, ref, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchCurrentUser, loginUser, initiateGoogleLogin } from '../services/api'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const route = useRoute()
const { setSession } = useAuth()

const form = reactive({
  email: '',
  password: '',
})

const error = ref('')
const success = ref('')
const submitting = ref(false)

watchEffect(() => {
  if (route.query.registered === '1') {
    success.value = 'Registration successful. Please log in.'
  } else {
    success.value = ''
  }

  if (route.query.error) {
    error.value = decodeURIComponent(route.query.error)
  }
})

const handleSubmit = async (event) => {
  event.preventDefault()
  submitting.value = true
  error.value = ''
  try {
    const tokenResponse = await loginUser({
      email: form.email,
      password: form.password,
    })

    const token = tokenResponse.access_token
    const user = await fetchCurrentUser(token)
    setSession({ token, user })
    const redirectTo = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirectTo)
  } catch (err) {
    error.value = err.message ?? 'Unable to log in'
  } finally {
    submitting.value = false
  }
}

const handleGoogleLogin = async () => {
  try {
    submitting.value = true
    error.value = ''
    const redirectTo = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    const callbackRedirect = redirectTo === '/'
      ? '/auth/google/callback'
      : `/auth/google/callback?redirect=${encodeURIComponent(redirectTo)}`
    const { authorization_url } = await initiateGoogleLogin(callbackRedirect)
    window.location.href = authorization_url
  } catch (err) {
    error.value = err.message ?? 'Failed to initiate Google login'
    submitting.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <form class="card" @submit="handleSubmit">
      <h1>Log in</h1>
      <p>Access your emoji dashboard.</p>

      <button
        type="button"
        class="google-btn"
        @click="handleGoogleLogin"
        :disabled="submitting"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
          <path d="M19.6 10.23c0-.82-.1-1.42-.25-2.05H10v3.72h5.5c-.15.96-.74 2.31-2.04 3.22v2.45h3.16c1.89-1.73 2.98-4.3 2.98-7.34z" fill="#4285F4"/>
          <path d="M13.46 15.13c-.83.59-1.96 1-3.46 1-2.64 0-4.88-1.74-5.68-4.15H1.07v2.52C2.72 17.75 6.09 20 10 20c2.7 0 4.96-.89 6.62-2.42l-3.16-2.45z" fill="#34A853"/>
          <path d="M3.99 10c0-.69.12-1.35.32-1.97V5.51H1.07A9.973 9.973 0 000 10c0 1.61.39 3.14 1.07 4.49l3.24-2.52c-.2-.62-.32-1.28-.32-1.97z" fill="#FBBC05"/>
          <path d="M10 3.88c1.88 0 3.13.81 3.85 1.48l2.84-2.76C14.96.99 12.7 0 10 0 6.09 0 2.72 2.25 1.07 5.51l3.24 2.52C5.12 5.62 7.36 3.88 10 3.88z" fill="#EA4335"/>
        </svg>
        Sign in with Google
      </button>

      <div class="divider">
        <span>or continue with email</span>
      </div>

      <label>
        Email
        <input v-model.trim="form.email" type="email" required aria-required="true" />
      </label>

      <label>
        Password
        <input v-model="form.password" type="password" required aria-required="true" />
      </label>

      <button type="submit" :disabled="submitting">
        {{ submitting ? 'Signing in…' : 'Sign in' }}
      </button>

      <p v-if="error" class="feedback error" role="alert">{{ error }}</p>
      <p v-if="success" class="feedback success">{{ success }}</p>

      <div class="links">
        <router-link class="link" :to="{ name: 'forgot-password' }">
          Forgot password?
        </router-link>
        <router-link class="link" :to="{ name: 'register' }">
          Need an account? Register now
        </router-link>
      </div>
    </form>
  </main>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem;
  background: radial-gradient(circle at top, var(--bg-auth-1), var(--bg-auth-2));
}

.card {
  width: min(420px, 100%);
  display: grid;
  gap: 1rem;
  padding: 2.5rem;
  border-radius: 1.5rem;
  background: var(--color-bg-surface-solid);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-elevated);
}

.card h1 {
  margin: 0;
  font-size: 2rem;
  color: var(--color-text-heading);
}

label {
  display: grid;
  gap: 0.4rem;
  font-weight: 600;
  color: var(--color-text-heading);
}

input {
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-input);
  color: var(--color-text);
  padding: 0.65rem 0.85rem;
  font: inherit;
}

button {
  border: none;
  border-radius: 0.75rem;
  padding: 0.75rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  cursor: pointer;
}

button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.google-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  background: var(--color-google-btn-bg);
  color: var(--color-text-heading);
  border: 1px solid var(--color-google-btn-border);
  font-weight: 500;
  transition: all 0.2s;
}

.google-btn:hover:not(:disabled) {
  background: var(--color-google-btn-hover);
  border-color: var(--color-text-muted);
}

.divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: var(--color-text-muted);
  font-size: 0.875rem;
  margin: 0.5rem 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-divider);
}

.feedback {
  margin: 0;
  font-size: 0.9rem;
}

.feedback.error {
  color: var(--color-text-error);
}

.feedback.success {
  color: var(--color-text-success);
}

.links {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.link {
  justify-self: start;
  color: var(--color-text-link);
  font-weight: 600;
}
</style>
