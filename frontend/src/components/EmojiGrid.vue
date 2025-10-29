<script setup>
import { ref } from 'vue'
import EmojiCard from './EmojiCard.vue'

const props = defineProps({
  emojis: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['delete', 'update'])

const selectedEmoji = ref(null)

const handleDelete = (emoji) => {
  emit('delete', emoji)
}

const handleUpdate = (emoji, payload) => {
  emit('update', emoji, payload)
}

const handleEmojiClick = (emoji) => {
  selectedEmoji.value = emoji
}

const closeModal = () => {
  selectedEmoji.value = null
}
</script>

<template>
  <section class="grid-container">
    <p v-if="!props.emojis.length" class="empty">No emojis available.</p>
    
    <div v-else class="emoji-grid">
      <div
        v-for="item in props.emojis"
        :key="item.id"
        class="emoji-item"
        @click="handleEmojiClick(item)"
      >
        <EmojiCard
          :emoji="item"
          @delete="handleDelete"
          @update="handleUpdate"
        />
      </div>
    </div>

    <!-- Enlarged Emoji Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="selectedEmoji" class="modal-overlay" @click="closeModal">
          <div class="modal-content" @click.stop>
            <button class="modal-close" @click="closeModal" aria-label="Close">✕</button>
            <div class="enlarged-emoji">
              <div class="emoji-symbol">{{ selectedEmoji.symbol }}</div>
              <h2>{{ selectedEmoji.title }}</h2>
              <p v-if="selectedEmoji.description" class="emoji-description">
                {{ selectedEmoji.description }}
              </p>
              <div v-if="selectedEmoji.category" class="emoji-meta">
                <span class="category-badge">{{ selectedEmoji.category }}</span>
              </div>
              <div v-if="selectedEmoji.keywords?.length" class="emoji-keywords">
                <span v-for="keyword in selectedEmoji.keywords" :key="keyword" class="keyword-tag">
                  #{{ keyword }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
.grid-container {
  position: relative;
  width: 100%;
}

.emoji-grid {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}

@media (min-width: 1200px) {
  .emoji-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.emoji-item {
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.emoji-item:hover {
  transform: translateY(-4px);
  z-index: 10;
}

.empty {
  text-align: center;
  color: #6b7280;
  padding: 3rem;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
  backdrop-filter: blur(4px);
}

.modal-content {
  position: relative;
  background: white;
  border-radius: 1.5rem;
  padding: 3rem;
  max-width: 600px;
  width: 100%;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
  animation: scaleIn 0.3s ease-out;
}

@keyframes scaleIn {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.modal-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(0, 0, 0, 0.1);
  border: none;
  font-size: 1.5rem;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  color: #6b7280;
}

.modal-close:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  transform: rotate(90deg);
}

.enlarged-emoji {
  text-align: center;
}

.emoji-symbol {
  font-size: 8rem;
  line-height: 1;
  margin-bottom: 1.5rem;
  animation: bounceIn 0.5s ease-out;
}

@keyframes bounceIn {
  0% {
    transform: scale(0);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

.enlarged-emoji h2 {
  font-size: 2rem;
  margin: 0 0 1rem 0;
  color: #1f2937;
}

.emoji-description {
  color: #6b7280;
  font-size: 1.1rem;
  margin: 0 0 1.5rem 0;
  line-height: 1.6;
}

.emoji-meta {
  margin: 1.5rem 0;
}

.category-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.95rem;
}

.emoji-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 1.5rem;
}

.keyword-tag {
  padding: 0.4rem 0.8rem;
  background: rgba(99, 102, 241, 0.1);
  color: #4338ca;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 500;
}

/* Modal Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-enter-from .modal-content {
  transform: scale(0.9);
}
</style>
