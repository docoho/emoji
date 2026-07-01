<script setup>
import { useToast } from '../composables/useToast'

const { toasts, removeToast } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast"
          :class="toast.type"
          @click="removeToast(toast.id)"
        >
          <span class="toast-icon">
            {{ toast.type === 'success' ? '\u2705' : toast.type === 'error' ? '\u274C' : '\u2139\uFE0F' }}
          </span>
          <span class="toast-message">{{ toast.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 9999;
  display: flex;
  flex-direction: column-reverse;
  gap: 0.5rem;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-radius: 0.75rem;
  font-size: 0.9rem;
  font-weight: 500;
  color: #fff;
  backdrop-filter: blur(8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  pointer-events: auto;
  max-width: 360px;
}

.toast.success {
  background: rgba(16, 185, 129, 0.92);
}

.toast.error {
  background: rgba(239, 68, 68, 0.92);
}

.toast.info {
  background: rgba(99, 102, 241, 0.92);
}

.toast-icon {
  flex-shrink: 0;
  font-size: 1rem;
}

.toast-message {
  line-height: 1.3;
}

.toast-enter-active {
  transition: all 0.3s ease-out;
}

.toast-leave-active {
  transition: all 0.25s ease-in;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(80px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(80px);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
