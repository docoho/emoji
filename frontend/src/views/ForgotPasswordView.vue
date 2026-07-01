<script setup>
import { ref } from 'vue'
import { requestPasswordReset } from '../services/api'

const email = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

const handleSubmit = async () => {
  if (!email.value) {
    error.value = 'Please enter your email'
    return
  }

  loading.value = true
  error.value = ''
  success.value = false

  try {
    await requestPasswordReset(email.value)
    success.value = true
  } catch (err) {
    error.value = err.message ?? 'Failed to request password reset'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="page">
    <div class="form-container">
      <h1>Forgot Password</h1>
      <p class="subtitle">Enter your email to reset your password</p>

      <form v-if="!success" @submit.prevent="handleSubmit" class="form">
        <div class="field">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="your@email.com"
            required
          />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <button type="submit" :disabled="loading" class="submit-btn">
          {{ loading ? 'Sending...' : 'Send Reset Link' }}
        </button>
      </form>

      <div v-else class="success-message">
        <p class="success">✓ Password reset instructions sent!</p>
        <p>Check your email for the reset link.</p>
      </div>

      <p class="link-text">
        Remember your password?
        <RouterLink :to="{ name: 'login' }">Log in</RouterLink>
      </p>
    </div>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: radial-gradient(circle at top, var(--bg-page-1), var(--bg-page-2), var(--bg-page-3));
}

.form-container {
  width: 100%;
  max-width: 420px;
  padding: 2.5rem;
  border-radius: 1.5rem;
  background: var(--color-bg-surface-solid);
  box-shadow: var(--shadow-elevated);
}

h1 {
  margin: 0 0 0.5rem 0;
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--color-text-heading);
}

.subtitle {
  margin: 0 0 2rem 0;
  color: var(--color-text-muted);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

label {
  font-weight: 600;
  color: var(--color-text-secondary);
}

input {
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border-input);
  background: var(--color-bg-input);
  color: var(--color-text);
  border-radius: 0.5rem;
  font-size: 1rem;
}

input:focus {
  outline: none;
  border-color: #6366f1;
}

.error {
  color: var(--color-text-error);
  font-size: 0.95rem;
  margin: 0;
}

.success {
  color: var(--color-text-success);
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
}

.success-message {
  margin-bottom: 1.5rem;
}

.submit-btn {
  padding: 0.875rem 1.5rem;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.link-text {
  margin-top: 1.5rem;
  text-align: center;
  color: var(--color-text-muted);
}

.link-text a {
  color: var(--color-text-link);
  font-weight: 600;
  text-decoration: none;
}

.link-text a:hover {
  text-decoration: underline;
}
</style>
