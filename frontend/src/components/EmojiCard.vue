<script setup>
const props = defineProps({
  emoji: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['delete'])

const handleDelete = () => {
  emit('delete', props.emoji)
}
</script>

<template>
  <article class="card">
    <div class="symbol" aria-hidden="true">{{ emoji.symbol }}</div>
    <h3>{{ emoji.title }}</h3>
    <p v-if="emoji.description" class="description">{{ emoji.description }}</p>
    <ul class="meta">
      <li v-if="emoji.category">{{ emoji.category }}</li>
      <li v-for="tag in emoji.keywords" :key="tag">#{{ tag }}</li>
    </ul>
    <button
      v-if="emoji.can_delete"
      type="button"
      class="delete"
      @click="handleDelete"
    >
      Delete
    </button>
  </article>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(233, 233, 233, 0.8);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 34px rgba(15, 23, 42, 0.12);
}

.symbol {
  font-size: 2.5rem;
  line-height: 1;
}

.description {
  color: #4b5563;
  font-size: 0.95rem;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.5rem;
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.meta li {
  background: rgba(15, 23, 42, 0.05);
  border-radius: 999px;
  padding: 0.25rem 0.6rem;
}

.delete {
  align-self: flex-start;
  margin-top: 0.5rem;
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
</style>
