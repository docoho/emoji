<script setup>
import { reactive, ref } from 'vue'

const props = defineProps({
  onSubmit: {
    type: Function,
    required: true,
  },
})

const defaultForm = () => ({
  symbol: '',
  title: '',
  description: '',
  category: '',
  keywords: '',
  submitter_email: '',
})

const form = reactive(defaultForm())
const error = ref('')
const success = ref('')
const submitting = ref(false)

const onSubmit = async (event) => {
  event.preventDefault()
  error.value = ''
  success.value = ''

  const keywordList = form.keywords
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  const payload = {
    symbol: form.symbol,
    title: form.title,
    description: form.description || null,
    category: form.category || null,
    keywords: keywordList,
    submitter_email: form.submitter_email || null,
  }

  submitting.value = true
  try {
    await props.onSubmit(payload)
    Object.assign(form, defaultForm())
    success.value = 'Emoji submitted!'
  } catch (err) {
    error.value = err.message ?? 'Submission failed.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="form" @submit="onSubmit">
    <h2>Share an emoji</h2>

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
      <input v-model.trim="form.category" maxlength="64" />
    </label>

    <label>
      Keywords
      <input
        v-model="form.keywords"
        maxlength="256"
        placeholder="comma separated"
      />
    </label>

    <label>
      Contact email
      <input v-model.trim="form.submitter_email" type="email" maxlength="256" />
    </label>

    <button type="submit" :disabled="submitting">
      {{ submitting ? 'Submitting…' : 'Submit emoji' }}
    </button>

    <p v-if="error" class="feedback error" role="alert">{{ error }}</p>
    <p v-if="success" class="feedback success">{{ success }}</p>
  </form>
</template>

<style scoped>
.form {
  display: grid;
  gap: 1rem;
  padding: 2rem;
  border-radius: 1.5rem;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(209, 213, 219, 0.7);
  box-shadow: 0 10px 32px rgba(15, 23, 42, 0.08);
}

.form h2 {
  margin: 0;
  font-size: 1.5rem;
}

label {
  display: grid;
  gap: 0.4rem;
  font-weight: 600;
  color: #1f2937;
}

input,
textarea {
  border-radius: 0.75rem;
  border: 1px solid rgba(209, 213, 219, 0.8);
  padding: 0.65rem 0.85rem;
  font: inherit;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

input:focus,
textarea:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

button {
  border: none;
  border-radius: 0.75rem;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  font-weight: 600;
  padding: 0.75rem;
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

.feedback {
  margin: 0;
  font-size: 0.9rem;
}

.feedback.error {
  color: #dc2626;
}

.feedback.success {
  color: #047857;
}
</style>
