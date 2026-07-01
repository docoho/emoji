<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { useAuth } from '../composables/useAuth'
import { useCollections } from '../composables/useCollections'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  emoji: {
    type: Object,
    default: null,
  },
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'saved'])

const { token, isAuthenticated: authState } = useAuth()
const emojiId = computed(() => props.emoji?.id ?? null)
const {
  collections,
  loading,
  saving,
  error,
  hasCollections,
  selectedIds,
  loadEmojiCollections,
  saveEmojiCollections,
  createCollection,
} = useCollections(emojiId)

const selectedCollectionIds = ref([])
const quickCreateName = ref('')
const localError = ref('')
const creatingCollection = ref(false)

const sessionIsAuthenticated = computed(() => props.isAuthenticated || authState.value || Boolean(token.value))
const emojiLabel = computed(() => props.emoji?.title || props.emoji?.symbol || 'this emoji')
const isBusy = computed(() => loading.value || saving.value || creatingCollection.value)

const suggestedCollectionName = () => `Saved ${emojiLabel.value} collection`

const syncSelectionFromState = () => {
  selectedCollectionIds.value = selectedIds.value.map(id => String(id))
  if (!quickCreateName.value) {
    quickCreateName.value = suggestedCollectionName()
  }
}

const loadCollectionsForEmoji = async () => {
  localError.value = ''
  quickCreateName.value = suggestedCollectionName()

  if (!sessionIsAuthenticated.value || !emojiId.value) {
    selectedCollectionIds.value = []
    return
  }

  try {
    await loadEmojiCollections(true)
    syncSelectionFromState()
  } catch (loadError) {
    localError.value = loadError.message ?? 'Failed to load collections'
  }
}

const closeDialog = () => {
  localError.value = ''
  emit('close')
}

const handleSave = async () => {
  if (!sessionIsAuthenticated.value) {
    localError.value = 'Please log in to save emojis to collections.'
    return
  }

  localError.value = ''
  try {
    const result = await saveEmojiCollections(selectedCollectionIds.value)
    emit('saved', {
      emojiId: emojiId.value,
      collectionIds: result.selectedIds,
    })
    closeDialog()
  } catch (saveError) {
    localError.value = saveError.message ?? 'Failed to save collections'
  }
}

const handleQuickCreate = async () => {
  if (!sessionIsAuthenticated.value) {
    localError.value = 'Please log in to create collections.'
    return
  }

  const name = quickCreateName.value.trim()
  if (!name) {
    localError.value = 'Give your collection a name first.'
    return
  }

  creatingCollection.value = true
  localError.value = ''

  try {
    const created = await createCollection({ name })
    const createdId = created?.id ?? created?.collection_id ?? created?.collectionId
    if (createdId === null || createdId === undefined) {
      throw new Error('Collection was created, but no collection id was returned')
    }
    selectedCollectionIds.value = [String(createdId)]
    await saveEmojiCollections(selectedCollectionIds.value)
    emit('saved', {
      emojiId: emojiId.value,
      collectionIds: selectedCollectionIds.value,
      createdCollection: created,
    })
    closeDialog()
  } catch (createError) {
    localError.value = createError.message ?? 'Failed to create collection'
  } finally {
    creatingCollection.value = false
  }
}

watch(
  [() => props.open, emojiId],
  async ([open]) => {
    if (!open) {
      selectedCollectionIds.value = []
      quickCreateName.value = ''
      localError.value = ''
      return
    }

    await loadCollectionsForEmoji()
  },
  { immediate: true }
)
</script>

<template>
  <Teleport to="body">
    <Transition name="picker">
      <div
        v-if="open"
        class="picker-overlay"
        @click.self="closeDialog"
      >
        <div class="picker-dialog" role="dialog" aria-modal="true" :aria-label="`Save ${emojiLabel} to a collection`">
          <button type="button" class="picker-close" @click="closeDialog" aria-label="Close picker">
            ×
          </button>

          <div class="picker-header">
            <div class="picker-emoji" aria-hidden="true">{{ emoji?.symbol }}</div>
            <div>
              <h3>Save to collection</h3>
              <p>Choose where to keep {{ emojiLabel }}.</p>
            </div>
          </div>

          <p v-if="localError || error" class="picker-error">
            {{ localError || error }}
          </p>

          <template v-if="sessionIsAuthenticated">
            <div v-if="loading" class="picker-status">Loading your collections...</div>

            <template v-else>
              <div v-if="hasCollections" class="picker-list">
                <label
                  v-for="collection in collections"
                  :key="collection.id"
                  class="picker-item"
                >
                  <input
                    v-model="selectedCollectionIds"
                    type="checkbox"
                    :value="String(collection.id)"
                  />
                  <span class="picker-item-copy">
                    <strong>{{ collection.name }}</strong>
                    <small v-if="collection.description">{{ collection.description }}</small>
                  </span>
                </label>
              </div>

              <div v-else class="picker-empty">
                <p>You do not have any collections yet.</p>
                <div class="quick-create">
                  <input
                    v-model="quickCreateName"
                    type="text"
                    class="quick-create-input"
                    placeholder="New collection name"
                    @keyup.enter="handleQuickCreate"
                  />
                  <button
                    type="button"
                    class="picker-primary"
                    :disabled="isBusy || !quickCreateName.trim()"
                    @click="handleQuickCreate"
                  >
                    Create &amp; save
                  </button>
                </div>
              </div>

              <div v-if="hasCollections" class="picker-actions">
                <button
                  type="button"
                  class="picker-primary"
                  :disabled="isBusy"
                  @click="handleSave"
                >
                  Save changes
                </button>
              </div>

            </template>
          </template>

          <div v-else class="login-guidance">
            <h4>Log in to save collections</h4>
            <p>Sign in first, then you can save {{ emojiLabel }} to one or more collections.</p>
            <div class="login-actions">
              <RouterLink class="login-link primary" :to="{ name: 'login' }" @click="closeDialog">
                Log in
              </RouterLink>
              <RouterLink class="login-link" :to="{ name: 'register' }" @click="closeDialog">
                Create account
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.picker-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.72);
  backdrop-filter: blur(6px);
  z-index: 10020;
}

.picker-dialog {
  position: relative;
  width: min(100%, 520px);
  max-height: min(88vh, 760px);
  overflow: auto;
  border-radius: 1.5rem;
  padding: 1.5rem;
  background: var(--color-bg-solid);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-modal);
  color: var(--color-text);
}

.picker-close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 1.75rem;
  line-height: 1;
  cursor: pointer;
}

.picker-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-right: 2rem;
  margin-bottom: 1rem;
}

.picker-emoji {
  width: 3.5rem;
  height: 3.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 1rem;
  background: linear-gradient(120deg, rgba(99, 102, 241, 0.12), rgba(236, 72, 153, 0.12));
  font-size: 1.9rem;
}

.picker-header h3,
.login-guidance h4 {
  margin: 0;
  color: var(--color-text-heading);
}

.picker-header p,
.picker-footer p,
.login-guidance p,
.picker-empty p {
  margin: 0.25rem 0 0;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.picker-error {
  margin: 0 0 1rem;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  background: rgba(239, 68, 68, 0.08);
  color: #b91c1c;
}

.picker-status {
  padding: 1rem 0;
  color: var(--color-text-secondary);
}

.picker-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 1rem;
}

.picker-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-surface);
  cursor: pointer;
}

.picker-item input {
  margin-top: 0.2rem;
}

.picker-item-copy {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.picker-item-copy strong {
  color: var(--color-text-heading);
}

.picker-item-copy small {
  color: var(--color-text-secondary);
}

.picker-actions,
.picker-footer,
.quick-create,
.login-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.picker-actions,
.picker-footer {
  flex-direction: column;
}

.quick-create {
  align-items: center;
}

.quick-create-input {
  flex: 1;
  min-width: 0;
  padding: 0.75rem 0.9rem;
  border-radius: 0.85rem;
  border: 1px solid var(--color-border-input);
  background: var(--color-bg-input);
  color: var(--color-text);
  font: inherit;
}

.picker-primary,
.picker-secondary,
.login-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 1rem;
  border-radius: 999px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
  transition: transform 0.15s ease, opacity 0.15s ease;
}

.picker-primary {
  border: none;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
}

.picker-secondary {
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-surface);
  color: var(--color-text);
}

.login-guidance {
  margin-top: 0.5rem;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(99, 102, 241, 0.08);
}

.login-actions {
  flex-wrap: wrap;
}

.login-link.primary {
  border: none;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
}

.login-link {
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-surface);
  color: var(--color-text);
}

.picker-primary:hover,
.picker-secondary:hover,
.login-link:hover {
  transform: translateY(-1px);
}

.picker-primary:disabled,
.picker-secondary:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
}

.picker-enter-active,
.picker-leave-active {
  transition: opacity 0.2s ease;
}

.picker-enter-from,
.picker-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .quick-create,
  .login-actions {
    flex-direction: column;
  }

  .quick-create-input {
    width: 100%;
  }
}
</style>
