<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  collection: {
    type: Object,
    default: () => ({}),
  },
  heading: {
    type: String,
    default: 'Collection',
  },
  helperText: {
    type: String,
    default: '',
  },
  submitLabel: {
    type: String,
    default: 'Save collection',
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit', 'cancel'])

const form = reactive({
  name: '',
  description: '',
  kind: 'public',
})

const syncForm = (value) => {
  const source = value || {}
  form.name = source.name ?? source.title ?? ''
  form.description = source.description ?? ''
  form.kind = source.kind ?? (source.is_public ?? source.public ?? true ? 'public' : 'personal')
}

watch(
  () => props.collection,
  (value) => {
    syncForm(value)
  },
  { immediate: true, deep: true },
)

const handleSubmit = () => {
  emit('submit', {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    kind: form.kind,
  })
}
</script>

<template>
  <section class="form-shell">
    <div class="form-intro">
      <p class="eyebrow">Collections</p>
      <h1>{{ heading }}</h1>
      <p v-if="helperText" class="helper">
        {{ helperText }}
      </p>
    </div>

    <form class="collection-form" @submit.prevent="handleSubmit">
      <label class="field">
        <span>Name</span>
        <input v-model="form.name" type="text" maxlength="120" placeholder="Favorites for rainy days" />
      </label>

      <label class="field">
        <span>Description</span>
        <textarea
          v-model="form.description"
          rows="5"
          maxlength="500"
          placeholder="Tell people what this collection is for."
        />
      </label>

      <label class="field">
        <span>Collection type</span>
        <select v-model="form.kind">
          <option value="public">Public</option>
          <option value="personal">Personal</option>
        </select>
      </label>

      <div class="actions">
        <button type="submit" class="primary" :disabled="loading">
          {{ loading ? 'Saving...' : submitLabel }}
        </button>
        <button type="button" class="secondary" :disabled="loading" @click="emit('cancel')">
          Cancel
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.form-shell {
  width: min(760px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 1.25rem;
}

.form-intro {
  padding: 0.5rem 0.25rem 0;
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

.helper {
  margin: 0.65rem 0 0;
  max-width: 56ch;
  color: var(--color-text-secondary);
}

.collection-form {
  display: grid;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 1.5rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface-raised);
  backdrop-filter: blur(6px);
  box-shadow: var(--shadow-card);
}

.field {
  display: grid;
  gap: 0.45rem;
}

.field span {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text-heading);
}

input,
textarea,
select {
  width: 100%;
  box-sizing: border-box;
  border-radius: 0.9rem;
  border: 1px solid var(--color-border-input);
  background: var(--color-bg-input);
  color: var(--color-text);
  padding: 0.9rem 1rem;
  font: inherit;
}

textarea {
  resize: vertical;
  min-height: 10rem;
}

.actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  flex-wrap: wrap;
  padding-top: 0.25rem;
}

.primary,
.secondary {
  min-width: 8.5rem;
  padding: 0.75rem 1rem;
  border-radius: 999px;
  font-weight: 700;
}

.primary {
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
}

.secondary {
  background: var(--color-bg-solid);
  color: var(--color-text-heading);
  border: 1px solid var(--color-border);
}

.primary:disabled,
.secondary:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .actions {
    justify-content: stretch;
  }

  .primary,
  .secondary {
    width: 100%;
  }
}
</style>
