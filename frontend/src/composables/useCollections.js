import { computed, reactive } from 'vue'

import {
  createCollection as createCollectionApi,
  fetchEmojiCollections,
  saveEmojiCollections as saveEmojiCollectionsApi,
} from '../services/api'
import { useAuth } from './useAuth'

const emojiStates = reactive({})

const createEmptyState = () => ({
  collections: [],
  selectedIds: [],
  loading: false,
  saving: false,
  error: '',
  lastLoadedAt: 0,
})

const resolveValue = (value) => {
  if (typeof value === 'function') return value()
  if (value && typeof value === 'object' && 'value' in value) return value.value
  return value
}

const normalizeCollectionId = (id) => {
  if (id === null || id === undefined) return null
  if (typeof id === 'number') return id
  if (typeof id === 'string' && id.trim() !== '') {
    const numeric = Number(id)
    return Number.isNaN(numeric) ? id : numeric
  }
  if (typeof id === 'object') {
    return normalizeCollectionId(id.id ?? id.collection_id ?? id.collectionId)
  }
  return null
}

const normalizeCollection = (collection) => {
  if (!collection || typeof collection !== 'object') return null
  const id = normalizeCollectionId(collection.id ?? collection.collection_id ?? collection.collectionId)
  if (id === null) return null
  const name = collection.name ?? collection.title ?? collection.label ?? `Collection ${id}`
  return {
    ...collection,
    id,
    name,
    title: collection.title ?? name,
  }
}

const normalizeCollectionsResponse = (payload) => {
  const root = payload?.data ?? payload ?? {}
  const rawCollections = Array.isArray(root)
    ? root
    : root.collections ?? root.items ?? root.results ?? root.data ?? []

  const collections = rawCollections
    .map(normalizeCollection)
    .filter(Boolean)

  const rawSelectedIds = Array.isArray(root)
    ? []
    : root.selected_collection_ids
      ?? root.collection_ids
      ?? root.selected_ids
      ?? root.selectedIds
      ?? root.emoji_collection_ids
      ?? []

  const selectedIds = Array.isArray(rawSelectedIds)
    ? rawSelectedIds.map(normalizeCollectionId).filter(id => id !== null)
    : []

  if (selectedIds.length > 0) {
    return { collections, selectedIds }
  }

  return {
    collections,
    selectedIds: collections
      .filter(collection => collection.selected || collection.is_selected || collection.checked)
      .map(collection => collection.id),
  }
}

const ensureState = (emojiId) => {
  const key = String(emojiId)
  if (!emojiStates[key]) {
    emojiStates[key] = createEmptyState()
  }
  return emojiStates[key]
}

const serializeCollectionIds = (collectionIds) => {
  return Array.from(new Set((collectionIds ?? []).map(normalizeCollectionId).filter(id => id !== null)))
}

export function useCollections(emojiIdRef) {
  const { token } = useAuth()
  const emojiId = computed(() => resolveValue(emojiIdRef))
  const state = computed(() => {
    if (emojiId.value === null || emojiId.value === undefined) return null
    return ensureState(emojiId.value)
  })

  const collections = computed(() => state.value?.collections ?? [])
  const selectedIds = computed(() => state.value?.selectedIds ?? [])
  const loading = computed(() => Boolean(state.value?.loading))
  const saving = computed(() => Boolean(state.value?.saving))
  const error = computed(() => state.value?.error ?? '')
  const hasCollections = computed(() => collections.value.length > 0)

  const loadEmojiCollections = async (force = false) => {
    if (emojiId.value === null || emojiId.value === undefined) {
      return { collections: [], selectedIds: [] }
    }

    const currentState = ensureState(emojiId.value)
    if (currentState.loading) {
      return {
        collections: currentState.collections,
        selectedIds: currentState.selectedIds,
      }
    }

    if (!force && currentState.lastLoadedAt) {
      return {
        collections: currentState.collections,
        selectedIds: currentState.selectedIds,
      }
    }

    if (!token.value) {
      return { collections: [], selectedIds: [] }
    }

    currentState.loading = true
    currentState.error = ''

    try {
      const payload = await fetchEmojiCollections(emojiId.value, token.value)
      const normalized = normalizeCollectionsResponse(payload)
      currentState.collections = normalized.collections
      currentState.selectedIds = normalized.selectedIds
      currentState.lastLoadedAt = Date.now()
      return normalized
    } catch (error) {
      currentState.error = error.message ?? 'Failed to load collections'
      throw error
    } finally {
      currentState.loading = false
    }
  }

  const saveEmojiCollections = async (collectionIds) => {
    if (emojiId.value === null || emojiId.value === undefined) {
      throw new Error('Missing emoji id')
    }

    if (!token.value) {
      throw new Error('Please log in to save collections')
    }

    const currentState = ensureState(emojiId.value)
    const normalizedIds = serializeCollectionIds(collectionIds)

    currentState.saving = true
    currentState.error = ''

    try {
      const payload = await saveEmojiCollectionsApi(emojiId.value, normalizedIds, token.value)
      const normalized = normalizeCollectionsResponse(payload)
      if (normalized.collections.length > 0) {
        currentState.collections = normalized.collections
      }
      currentState.selectedIds = normalized.selectedIds.length > 0
        ? normalized.selectedIds
        : normalizedIds
      currentState.lastLoadedAt = Date.now()
      return {
        collections: currentState.collections,
        selectedIds: currentState.selectedIds,
      }
    } catch (error) {
      currentState.error = error.message ?? 'Failed to save collections'
      throw error
    } finally {
      currentState.saving = false
    }
  }

  const createCollection = async (payload) => {
    if (!token.value) {
      throw new Error('Please log in to create collections')
    }

    return createCollectionApi(payload, token.value)
  }

  return {
    emojiId,
    state,
    collections,
    selectedIds,
    loading,
    saving,
    error,
    hasCollections,
    loadEmojiCollections,
    saveEmojiCollections,
    createCollection,
  }
}
