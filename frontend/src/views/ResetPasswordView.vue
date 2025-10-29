<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { confirmPasswordReset } from '../services/api'

const route = useRoute()
const router = useRouter()

const token = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

onMounted(() => {
  token.value = route.query.token || ''
})

const handleSubmit = async () => {
  error.value = ''

  if (!token.value) {
    error.value = 'Invalid or missing reset token'
    return
  }

  if (newPassword.value.length < 8) {
    error.value = 'Password must be at least 8 characters'
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }

  loading.value = true

  try {
    await confirmPasswordReset(token.value, newPassword.value)
    success.value = true
    setTimeout(() => {
      router.push({ name: 'login' })
    }, 2000)
  } catch (err) {
    error.value = err.message ?? 'Failed to reset password'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="page">
    <div class="form-container">
      <h1>Reset Password</h1>
      <p class="subtitle">Enter your new password</p>

      <form v-if="!success" @submit.prevent="handleSubmit" class="form">
        <div class="field">
          <label for="password">New Password</label>
          <input
            id="password"
            v-model="newPassword"
            type="password"
            placeholder="At least 8 characters"
            required
            minlength="8"
          />
        </div>

        <div class="field">
          <label for="confirm-password">Confirm Password</label>
          <input
            id="confirm-password"
            v-model="confirmPassword"
            type="password"
            placeholder="Re-enter your password"
            required
            minlength="8"
          />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <button type="submit" :disabled="loading" class="submit-btn">
          {{ loading ? 'Resetting...' : 'Reset Password' }}
        </button>
      </form>

      <div v-else class="success-message">
        <p class="success">✓ Password successfully reset!</p>
        <p>Redirecting to login...</p>
      </div>

      <p class="link-text">
        <RouterLink :to="{ name: 'login' }">Back to Login</RouterLink>
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
  background: radial-gradient(circle at top, #fdf2f8, #e0f2fe, #ede9fe);
}

.form-container {
  width: 100%;
  max-width: 420px;
  padding: 2.5rem;
  border-radius: 1.5rem;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.12);
}

h1 {
  margin: 0 0 0.5rem 0;
  font-size: 1.875rem;
  font-weight: 700;
}

.subtitle {
  margin: 0 0 2rem 0;
  color: #64748b;
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
  color: #334155;
}

input {
  padding: 0.75rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 1rem;
}

input:focus {
  outline: none;
  border-color: #6366f1;
}

.error {
  color: #dc2626;
  font-size: 0.95rem;
  margin: 0;
}

.success {
  color: #047857;
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
}

.success-message {
  margin-bottom: 1.5rem;
  text-align: center;
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
  color: #64748b;
}

.link-text a {
  color: #6366f1;
  font-weight: 600;
  text-decoration: none;
}

.link-text a:hover {
  text-decoration: underline;
}
</style>
