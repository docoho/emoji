<script setup>
import { ref } from 'vue'

const props = defineProps({
  emoji: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['delete', 'update'])

const isEditing = ref(false)
const editForm = ref({
  symbol: props.emoji.symbol,
  title: props.emoji.title,
  description: props.emoji.description || '',
  category: props.emoji.category || '',
  keywords: props.emoji.keywords || [],
})

const handleDelete = () => {
  emit('delete', props.emoji)
}

const startEdit = () => {
  editForm.value = {
    symbol: props.emoji.symbol,
    title: props.emoji.title,
    description: props.emoji.description || '',
    category: props.emoji.category || '',
    keywords: [...(props.emoji.keywords || [])],
  }
  isEditing.value = true
}

const cancelEdit = () => {
  isEditing.value = false
}

const saveEdit = () => {
  const payload = {
    symbol: editForm.value.symbol,
    title: editForm.value.title,
    description: editForm.value.description || undefined,
    category: editForm.value.category || undefined,
    keywords: editForm.value.keywords.length > 0 ? editForm.value.keywords : undefined,
  }
  emit('update', props.emoji, payload)
  isEditing.value = false
}

const updateKeywords = (e) => {
  editForm.value.keywords = e.target.value
    .split(',')
    .map(k => k.trim())
    .filter(k => k)
}
</script>

<template>
  <article class="card">
    <div v-if="!isEditing" class="card-content">
      <div class="symbol" aria-hidden="true">{{ emoji.symbol }}</div>
      <h3 class="title">{{ emoji.title }}</h3>
      <p v-if="emoji.description" class="description">{{ emoji.description }}</p>
      <ul class="meta">
        <li v-if="emoji.category">{{ emoji.category }}</li>
        <li v-for="tag in emoji.keywords" :key="tag">#{{ tag }}</li>
      </ul>
      <div v-if="emoji.can_delete" class="actions">
        <button type="button" class="edit" @click.stop="startEdit">Edit</button>
        <button type="button" class="delete" @click.stop="handleDelete">Delete</button>
      </div>
    </div>

    <div v-else class="edit-form">
      <input v-model="editForm.symbol" placeholder="Emoji symbol" maxlength="8" class="input" />
      <input v-model="editForm.title" placeholder="Title" class="input" />
      <textarea v-model="editForm.description" placeholder="Description" class="textarea"></textarea>
      <input v-model="editForm.category" placeholder="Category" class="input" />
      <input 
        :value="editForm.keywords.join(', ')" 
        @input="updateKeywords"
        placeholder="Keywords (comma-separated)" 
        class="input" 
      />
      <div class="actions">
        <button type="button" class="save" @click="saveEdit">Save</button>
        <button type="button" class="cancel" @click="cancelEdit">Cancel</button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.card {
  height: 320px;
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(233, 233, 233, 0.8);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  overflow: hidden;
}

.card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 34px rgba(15, 23, 42, 0.12);
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  height: 100%;
  overflow: hidden;
}

.symbol {
  font-size: 3rem;
  line-height: 1;
  text-align: center;
  padding: 0.5rem 0;
  flex-shrink: 0;
}

.title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.description {
  color: #4b5563;
  font-size: 0.85rem;
  flex-shrink: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  max-height: 2.8em;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.5rem;
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 0.8rem;
  color: #6b7280;
  flex-grow: 1;
  overflow: hidden;
  max-height: 5.5rem;
  align-content: flex-start;
}

.meta li {
  background: rgba(15, 23, 42, 0.05);
  border-radius: 999px;
  padding: 0.25rem 0.6rem;
  white-space: nowrap;
  flex-shrink: 0;
  height: fit-content;
}

.actions {
  display: flex;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 0.5rem;
  flex-shrink: 0;
}

.edit {
  border: 1px solid rgba(99, 102, 241, 0.5);
  background: rgba(99, 102, 241, 0.1);
  color: #4338ca;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
}

.edit:hover {
  background: rgba(99, 102, 241, 0.2);
}

.delete {
  border: 1px solid rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
}

.delete:hover {
  background: rgba(239, 68, 68, 0.2);
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.input,
.textarea {
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  font-size: 0.95rem;
  font-family: inherit;
}

.textarea {
  min-height: 60px;
  resize: vertical;
}

.save {
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
}

.save:hover {
  opacity: 0.9;
}

.cancel {
  border: 1px solid #cbd5e1;
  background: white;
  color: #475569;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
}

.cancel:hover {
  background: #f1f5f9;
}
</style>
