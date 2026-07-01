<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { registerUser } from '../services/api'

const router = useRouter()

const form = reactive({
  email: '',
  password: '',
  confirmPassword: '',
  display_name: '',
})

const error = ref('')
const submitting = ref(false)

const handleSubmit = async (event) => {
  event.preventDefault()
  error.value = ''

  if (form.password !== form.confirmPassword) {
    error.value = 'Passwords do not match'
    return
  }

  submitting.value = true
  try {
    await registerUser({
      email: form.email,
      password: form.password,
      display_name: form.display_name || null,
    })
    router.push({ name: 'login', query: { registered: '1' } })
  } catch (err) {
    error.value = err.message ?? 'Registration failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <form class="card" @submit="handleSubmit">
      <h1>Create account</h1>
      <p>Join the emoji explorers.</p>

      <label>
        Email
        <input v-model.trim="form.email" type="email" required aria-required="true" />
      </label>

      <label>
        Display name
        <input v-model.trim="form.display_name" maxlength="64" />
      </label>

      <label>
        Password
        <input v-model="form.password" type="password" required aria-required="true" />
      </label>

      <label>
        Confirm password
        <input v-model="form.confirmPassword" type="password" required aria-required="true" />
      </label>

      <button type="submit" :disabled="submitting">
        {{ submitting ? 'Creating…' : 'Register' }}
      </button>

      <p v-if="error" class="feedback error" role="alert">{{ error }}</p>

      <router-link class="link" :to="{ name: 'login' }">
        Already have an account? Sign in
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
  background: radial-gradient(circle at top, var(--bg-register-1), var(--bg-register-2));
}

.card {
  width: min(460px, 100%);
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
  background: linear-gradient(120deg, #22d3ee, #a855f7);
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
  color: var(--color-text-error);
}

.link {
  justify-self: start;
  color: var(--color-text-link);
  font-weight: 600;
}
</style>
