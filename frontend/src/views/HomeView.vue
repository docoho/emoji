<script setup>
import { onMounted, ref, watch } from 'vue'

import EmojiGrid from '../components/EmojiGrid.vue'
import EmojiSubmitForm from '../components/EmojiSubmitForm.vue'
import { deleteEmoji, fetchEmojis, submitEmoji } from '../services/api'
import { useAuth } from '../composables/useAuth'

const emojis = ref([])
const loading = ref(true)
const error = ref('')
const actionMessage = ref('')

const { token, isAuthenticated } = useAuth()

const loadEmojis = async () => {
  loading.value = true
  error.value = ''
  actionMessage.value = ''
  try {
    emojis.value = await fetchEmojis(token.value)
  } catch (err) {
    error.value = err.message ?? 'Failed to load emojis'
  } finally {
    loading.value = false
  }
}

const handleSubmit = async (payload) => {
  actionMessage.value = ''
  error.value = ''
  try {
    const created = await submitEmoji(payload, token.value)
    emojis.value = [...emojis.value, created]
    actionMessage.value = 'Emoji submitted successfully.'
  } catch (err) {
    error.value = err.message ?? 'Failed to submit emoji'
  }
}

const handleDelete = async (emoji) => {
  actionMessage.value = ''
  error.value = ''
  try {
    await deleteEmoji(emoji.id, token.value)
    emojis.value = emojis.value.filter((item) => item.id !== emoji.id)
    actionMessage.value = 'Emoji deleted.'
  } catch (err) {
    error.value = err.message ?? 'Failed to delete emoji'
  }
}

onMounted(loadEmojis)

watch(token, () => {
  loadEmojis()
})
</script>

<template>
  <main class="page">
    <header class="hero">
      <h1>Emoji Showcase</h1>
      <p>Browse curated emojis shared by our community.</p>
    </header>

    <section class="content">
      <p v-if="loading" class="status">Loading emojis…</p>
      <p v-else-if="error" class="status error">{{ error }}</p>
      <div v-else class="layout">
        <div class="form-stack">
          <EmojiSubmitForm
            v-if="isAuthenticated"
            :on-submit="handleSubmit"
          />
          <div v-else class="placeholder">
            <h2>Want to share an emoji?</h2>
            <p>Please log in to submit new entries.</p>
          </div>
        </div>
        <EmojiGrid :emojis="emojis" @delete="handleDelete" />
      </div>
      <p v-if="actionMessage" class="status success">{{ actionMessage }}</p>
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 4rem 1.5rem;
  background: radial-gradient(circle at top, #fdf2f8, #e0f2fe, #ede9fe);
  color: #0f172a;
}

.hero {
  max-width: 720px;
  margin: 0 auto 2.5rem auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.hero h1 {
  font-size: clamp(2.5rem, 5vw, 3.5rem);
  font-weight: 700;
}

.hero p {
  color: #475569;
  font-size: 1.05rem;
}

.content {
  max-width: 1080px;
  margin: 0 auto;
}

.layout {
  display: grid;
  gap: 2.5rem;
}

.form-stack {
  min-width: 0;
}

.placeholder {
  padding: 2rem;
  border-radius: 1.5rem;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(209, 213, 219, 0.7);
  text-align: center;
  display: grid;
  gap: 0.5rem;
}

.status {
  text-align: center;
  color: #475569;
}

.status.error {
  color: #dc2626;
}

.status.success {
  color: #047857;
}
</style>

<style>
@media (min-width: 900px) {
  .layout {
    grid-template-columns: minmax(0, 360px) minmax(0, 1fr);
    align-items: start;
  }
}
</style>
