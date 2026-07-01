<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import CollectionCard from '../components/CollectionCard.vue'
import { useAuth } from '../composables/useAuth'

const getApi = () => import('../services/api')

const { token, isAuthenticated } = useAuth()

const collections = ref([])
const loading = ref(true)
const error = ref('')
const searchQuery = ref('')

const normalizeCollection = (value) => {
  const collection = value || {}
  return {
    ...collection,
    title: collection.title ?? collection.name,
    description: collection.description ?? '',
    emoji_count: collection.emoji_count ?? collection.item_count ?? collection.emojis?.length ?? collection.items?.length ?? 0,
    updated_at: collection.updated_at ?? collection.modified_at ?? collection.created_at ?? '',
    is_public: collection.is_public ?? collection.public ?? collection.kind === 'public',
  }
}

const normalizeCollectionList = (response) => {
  if (Array.isArray(response)) return response.map(normalizeCollection)
  if (Array.isArray(response?.items)) return response.items.map(normalizeCollection)
  if (Array.isArray(response?.collections)) return response.collections.map(normalizeCollection)
  if (Array.isArray(response?.data)) return response.data.map(normalizeCollection)
  return []
}

const sortByRecent = (items) => {
  return [...items].sort((left, right) => {
    const leftTime = new Date(left.updated_at || left.created_at || 0).getTime()
    const rightTime = new Date(right.updated_at || right.created_at || 0).getTime()
    return rightTime - leftTime
  })
}

const filteredCollections = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const sorted = sortByRecent(collections.value)
  if (!query) return sorted
  return sorted.filter((collection) => {
    return [collection.title, collection.description, collection.owner_name, collection.creator_name]
      .filter(Boolean)
      .some((field) => field.toLowerCase().includes(query))
  })
})

const loadCollections = async () => {
  loading.value = true
  error.value = ''
  try {
    const api = await getApi()
    if (typeof api.fetchCollections !== 'function') {
      collections.value = []
      return
    }
    const response = await api.fetchCollections(token.value)
    collections.value = normalizeCollectionList(response)
  } catch (err) {
    error.value = err?.message ?? 'Failed to load collections'
    collections.value = []
  } finally {
    loading.value = false
  }
}

const clearSearch = () => {
  searchQuery.value = ''
}

onMounted(() => {
  loadCollections()
})
</script>

<template>
  <main class="page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Collections</p>
        <h1>Curated emoji sets</h1>
        <p>
          Browse public collections, open a set to see its emojis, or create one for a specific mood,
          project, or moment.
        </p>
      </div>

      <div class="hero-actions">
        <div class="search-wrap">
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Search collections..."
            class="search"
          />
          <button v-if="searchQuery" type="button" class="clear" @click="clearSearch">
            Clear
          </button>
        </div>
        <RouterLink v-if="isAuthenticated" class="create-link" :to="{ name: 'collections-new' }">
          New collection
        </RouterLink>
      </div>
    </section>

    <section class="content">
      <p v-if="loading" class="status">Loading collections...</p>
      <p v-else-if="error" class="status error">{{ error }}</p>
      <template v-else>
        <div v-if="filteredCollections.length" class="grid">
          <CollectionCard
            v-for="collection in filteredCollections"
            :key="collection.id"
            :collection="collection"
          />
        </div>
        <div v-else class="empty-state">
          <h2 v-if="searchQuery">No collections match your search.</h2>
          <h2 v-else>No collections yet.</h2>
          <p v-if="isAuthenticated">
            Start a new set from the Collections page.
          </p>
          <p v-else>
            Log in to create and manage collections.
          </p>
          <RouterLink v-if="isAuthenticated" class="create-link inline" :to="{ name: 'collections-new' }">
            Create your first collection
          </RouterLink>
        </div>
      </template>
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 2rem 1rem 3rem;
  background: radial-gradient(circle at top, var(--bg-page-1), var(--bg-page-2), var(--bg-page-3));
  color: var(--color-text);
}

.hero,
.content {
  width: min(1120px, 100%);
  margin: 0 auto;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}

.hero-copy {
  max-width: 42rem;
}

.eyebrow {
  margin: 0 0 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--color-text-muted);
}

h1 {
  margin: 0;
  color: var(--color-text-heading);
}

.hero-copy p:last-child {
  margin: 0.75rem 0 0;
  color: var(--color-text-secondary);
  max-width: 60ch;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.search-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem;
  border-radius: 999px;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.search {
  min-width: min(320px, 72vw);
  border: 0;
  background: transparent;
  color: var(--color-text);
  padding: 0.55rem 0.9rem;
  font: inherit;
}

.search:focus {
  outline: none;
}

.clear,
.create-link {
  border-radius: 999px;
  font-weight: 700;
}

.clear {
  background: transparent;
  color: var(--color-text-secondary);
  border: 0;
  padding: 0.55rem 0.9rem;
}

.create-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 1rem;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  box-shadow: var(--shadow-elevated);
}

.create-link.inline {
  margin-top: 0.25rem;
}

.content {
  display: grid;
  gap: 1.25rem;
}

.status {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-text-secondary);
}

.status.error {
  color: var(--color-text-error);
}

.grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}

.empty-state {
  width: min(560px, 100%);
  margin: 2rem auto 0;
  padding: 2rem;
  border-radius: 1.5rem;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  text-align: center;
}

.empty-state h2 {
  margin: 0 0 0.75rem;
  color: var(--color-text-heading);
}

.empty-state p {
  margin: 0.5rem 0 0;
  color: var(--color-text-secondary);
}

@media (max-width: 720px) {
  .hero-actions {
    width: 100%;
    justify-content: stretch;
  }

  .search-wrap {
    width: 100%;
  }

  .search {
    min-width: 0;
    width: 100%;
  }

  .create-link {
    width: 100%;
  }
}
</style>
