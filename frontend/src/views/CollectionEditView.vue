<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import CollectionForm from '../components/CollectionForm.vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'

const getApi = () => import('../services/api')

const route = useRoute()
const router = useRouter()
const { token, isAuthenticated } = useAuth()
const { addToast } = useToast()

const collection = ref(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')

const collectionId = computed(() => route.params.id)

const normalizeCollection = (value) => {
  const source = value || {}
  return {
    ...source,
    name: source.name ?? source.title ?? '',
    description: source.description ?? '',
    kind: source.kind ?? (source.is_public ?? source.public ? 'public' : 'personal'),
  }
}

const loadCollection = async () => {
  loading.value = true
  error.value = ''
  try {
    const api = await getApi()
    if (typeof api.fetchCollection !== 'function') {
      throw new Error('Collection editing is not available yet')
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

const handleSubmit = async (payload) => {
  saving.value = true
  error.value = ''
  try {
    const api = await getApi()
    if (typeof api.updateCollection !== 'function') {
      throw new Error('Collection updates are not available yet')
    }
    const updated = await api.updateCollection(collectionId.value, payload, token.value)
    const updatedId = updated?.id ?? updated?.collection_id ?? updated?.slug ?? collectionId.value
    addToast('Collection updated successfully.')
    await router.push({ name: 'collection-detail', params: { id: updatedId } })
  } catch (err) {
    error.value = err?.message ?? 'Failed to update collection'
  } finally {
    saving.value = false
  }
}

const handleCancel = async () => {
  await router.push({ name: 'collection-detail', params: { id: collectionId.value } })
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
    <div v-if="!isAuthenticated" class="auth-card">
      <p class="eyebrow">Collections</p>
      <h1>Edit collection</h1>
      <p>You need to sign in before editing collections.</p>
      <RouterLink class="login-link" :to="{ name: 'login' }">Log in</RouterLink>
    </div>

    <div v-else-if="loading" class="status">Loading collection...</div>
    <div v-else-if="error && !collection" class="status error">{{ error }}</div>
    <template v-else-if="collection">
      <CollectionForm
        :collection="collection"
        heading="Edit collection"
        helper-text="Update the title, description, or visibility of this collection."
        submit-label="Save changes"
        :loading="saving"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
      <p v-if="error" class="status error">{{ error }}</p>
    </template>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 2rem 1rem 3rem;
  background: radial-gradient(circle at top, var(--bg-page-1), var(--bg-page-2), var(--bg-page-3));
  color: var(--color-text);
}

.auth-card {
  width: min(640px, 100%);
  margin: 0 auto;
  padding: 2rem;
  border-radius: 1.5rem;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
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

.auth-card p {
  color: var(--color-text-secondary);
}

.login-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 1rem;
  border-radius: 999px;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  font-weight: 700;
}

.status {
  width: min(760px, 100%);
  margin: 1rem auto 0;
  text-align: center;
  color: var(--color-text-secondary);
}

.status.error {
  color: var(--color-text-error);
}
</style>
