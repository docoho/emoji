<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import CollectionForm from '../components/CollectionForm.vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'

const getApi = () => import('../services/api')

const router = useRouter()
const { token, isAuthenticated } = useAuth()
const { addToast } = useToast()

const loading = ref(false)
const error = ref('')

const defaultCollection = computed(() => ({
  name: '',
  description: '',
  kind: 'public',
}))

const handleSubmit = async (payload) => {
  loading.value = true
  error.value = ''
  try {
    const api = await getApi()
    if (typeof api.createCollection !== 'function') {
      throw new Error('Collection creation is not available yet')
    }
    const created = await api.createCollection(payload, token.value)
    const createdId = created?.id ?? created?.collection_id ?? created?.slug
    if (!createdId) {
      throw new Error('Collection was created, but no id was returned')
    }
    addToast('Collection created successfully.')
    await router.push({ name: 'collection-detail', params: { id: createdId } })
  } catch (err) {
    error.value = err?.message ?? 'Failed to create collection'
  } finally {
    loading.value = false
  }
}

const handleCancel = async () => {
  await router.push({ name: 'collections-index' })
}
</script>

<template>
  <main class="page">
    <div v-if="!isAuthenticated" class="auth-card">
      <p class="eyebrow">Collections</p>
      <h1>Create a collection</h1>
      <p>You need to sign in before creating collections.</p>
      <RouterLink class="login-link" :to="{ name: 'login' }">Log in</RouterLink>
    </div>

    <template v-else>
      <CollectionForm
        :collection="defaultCollection"
        heading="Create a new collection"
        helper-text="Give this collection a clear name and decide whether it should be visible to everyone."
        submit-label="Create collection"
        :loading="loading"
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
