import { ref } from 'vue'

const toasts = ref([])
let nextId = 0

function removeToast(id) {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

function addToast(message, type = 'success', duration = 3000) {
  const id = nextId++
  if (toasts.value.length >= 5) {
    toasts.value.shift()
  }
  toasts.value.push({ id, message, type })
  setTimeout(() => removeToast(id), duration)
}

export function useToast() {
  return {
    toasts,
    addToast,
    removeToast,
  }
}
