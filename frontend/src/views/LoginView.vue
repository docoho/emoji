<script setup>
import { reactive, ref, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchCurrentUser, loginUser } from '../services/api'
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
    router.push({ name: 'home' })
  } catch (err) {
    error.value = err.message ?? 'Unable to log in'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <form class="card" @submit="handleSubmit">
      <h1>Log in</h1>
      <p>Access your emoji dashboard.</p>

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

      <router-link class="link" :to="{ name: 'register' }">
        Need an account? Register now
      </router-link>
    </form>
  </main>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem;
  background: radial-gradient(circle at top, #ede9fe, #ecfeff);
}

.card {
  width: min(420px, 100%);
  display: grid;
  gap: 1rem;
  padding: 2.5rem;
  border-radius: 1.5rem;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(209, 213, 219, 0.6);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
}

.card h1 {
  margin: 0;
  font-size: 2rem;
}

label {
  display: grid;
  gap: 0.4rem;
  font-weight: 600;
  color: #1f2937;
}

input {
  border-radius: 0.75rem;
  border: 1px solid rgba(209, 213, 219, 0.8);
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

.feedback {
  margin: 0;
  font-size: 0.9rem;
}

.feedback.error {
  color: #dc2626;
}

.feedback.success {
  color: #047857;
}

.link {
  justify-self: start;
  color: #4f46e5;
  font-weight: 600;
}
</style>
