<script setup>
import EmojiCard from './EmojiCard.vue'

const props = defineProps({
  emojis: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['delete'])

const handleDelete = (emoji) => {
  emit('delete', emoji)
}
</script>

<template>
  <section class="grid" aria-live="polite">
    <p v-if="!props.emojis.length" class="empty">No emojis available.</p>
    <EmojiCard
      v-for="item in props.emojis"
      :key="item.id"
      :emoji="item"
      @delete="handleDelete"
    />
  </section>
</template>

<style scoped>
.grid {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}

.empty {
  grid-column: 1 / -1;
  text-align: center;
  color: #6b7280;
}
</style>
