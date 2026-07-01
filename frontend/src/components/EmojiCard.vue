<script setup>
import { computed, ref } from 'vue'
import { useToast } from '../composables/useToast'

const props = defineProps({
  emoji: {
    type: Object,
    required: true,
  },
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['delete', 'update', 'toggle-like', 'save-to-collection'])
const { addToast } = useToast()

const categoryThemes = {
  People: {
    accent: '#fb7185',
    accentSoft: 'rgba(251, 113, 133, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(255, 228, 230, 0.88) 48%, rgba(251, 113, 133, 0.18) 100%)',
  },
  Nature: {
    accent: '#22c55e',
    accentSoft: 'rgba(34, 197, 94, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(220, 252, 231, 0.88) 48%, rgba(34, 197, 94, 0.18) 100%)',
  },
  Food: {
    accent: '#f97316',
    accentSoft: 'rgba(249, 115, 22, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(255, 237, 213, 0.88) 48%, rgba(249, 115, 22, 0.18) 100%)',
  },
  Activities: {
    accent: '#8b5cf6',
    accentSoft: 'rgba(139, 92, 246, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(243, 232, 255, 0.9) 48%, rgba(139, 92, 246, 0.18) 100%)',
  },
  Travel: {
    accent: '#06b6d4',
    accentSoft: 'rgba(6, 182, 212, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(207, 250, 254, 0.88) 48%, rgba(6, 182, 212, 0.18) 100%)',
  },
  Objects: {
    accent: '#eab308',
    accentSoft: 'rgba(234, 179, 8, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(254, 249, 195, 0.88) 48%, rgba(234, 179, 8, 0.18) 100%)',
  },
  Symbols: {
    accent: '#ec4899',
    accentSoft: 'rgba(236, 72, 153, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(252, 231, 243, 0.88) 48%, rgba(236, 72, 153, 0.18) 100%)',
  },
  Flags: {
    accent: '#3b82f6',
    accentSoft: 'rgba(59, 130, 246, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(219, 234, 254, 0.9) 48%, rgba(59, 130, 246, 0.18) 100%)',
  },
  default: {
    accent: '#14b8a6',
    accentSoft: 'rgba(20, 184, 166, 0.18)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.95), rgba(204, 251, 241, 0.9) 48%, rgba(20, 184, 166, 0.18) 100%)',
  },
}

const copied = ref(false)

const handleToggleLike = () => {
  if (props.isAuthenticated) {
    emit('toggle-like', props.emoji)
  }
}

const handleSaveToCollection = () => {
  emit('save-to-collection', props.emoji)
}

const copyEmoji = async () => {
  try {
    await navigator.clipboard.writeText(props.emoji.symbol)
    copied.value = true
    addToast(`Copied ${props.emoji.symbol} to clipboard!`)
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    addToast('Failed to copy emoji', 'error')
  }
}

const categoryTheme = computed(() => categoryThemes[props.emoji.category] || categoryThemes.default)

const cardStyle = computed(() => ({
  '--card-accent': categoryTheme.value.accent,
  '--card-accent-soft': categoryTheme.value.accentSoft,
  '--card-glow': categoryTheme.value.glow,
}))

const categoryLabel = computed(() => props.emoji.category || 'Curated')
</script>

<template>
  <article class="card" :style="cardStyle">
    <div class="card-content">
      <div class="card-head">
        <span class="category-pill">{{ categoryLabel }}</span>
        <button type="button" class="copy-btn" :class="{ copied }" @click.stop="copyEmoji" :title="copied ? 'Copied!' : 'Copy emoji'">
          {{ copied ? 'Copied!' : 'Copy' }}
        </button>
      </div>

      <div class="symbol-stage" aria-hidden="true">
        <div class="symbol-orb"></div>
        <div class="symbol">{{ emoji.symbol }}</div>
      </div>

      <div class="card-body">
        <div class="likes-chip" :class="{ liked: emoji.is_liked }">
          <span class="likes-icon">{{ emoji.is_liked ? '\u2764\uFE0F' : '\u2661' }}</span>
          <span>{{ emoji.like_count || 0 }}</span>
        </div>
        <div class="comments-chip">
          <span class="comments-icon">💬</span>
          <span>{{ emoji.comment_count || 0 }}</span>
        </div>
      </div>

      <div class="card-footer">
        <div class="action-row">
          <button
            type="button"
            class="collection-btn"
            title="Save to a collection"
            @click.stop="handleSaveToCollection"
          >
            <span class="btn-mark">+</span>
            <span>Save</span>
          </button>
          <button
            type="button"
            class="like-btn"
            :class="{ liked: emoji.is_liked, disabled: !isAuthenticated }"
            :title="isAuthenticated ? (emoji.is_liked ? 'Unlike' : 'Like') : 'Log in to like'"
            @click.stop="handleToggleLike"
          >
            <span class="heart">{{ emoji.is_liked ? '\u2764\uFE0F' : '\u2661' }}</span>
            <span>{{ emoji.is_liked ? 'Liked' : 'Like' }}</span>
          </button>
        </div>
      </div>
    </div>
  </article>
</template>

<style scoped>
.card {
  position: relative;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  padding: 0.95rem;
  border-radius: 1.55rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.82)),
    linear-gradient(135deg, var(--card-accent-soft), transparent 55%);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.1);
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
  overflow: hidden;
  isolation: isolate;
}

[data-theme="dark"] .card {
  background:
    linear-gradient(180deg, rgba(24, 24, 36, 0.96), rgba(17, 24, 39, 0.92)),
    linear-gradient(135deg, var(--card-accent-soft), transparent 60%);
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.5);
}

.card::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top right, var(--card-accent-soft), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent 35%);
  pointer-events: none;
  z-index: -1;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.14);
  border-color: color-mix(in srgb, var(--card-accent) 28%, rgba(255, 255, 255, 0.5));
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
  min-height: 100%;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.category-pill {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 1.85rem;
  padding: 0.28rem 0.72rem;
  border-radius: 999px;
  background: var(--card-accent-soft);
  color: var(--card-accent);
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.symbol {
  position: relative;
  z-index: 1;
  font-size: clamp(3.1rem, 5vw, 3.9rem);
  line-height: 1;
  text-align: center;
  filter: drop-shadow(0 8px 18px rgba(15, 23, 42, 0.12));
}

.symbol-stage {
  position: relative;
  min-height: 6.1rem;
  display: grid;
  place-items: center;
  border-radius: 1.2rem;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.62), rgba(255, 255, 255, 0.18)),
    var(--card-glow);
  border: 1px solid rgba(255, 255, 255, 0.45);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
}

[data-theme="dark"] .symbol-stage {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01)),
    var(--card-glow);
  border-color: rgba(148, 163, 184, 0.16);
}

.symbol-orb {
  position: absolute;
  width: 5.8rem;
  height: 5.8rem;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.9), transparent 68%);
  opacity: 0.85;
}

.copy-btn {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.68);
  border-radius: 999px;
  padding: 0.38rem 0.72rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--color-text-secondary);
  cursor: pointer;
  backdrop-filter: blur(10px);
  transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.copy-btn:hover {
  transform: translateY(-1px);
  background: var(--card-accent);
  color: white;
  border-color: var(--card-accent);
}

.copy-btn.copied {
  opacity: 1;
  background: #10b981;
  color: white;
  border-color: #10b981;
}

.card-body {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  flex: 1;
  justify-content: center;
  min-height: 2.5rem;
}

.likes-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
  padding: 0.34rem 0.62rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  color: var(--color-text-secondary);
  font-size: 0.74rem;
  font-weight: 700;
}

[data-theme="dark"] .likes-chip {
  background: rgba(255, 255, 255, 0.08);
}

.comments-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.34rem 0.62rem;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.1);
  color: #0f766e;
  font-size: 0.74rem;
  font-weight: 700;
}

[data-theme="dark"] .comments-chip {
  background: rgba(56, 189, 248, 0.12);
  color: #67e8f9;
}

.likes-chip.liked {
  color: #dc2626;
  background: rgba(239, 68, 68, 0.1);
}

.likes-icon {
  font-size: 0.9rem;
  line-height: 1;
}

.card-footer {
  display: flex;
  flex-direction: column;
  margin-top: auto;
  padding-top: 0.1rem;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  justify-content: center;
  flex-wrap: nowrap;
}

.collection-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 0.62rem 0.95rem;
  min-width: 6.25rem;
  min-height: 2.55rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: var(--card-accent);
  color: white;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 12px 22px color-mix(in srgb, var(--card-accent) 30%, transparent);
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.collection-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 28px color-mix(in srgb, var(--card-accent) 38%, transparent);
}

.btn-mark {
  display: inline-grid;
  place-items: center;
  width: 1rem;
  height: 1rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
}

.like-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  justify-content: center;
  background: var(--card-accent);
  border: 1px solid transparent;
  cursor: pointer;
  padding: 0.62rem 0.95rem;
  min-width: 6.25rem;
  min-height: 2.74rem;
  border-radius: 999px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  font-size: 0.84rem;
  font-weight: 800;
  color: white;
  box-shadow: 0 12px 22px color-mix(in srgb, var(--card-accent) 30%, transparent);
}

.like-btn:hover:not(.disabled) {
  transform: translateY(-1px);
  box-shadow: 0 16px 28px color-mix(in srgb, var(--card-accent) 38%, transparent);
}

.like-btn.disabled {
  cursor: default;
  opacity: 0.6;
}

.like-btn.liked {
  background: linear-gradient(135deg, #ef4444, #f87171);
  box-shadow: 0 16px 28px rgba(239, 68, 68, 0.3);
}

.like-btn.liked .heart {
  animation: heartPop 0.3s ease;
}

.heart {
  font-size: 1rem;
  line-height: 1;
}

@keyframes heartPop {
  0% { transform: scale(1); }
  50% { transform: scale(1.22); }
  100% { transform: scale(1); }
}

@media (max-width: 640px) {
  .card {
    min-height: 286px;
    padding: 0.85rem;
    border-radius: 1.25rem;
  }

  .symbol-stage {
    min-height: 5.35rem;
  }

  .action-row {
    width: 100%;
  }

  .collection-btn,
  .like-btn {
    flex: 1 1 0;
  }
}
</style>
