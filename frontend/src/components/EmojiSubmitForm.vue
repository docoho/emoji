<script setup>
import { reactive, ref, watch } from 'vue'

const props = defineProps({
  onSubmit: {
    type: Function,
    required: true,
  },
  initialValue: {
    type: Object,
    default: null,
  },
  formTitle: {
    type: String,
    default: 'Shape your next emoji',
  },
  formDescription: {
    type: String,
    default: 'Save a private draft first or send a polished version to moderation.',
  },
  primaryLabel: {
    type: String,
    default: 'Submit for review',
  },
  secondaryLabel: {
    type: String,
    default: 'Save draft',
  },
  allowDraft: {
    type: Boolean,
    default: true,
  },
  resetOnSuccess: {
    type: Boolean,
    default: true,
  },
  showCancel: {
    type: Boolean,
    default: false,
  },
  onCancel: {
    type: Function,
    default: null,
  },
})

const defaultForm = (source = {}) => ({
  symbol: source?.symbol ?? '',
  title: source?.title ?? '',
  description: source?.description ?? '',
  category: source?.category ?? '',
  keywords: Array.isArray(source?.keywords) ? source.keywords.join(', ') : '',
})

const form = reactive(defaultForm())
const error = ref('')
const submittingIntent = ref('')

const syncForm = () => {
  Object.assign(form, defaultForm(props.initialValue))
}

const buildPayload = (intent) => {
  const keywordList = form.keywords
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  return {
    symbol: form.symbol,
    title: form.title,
    description: form.description || null,
    category: form.category || null,
    keywords: keywordList,
    ...(intent ? { intent } : {}),
  }
}

const submitForm = async (intent = '') => {
  error.value = ''
  submittingIntent.value = intent || 'primary'

  try {
    await props.onSubmit(buildPayload(intent))
    if (props.resetOnSuccess) {
      Object.assign(form, defaultForm())
    }
  } catch (err) {
    error.value = err.message ?? 'Unable to save emoji.'
  } finally {
    submittingIntent.value = ''
  }
}

const handlePrimarySubmit = async (event) => {
  event.preventDefault()
  await submitForm(props.allowDraft ? 'submit' : '')
}

const handleSaveDraft = async () => {
  await submitForm('draft')
}

const handleCancel = () => {
  error.value = ''
  syncForm()
  props.onCancel?.()
}

watch(
  () => props.initialValue,
  () => {
    syncForm()
  },
  { immediate: true, deep: true },
)
</script>

<template>
  <form class="form" @submit="handlePrimarySubmit">
    <div class="form-copy">
      <h2>{{ formTitle }}</h2>
      <p>{{ formDescription }}</p>
    </div>

    <label>
      Emoji symbol
      <input v-model.trim="form.symbol" maxlength="8" required aria-required="true" />
    </label>

    <label>
      Title
      <input v-model.trim="form.title" maxlength="128" required aria-required="true" />
    </label>

    <label>
      Description
      <textarea v-model.trim="form.description" maxlength="256" rows="3" />
    </label>

    <label>
      Category
      <select v-model="form.category">
        <option value="">— Select a category —</option>
        <option value="People">People</option>
        <option value="Nature">Nature</option>
        <option value="Food">Food</option>
        <option value="Activities">Activities</option>
        <option value="Travel">Travel</option>
        <option value="Objects">Objects</option>
        <option value="Symbols">Symbols</option>
        <option value="Flags">Flags</option>
      </select>
    </label>

    <label>
      Keywords
      <input
        v-model="form.keywords"
        maxlength="256"
        placeholder="comma separated"
      />
    </label>

    <div class="actions">
      <button
        v-if="allowDraft"
        type="button"
        class="secondary-btn"
        :disabled="Boolean(submittingIntent)"
        @click="handleSaveDraft"
      >
        {{ submittingIntent === 'draft' ? 'Saving…' : secondaryLabel }}
      </button>
      <button type="submit" :disabled="Boolean(submittingIntent)">
        {{ submittingIntent && submittingIntent !== 'draft' ? 'Saving…' : primaryLabel }}
      </button>
      <button
        v-if="showCancel"
        type="button"
        class="ghost-btn"
        :disabled="Boolean(submittingIntent)"
        @click="handleCancel"
      >
        Cancel
      </button>
    </div>

    <p v-if="error" class="feedback error" role="alert">{{ error }}</p>
  </form>
</template>

<style scoped>
.form {
  display: grid;
  gap: 1rem;
  padding: 2rem;
  border-radius: 1.5rem;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.form-copy {
  display: grid;
  gap: 0.35rem;
}

.form h2,
.form p {
  margin: 0;
}

.form-copy p {
  color: var(--color-text-secondary);
}

label {
  display: grid;
  gap: 0.4rem;
  font-weight: 600;
  color: var(--color-text-heading);
}

input,
textarea,
select {
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-input);
  color: var(--color-text);
  padding: 0.65rem 0.85rem;
  font: inherit;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

button {
  border: none;
  border-radius: 0.75rem;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  font-weight: 700;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(99, 102, 241, 0.2);
}

button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.secondary-btn {
  background: rgba(99, 102, 241, 0.12);
  color: var(--color-text-heading);
  border: 1px solid rgba(99, 102, 241, 0.24);
}

.ghost-btn {
  background: transparent;
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.feedback {
  margin: 0;
  font-size: 0.9rem;
}

.feedback.error {
  color: var(--color-text-error);
}
</style>
