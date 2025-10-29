<script setup>
import { onMounted, ref, watch } from 'vue'

import EmojiGrid from '../components/EmojiGrid.vue'
import EmojiSubmitForm from '../components/EmojiSubmitForm.vue'
import { deleteEmoji, fetchEmojis, submitEmoji, updateEmoji } from '../services/api'
import { useAuth } from '../composables/useAuth'

const emojis = ref([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
const actionMessage = ref('')

const searchQuery = ref('')
const categoryFilter = ref('')
const sortOrder = ref('date_desc')
const currentPage = ref(1)
const pageSize = ref(20)

const { token, isAuthenticated } = useAuth()

const loadEmojis = async () => {
  loading.value = true
  error.value = ''
  actionMessage.value = ''
  try {
    const params = {
      search: searchQuery.value || undefined,
      category: categoryFilter.value || undefined,
      sort: sortOrder.value,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    }
    const response = await fetchEmojis(token.value, params)
    emojis.value = response.items || response
    total.value = response.total || (response.items ? response.items.length : response.length)
  } catch (err) {
    error.value = err.message ?? 'Failed to load emojis'
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadEmojis()
}

const handleFilterChange = () => {
  currentPage.value = 1
  loadEmojis()
}

const handleSubmit = async (payload) => {
  actionMessage.value = ''
  error.value = ''
  try {
    const created = await submitEmoji(payload, token.value)
    emojis.value = [created, ...emojis.value]
    total.value += 1
    actionMessage.value = 'Emoji submitted successfully.'
  } catch (err) {
    error.value = err.message ?? 'Failed to submit emoji'
  }
}

const handleUpdate = async (emoji, payload) => {
  actionMessage.value = ''
  error.value = ''
  try {
    const updated = await updateEmoji(emoji.id, payload, token.value)
    const index = emojis.value.findIndex((item) => item.id === emoji.id)
    if (index !== -1) {
      emojis.value[index] = updated
    }
    actionMessage.value = 'Emoji updated successfully.'
  } catch (err) {
    error.value = err.message ?? 'Failed to update emoji'
  }
}

const handleDelete = async (emoji) => {
  actionMessage.value = ''
  error.value = ''
  try {
    await deleteEmoji(emoji.id, token.value)
    emojis.value = emojis.value.filter((item) => item.id !== emoji.id)
    total.value -= 1
    actionMessage.value = 'Emoji deleted.'
  } catch (err) {
    error.value = err.message ?? 'Failed to delete emoji'
  }
}

const nextPage = () => {
  if (currentPage.value * pageSize.value < total.value) {
    currentPage.value += 1
    loadEmojis()
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value -= 1
    loadEmojis()
  }
}

const totalPages = () => Math.ceil(total.value / pageSize.value)

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
      <div class="filters">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search emojis..."
          class="search-input"
          @keyup.enter="handleSearch"
        />
        <button class="search-btn" @click="handleSearch">Search</button>
        <select v-model="categoryFilter" class="filter-select" @change="handleFilterChange">
          <option value="">All Categories</option>
          <option value="People">People</option>
          <option value="Nature">Nature</option>
          <option value="Food">Food</option>
          <option value="Activities">Activities</option>
          <option value="Travel">Travel</option>
          <option value="Objects">Objects</option>
          <option value="Symbols">Symbols</option>
          <option value="Flags">Flags</option>
        </select>
        <select v-model="sortOrder" class="filter-select" @change="handleFilterChange">
          <option value="date_desc">Newest First</option>
          <option value="date_asc">Oldest First</option>
          <option value="title_asc">Title A-Z</option>
          <option value="title_desc">Title Z-A</option>
        </select>
      </div>

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
        <div>
          <EmojiGrid :emojis="emojis" @delete="handleDelete" @update="handleUpdate" />
          
          <div v-if="totalPages() > 1" class="pagination">
            <button :disabled="currentPage === 1" @click="prevPage" class="page-btn">
              ← Previous
            </button>
            <span class="page-info">
              Page {{ currentPage }} of {{ totalPages() }} ({{ total }} total)
            </span>
            <button :disabled="currentPage >= totalPages()" @click="nextPage" class="page-btn">
              Next →
            </button>
          </div>
        </div>
      </div>
      <p v-if="actionMessage" class="status success">{{ actionMessage }}</p>
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 2rem 1rem;
  background: radial-gradient(circle at top, #fdf2f8, #e0f2fe, #ede9fe);
  color: #0f172a;
}

@media (min-width: 768px) {
  .page {
    padding: 4rem 1.5rem;
  }
}

.hero {
  max-width: 720px;
  margin: 0 auto 2rem auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0 1rem;
}

@media (min-width: 768px) {
  .hero {
    margin: 0 auto 2.5rem auto;
  }
}

.hero h1 {
  font-size: clamp(2rem, 5vw, 3.5rem);
  font-weight: 700;
}

.hero p {
  color: #475569;
  font-size: clamp(0.95rem, 2vw, 1.05rem);
}

.content {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 1rem;
}

@media (min-width: 1400px) {
  .content {
    max-width: 1400px;
  }
}

.filters {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  align-items: stretch;
}

@media (min-width: 768px) {
  .filters {
    margin-bottom: 2rem;
  }
}

.search-input {
  flex: 1 1 100%;
  min-width: 200px;
  padding: 0.6rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  font-size: 0.95rem;
}

@media (min-width: 640px) {
  .search-input {
    flex: 1 1 auto;
  }
}

.search-btn {
  flex: 0 0 auto;
  padding: 0.6rem 1.5rem;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.search-btn:hover {
  opacity: 0.9;
}

.filter-select {
  flex: 1 1 calc(50% - 0.375rem);
  min-width: 140px;
  padding: 0.6rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  font-size: 0.95rem;
  background: white;
  cursor: pointer;
}

@media (min-width: 640px) {
  .filter-select {
    flex: 0 1 auto;
  }
}

.layout {
  display: grid;
  gap: 2rem;
  grid-template-columns: 1fr;
}

@media (min-width: 900px) {
  .layout {
    gap: 2.5rem;
    grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
    align-items: start;
  }
}

.form-stack {
  min-width: 0;
  width: 100%;
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

.pagination {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
  padding: 1rem;
}

@media (min-width: 640px) {
  .pagination {
    flex-direction: row;
    gap: 1.5rem;
    padding: 1.5rem;
  }
}

.page-btn {
  width: 100%;
  max-width: 200px;
  padding: 0.6rem 1.2rem;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

@media (min-width: 640px) {
  .page-btn {
    width: auto;
  }
}

.page-btn:hover:not(:disabled) {
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  border-color: transparent;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  color: #475569;
  font-size: clamp(0.85rem, 2vw, 0.95rem);
  text-align: center;
  order: -1;
}

@media (min-width: 640px) {
  .page-info {
    order: 0;
  }
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
