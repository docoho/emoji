<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import EmojiGrid from '../components/EmojiGrid.vue'
import { deleteEmoji, fetchEmojis, likeEmoji, unlikeEmoji, updateEmoji } from '../services/api'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'

const emojis = ref([])
const total = ref(0)
const loading = ref(true)
const error = ref('')

const searchQuery = ref('')
const categoryFilter = ref('')
const sortOrder = ref('date_desc')
const showFavorites = ref(false)
const currentPage = ref(1)
const pageSize = ref(8)

const { token, isAuthenticated } = useAuth()
const { addToast } = useToast()

const floatingEmojis = ref([])
const emojiPool = ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗', '😚', '😙', '🥲', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '🥸', '😎', '🤓', '🧐', '😕', '😟', '🙁', '☹️', '😮', '😯', '😲', '😳', '🥺', '😦', '😧', '😨', '😰', '😥', '😢', '😭', '😱', '😖', '😣', '😞', '😓', '😩', '😫', '🥱', '😤', '😡', '😠', '🤬', '😈', '👿', '💀', '☠️', '💩', '🤡', '👹', '👺', '👻', '👽', '👾', '🤖', '😺', '😸', '😹', '😻', '😼', '😽', '🙀', '😿', '😾']
let animationInterval = null

const replaceEmojiInList = (listRef, updated) => {
  listRef.value = listRef.value.map((item) => (item.id === updated.id ? { ...item, ...updated } : item))
}

const removeEmojiFromList = (listRef, emojiId) => {
  listRef.value = listRef.value.filter((item) => item.id !== emojiId)
}

const addFloatingEmoji = () => {
  const emoji = emojiPool[Math.floor(Math.random() * emojiPool.length)]
  const id = Date.now() + Math.random()
  const startX = Math.random() * 100
  const startY = Math.random() * 100
  const duration = 2000 + Math.random() * 2000
  
  floatingEmojis.value.push({ id, emoji, startX, startY, duration })
  
  setTimeout(() => {
    floatingEmojis.value = floatingEmojis.value.filter(e => e.id !== id)
  }, duration)
}

const startEmojiAnimation = () => {
  addFloatingEmoji()
  animationInterval = setInterval(() => {
    addFloatingEmoji()
  }, 500 + Math.random() * 1000)
}

const stopEmojiAnimation = () => {
  if (animationInterval) {
    clearInterval(animationInterval)
    animationInterval = null
  }
}

const loadEmojis = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = {
      search: searchQuery.value || undefined,
      category: categoryFilter.value || undefined,
      sort: sortOrder.value,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
      favorites: showFavorites.value || undefined,
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

const clearSearch = () => {
  searchQuery.value = ''
  currentPage.value = 1
  loadEmojis()
}

const handleFilterChange = () => {
  currentPage.value = 1
  loadEmojis()
}

const handleUpdate = async (emoji, payload) => {
  try {
    const updated = await updateEmoji(emoji.id, payload, token.value)
    replaceEmojiInList(emojis, updated)
    addToast('Emoji updated successfully!')
  } catch (err) {
    addToast(err.message ?? 'Failed to update emoji', 'error')
  }
}

const handleDelete = async (emoji) => {
  try {
    await deleteEmoji(emoji.id, token.value)
    removeEmojiFromList(emojis, emoji.id)
    total.value -= 1
    addToast('Emoji deleted.')
  } catch (err) {
    addToast(err.message ?? 'Failed to delete emoji', 'error')
  }
}

const handleToggleLike = async (emoji) => {
  if (!isAuthenticated.value) return
  try {
    if (emoji.is_liked) {
      await unlikeEmoji(emoji.id, token.value)
      emoji.is_liked = false
      emoji.like_count = Math.max(0, (emoji.like_count || 0) - 1)
    } else {
      await likeEmoji(emoji.id, token.value)
      emoji.is_liked = true
      emoji.like_count = (emoji.like_count || 0) + 1
    }
  } catch (err) {
    addToast(err.message ?? 'Failed to toggle like', 'error')
  }
}

const toggleFavorites = () => {
  showFavorites.value = !showFavorites.value
  currentPage.value = 1
  loadEmojis()
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

onMounted(() => {
  loadEmojis()
  startEmojiAnimation()
})

onUnmounted(() => {
  stopEmojiAnimation()
})

watch(token, () => {
  loadEmojis()
})
</script>

<template>
  <main class="page">
    <header class="hero">
      <div class="hero-title-container">
        <h1>Emoji Showcase</h1>
        <div 
          v-for="emoji in floatingEmojis" 
          :key="emoji.id" 
          class="floating-emoji"
          :style="{
            '--start-x': emoji.startX + '%',
            '--start-y': emoji.startY + '%',
            '--duration': emoji.duration + 'ms'
          }"
        >
          {{ emoji.emoji }}
        </div>
      </div>
    </header>

    <section class="content">
      <div class="filters">
        <div class="search-row">
          <div class="search-container">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search emojis..."
              class="search-input"
              @keyup.enter="handleSearch"
            />
            <button 
              v-if="searchQuery" 
              class="clear-btn" 
              @click="clearSearch"
              type="button"
              aria-label="Clear search"
            >
              ✕
            </button>
          </div>
          <button class="search-btn" @click="handleSearch">Search</button>
        </div>
        <div class="filter-group">
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
            <option value="popular">Most Popular</option>
          </select>
          <button
            v-if="isAuthenticated"
            class="favorites-btn"
            :class="{ active: showFavorites }"
            @click="toggleFavorites"
          >
            {{ showFavorites ? '\u2764\uFE0F My Favorites' : '\uD83E\uDE76 My Favorites' }}
          </button>
        </div>
      </div>

      <p v-if="loading" class="status">Loading emojis…</p>
      <p v-else-if="error" class="status error">{{ error }}</p>
      <div v-else class="layout">
        <div class="form-stack">
          <div class="creator-card">
            <h2>{{ isAuthenticated ? 'Ready to build your next emoji?' : 'Want to share an emoji?' }}</h2>
            <p v-if="isAuthenticated">
              Open your creator dashboard to save drafts, submit new emojis for review, and shape your public creator page.
            </p>
            <p v-else>
              Sign in to create drafts, submit new emojis for review, and build your public creator page.
            </p>
            <div class="creator-actions">
              <RouterLink
                v-if="isAuthenticated"
                class="creator-link primary"
                :to="{ name: 'creator-dashboard' }"
              >
                Open creator dashboard
              </RouterLink>
              <template v-else>
                <RouterLink class="creator-link primary" :to="{ name: 'login', query: { redirect: '/creator' } }">
                  Log in
                </RouterLink>
                <RouterLink class="creator-link" :to="{ name: 'register' }">
                  Register
                </RouterLink>
              </template>
            </div>
          </div>
        </div>
        <div>
          <EmojiGrid :emojis="emojis" :is-authenticated="isAuthenticated" @delete="handleDelete" @update="handleUpdate" @toggle-like="handleToggleLike" />
          
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
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 1rem 1rem;
  background: radial-gradient(circle at top, var(--bg-page-1), var(--bg-page-2), var(--bg-page-3));
  color: var(--color-text);
}

@media (min-width: 768px) {
  .page {
    padding: 2rem 1.5rem;
  }
}

.hero {
  max-width: 720px;
  margin: 0 auto 1rem auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 1rem;
}

@media (min-width: 768px) {
  .hero {
    margin: 0 auto 1.5rem auto;
  }
}

.hero-title-container {
  position: relative;
  display: inline-block;
  margin: 0 auto;
}

.hero h1 {
  font-size: clamp(2rem, 5vw, 3.5rem);
  font-weight: 700;
  position: relative;
  z-index: 1;
}

.hero p {
  color: var(--color-text-secondary);
  font-size: clamp(0.95rem, 2vw, 1.05rem);
}

.floating-emoji {
  position: absolute;
  font-size: clamp(1.5rem, 3vw, 2.5rem);
  pointer-events: none;
  left: var(--start-x);
  top: var(--start-y);
  animation: float-and-fade var(--duration) ease-in-out forwards;
  z-index: 0;
}

@keyframes float-and-fade {
  0% {
    opacity: 0;
    transform: translate(0, 0) scale(0.5) rotate(0deg);
  }
  15% {
    opacity: 1;
    transform: translate(10px, -10px) scale(1) rotate(15deg);
  }
  50% {
    opacity: 0.8;
    transform: translate(20px, -30px) scale(1.1) rotate(-10deg);
  }
  85% {
    opacity: 0.6;
    transform: translate(15px, -50px) scale(0.9) rotate(20deg);
  }
  100% {
    opacity: 0;
    transform: translate(0, -70px) scale(0.5) rotate(-15deg);
  }
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
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
  align-items: center;
}

@media (min-width: 768px) {
  .filters {
    margin-bottom: 2rem;
  }
}

.search-row {
  display: flex;
  gap: 0.75rem;
  width: 100%;
  max-width: 700px;
  align-items: center;
  flex-wrap: wrap;
}

@media (min-width: 640px) {
  .search-row {
    flex-wrap: nowrap;
  }
}

.search-container {
  position: relative;
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
}

.search-input {
  width: 100%;
  padding: 0.6rem 1rem;
  padding-right: 2.5rem;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border-input);
  background: var(--color-bg-input);
  color: var(--color-text);
  font-size: 0.95rem;
}

.search-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.clear-btn {
  position: absolute;
  right: 0.5rem;
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.clear-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.search-btn {
  padding: 0.6rem 1.5rem;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  font-size: 1rem;
  flex-shrink: 0;
}

.search-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.filter-group {
  display: flex;
  gap: 0.75rem;
  width: 100%;
  max-width: 600px;
  flex-wrap: wrap;
  justify-content: center;
}

.filter-select {
  flex: 1 1 calc(50% - 0.375rem);
  min-width: 160px;
  padding: 0.6rem 1rem;
  border-radius: 0.5rem;
  border: none;
  font-size: 0.95rem;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.filter-select:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.filter-select:focus {
  outline: none;
  opacity: 0.9;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.favorites-btn {
  padding: 0.6rem 1.25rem;
  border-radius: 0.5rem;
  border: none;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95rem;
  white-space: nowrap;
}

.favorites-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.favorites-btn.active {
  background: linear-gradient(120deg, #ef4444, #ec4899);
}

@media (min-width: 640px) {
  .filter-select {
    flex: 0 1 auto;
    min-width: 180px;
  }
}

.layout {
  display: grid;
  gap: 2rem;
  grid-template-columns: 1fr;
}

@media (min-width: 900px) {
  .layout {
    gap: 2rem;
    grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
    align-items: start;
  }
}

.form-stack {
  min-width: 0;
  width: 100%;
}

.creator-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.creator-card {
  display: grid;
  gap: 1.25rem;
  padding: 2rem 1.65rem 1.75rem;
  border-radius: 1.5rem;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(188, 199, 216, 0.72);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.09);
  color: #172240;
  text-align: left;
}

[data-theme="dark"] .creator-card {
  background: rgba(23, 31, 54, 0.94);
  border-color: rgba(148, 163, 184, 0.26);
  color: #f8fafc;
  box-shadow: 0 30px 70px rgba(2, 6, 23, 0.45);
}

.creator-card h2,
.creator-card p {
  margin: 0;
}

.creator-card h2 {
  font-size: clamp(1.65rem, 2.2vw, 2.15rem);
  line-height: 1.08;
  font-weight: 800;
  letter-spacing: 0;
}

.creator-card p {
  max-width: 22ch;
  font-size: clamp(0.98rem, 1.25vw, 1.1rem);
  line-height: 1.5;
  color: rgba(23, 34, 64, 0.86);
}

[data-theme="dark"] .creator-card p {
  color: rgba(226, 232, 240, 0.84);
}

.creator-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  min-height: 2.9rem;
  min-width: 8.5rem;
  padding: 0.55rem 1rem;
  border-radius: 999px;
  border: 2px solid #c9d3e4;
  color: #172240;
  background: rgba(255, 255, 255, 0.55);
  font-weight: 800;
  font-size: 0.9rem;
  line-height: 1.15;
  text-decoration: none;
  text-align: center;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

[data-theme="dark"] .creator-link {
  border-color: rgba(191, 219, 254, 0.28);
  color: #f8fafc;
  background: rgba(255, 255, 255, 0.04);
}

.creator-link.primary {
  border: none;
  background: linear-gradient(135deg, #7267e6, #d845a4);
  color: #fff;
  box-shadow: 0 20px 38px rgba(216, 69, 164, 0.28);
}

.creator-link:hover {
  transform: translateY(-1px);
}

.creator-link:not(.primary):hover {
  border-color: #aebdd6;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

@media (max-width: 640px) {
  .creator-card {
    padding: 1.75rem 1.35rem 1.5rem;
    gap: 1.1rem;
    border-radius: 1.35rem;
  }

  .creator-card p {
    max-width: none;
  }

  .creator-actions {
    gap: 0.9rem;
  }

  .creator-link {
    width: min(100%, 14rem);
    min-width: 0;
    min-height: 3rem;
  }
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
  background: var(--color-bg-solid);
  border: 1px solid var(--color-border-input);
  color: var(--color-text);
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
  color: var(--color-text-secondary);
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
  color: var(--color-text-secondary);
}

.status.error {
  color: var(--color-text-error);
}
</style>
