<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import EmojiGrid from '../components/EmojiGrid.vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'

const getApi = () => import('../services/api')

const route = useRoute()
const router = useRouter()
const { token, isAuthenticated, user } = useAuth()
const { addToast } = useToast()

const collection = ref(null)
const loading = ref(true)
const error = ref('')

const normalizeCollection = (value) => {
  const source = value || {}
  const emojis = source.emojis ?? source.items ?? source.emoji_items ?? []
  return {
    ...source,
    title: source.title ?? source.name ?? 'Untitled collection',
    description: source.description ?? '',
    ownerName: source.owner_name ?? source.creator_name ?? source.submitter_name ?? source.username ?? '',
    ownerId: source.owner_id ?? source.user_id ?? null,
    emoji_count: source.emoji_count ?? source.item_count ?? emojis.length,
    is_public: source.is_public ?? source.public ?? source.kind === 'public',
    kind: source.kind ?? (source.is_public ?? source.public ? 'public' : 'personal'),
    emojis,
  }
}

const collectionId = computed(() => route.params.id)

const emojis = computed(() => collection.value?.emojis ?? [])

const canEdit = computed(() => {
  const current = collection.value || {}
  return Boolean(
    current.can_edit ??
      current.can_delete ??
      current.is_owner ??
      current.owned_by_current_user ??
      (user.value && current.ownerId && String(current.ownerId) === String(user.value.id)),
  )
})

const formatDate = (value) => {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
}

const loadCollection = async () => {
  loading.value = true
  error.value = ''
  try {
    const api = await getApi()
    if (typeof api.fetchCollection !== 'function') {
      throw new Error('Collection details are not available yet')
    }
    const response = await api.fetchCollection(collectionId.value, token.value)
    collection.value = normalizeCollection(response)
  } catch (err) {
    error.value = err?.message ?? 'Failed to load collection'
    collection.value = null
  } finally {
    loading.value = false
  }
}

const handleToggleLike = async (emoji) => {
  if (!isAuthenticated.value) return
  try {
    const api = await getApi()
    if (emoji.is_liked) {
      await api.unlikeEmoji(emoji.id, token.value)
      emoji.is_liked = false
      emoji.like_count = Math.max(0, (emoji.like_count || 0) - 1)
    } else {
      await api.likeEmoji(emoji.id, token.value)
      emoji.is_liked = true
      emoji.like_count = (emoji.like_count || 0) + 1
    }
  } catch (err) {
    addToast(err?.message ?? 'Failed to toggle like', 'error')
  }
}

const handleDelete = async () => {
  if (!collection.value) return
  const confirmed = window.confirm(`Delete "${collection.value.title}"? This cannot be undone.`)
  if (!confirmed) return
  try {
    const api = await getApi()
    if (typeof api.deleteCollection !== 'function') {
      throw new Error('Collection deletion is not available yet')
    }
    await api.deleteCollection(collectionId.value, token.value)
    addToast('Collection deleted.')
    await router.push({ name: 'collections-index' })
  } catch (err) {
    addToast(err?.message ?? 'Failed to delete collection', 'error')
  }
}

const handleEdit = async () => {
  await router.push({ name: 'collection-edit', params: { id: collectionId.value } })
}

watch(
  collectionId,
  () => {
    loadCollection()
  },
  { immediate: true },
)
</script>

<template>
  <main class="page">
    <div v-if="loading" class="status">Loading collection...</div>
    <div v-else-if="error" class="status error">{{ error }}</div>
    <div v-else-if="collection" class="layout">
      <section class="hero-card">
        <div class="hero-topline">
          <RouterLink class="back-link" :to="{ name: 'collections-index' }">Collections</RouterLink>
          <span class="badge" :class="{ public: collection.is_public }">
            {{ collection.kind === 'personal' ? 'Personal' : 'Public' }}
          </span>
        </div>

        <div class="hero-copy">
          <h1>{{ collection.title }}</h1>
          <p v-if="collection.description" class="description">
            {{ collection.description }}
          </p>
          <p v-else class="description muted">No description yet.</p>
        </div>

        <div class="meta-row">
          <div class="stat">
            <span class="stat-value">{{ collection.emoji_count }}</span>
            <span class="stat-label">Emojis</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ collection.ownerName || 'Unknown' }}</span>
            <span class="stat-label">Owner</span>
          </div>
          <div class="stat" v-if="collection.created_at || collection.updated_at">
            <span class="stat-value">{{ formatDate(collection.updated_at || collection.created_at) }}</span>
            <span class="stat-label">Updated</span>
          </div>
        </div>

        <div v-if="canEdit" class="actions">
          <button type="button" class="secondary" @click="handleEdit">Edit</button>
          <button type="button" class="danger" @click="handleDelete">Delete</button>
        </div>
      </section>

      <section class="content-card">
        <div class="section-head">
          <h2>Emoji set</h2>
          <p>{{ collection.emoji_count }} total emojis</p>
        </div>

        <EmojiGrid
          v-if="emojis.length"
          :emojis="emojis"
          :is-authenticated="isAuthenticated"
          @toggle-like="handleToggleLike"
        />
        <div v-else class="empty-state">
          <p>This collection does not have any emojis yet.</p>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 2rem 1rem 3rem;
  background: radial-gradient(circle at top, var(--bg-page-1), var(--bg-page-2), var(--bg-page-3));
  color: var(--color-text);
}

.layout {
  width: min(1120px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 1.25rem;
}

.hero-card,
.content-card {
  padding: 1.5rem;
  border-radius: 1.5rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface-raised);
  backdrop-filter: blur(6px);
  box-shadow: var(--shadow-card);
}

.hero-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.back-link {
  color: var(--color-text-link);
  font-weight: 700;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  background: var(--color-tag-bg);
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.badge.public {
  color: var(--color-text-success);
}

.hero-copy h1,
.section-head h2 {
  margin: 0;
  color: var(--color-text-heading);
}

.description {
  margin: 0.75rem 0 0;
  color: var(--color-text-secondary);
  max-width: 60ch;
}

.description.muted {
  color: var(--color-text-muted);
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 1.35rem;
}

.stat {
  min-width: 150px;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  background: var(--color-tag-bg);
  border: 1px solid var(--color-border-light);
}

.stat-value {
  color: var(--color-text-heading);
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-label {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 1.25rem;
}

.secondary,
.danger {
  padding: 0.75rem 1rem;
  border-radius: 999px;
  font-weight: 700;
}

.secondary {
  background: var(--color-bg-solid);
  color: var(--color-text-heading);
  border: 1px solid var(--color-border);
}

.danger {
  background: #dc2626;
  color: white;
}

.content-card {
  display: grid;
  gap: 1rem;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.section-head p {
  margin: 0;
  color: var(--color-text-secondary);
}

.status {
  text-align: center;
  padding: 4rem 1rem;
  color: var(--color-text-secondary);
}

.status.error {
  color: var(--color-text-error);
}

.empty-state {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--color-text-secondary);
}

@media (max-width: 640px) {
  .stat {
    min-width: 100%;
  }

  .secondary,
  .danger {
    width: 100%;
  }
}
</style>
