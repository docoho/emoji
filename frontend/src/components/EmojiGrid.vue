<script setup>
import { reactive, ref, watch } from 'vue'

import CollectionPickerDialog from './CollectionPickerDialog.vue'
import EmojiCard from './EmojiCard.vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import {
  createEmojiComment,
  deleteEmojiComment,
  fetchEmojiComments,
  reportEmoji,
} from '../services/api'

const props = defineProps({
  emojis: {
    type: Array,
    default: () => [],
  },
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['delete', 'update', 'toggle-like'])

const COMMENTS_PAGE_SIZE = 20
const REPORT_REASONS = [
  { value: 'spam', label: 'Spam or abuse' },
  { value: 'copyright', label: 'Copyright issue' },
  { value: 'offensive', label: 'Offensive content' },
  { value: 'misleading', label: 'Misleading or wrong' },
  { value: 'other', label: 'Other' },
]
const categoryThemes = {
  People: {
    accent: '#fb7185',
    accentStrong: 'rgba(251, 113, 133, 0.35)',
    accentSoft: 'rgba(251, 113, 133, 0.16)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(255, 228, 230, 0.88) 52%, rgba(251, 113, 133, 0.2) 100%)',
  },
  Nature: {
    accent: '#22c55e',
    accentStrong: 'rgba(34, 197, 94, 0.34)',
    accentSoft: 'rgba(34, 197, 94, 0.14)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(220, 252, 231, 0.88) 52%, rgba(34, 197, 94, 0.2) 100%)',
  },
  Food: {
    accent: '#f97316',
    accentStrong: 'rgba(249, 115, 22, 0.34)',
    accentSoft: 'rgba(249, 115, 22, 0.14)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(255, 237, 213, 0.88) 52%, rgba(249, 115, 22, 0.2) 100%)',
  },
  Activities: {
    accent: '#8b5cf6',
    accentStrong: 'rgba(139, 92, 246, 0.34)',
    accentSoft: 'rgba(139, 92, 246, 0.14)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(243, 232, 255, 0.9) 52%, rgba(139, 92, 246, 0.2) 100%)',
  },
  Travel: {
    accent: '#06b6d4',
    accentStrong: 'rgba(6, 182, 212, 0.34)',
    accentSoft: 'rgba(6, 182, 212, 0.14)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(207, 250, 254, 0.88) 52%, rgba(6, 182, 212, 0.2) 100%)',
  },
  Objects: {
    accent: '#eab308',
    accentStrong: 'rgba(234, 179, 8, 0.34)',
    accentSoft: 'rgba(234, 179, 8, 0.14)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(254, 249, 195, 0.88) 52%, rgba(234, 179, 8, 0.2) 100%)',
  },
  Symbols: {
    accent: '#ec4899',
    accentStrong: 'rgba(236, 72, 153, 0.34)',
    accentSoft: 'rgba(236, 72, 153, 0.14)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(252, 231, 243, 0.88) 52%, rgba(236, 72, 153, 0.2) 100%)',
  },
  Flags: {
    accent: '#3b82f6',
    accentStrong: 'rgba(59, 130, 246, 0.34)',
    accentSoft: 'rgba(59, 130, 246, 0.14)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(219, 234, 254, 0.9) 52%, rgba(59, 130, 246, 0.2) 100%)',
  },
  default: {
    accent: '#14b8a6',
    accentStrong: 'rgba(20, 184, 166, 0.34)',
    accentSoft: 'rgba(20, 184, 166, 0.14)',
    glow: 'radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.95), rgba(204, 251, 241, 0.9) 52%, rgba(20, 184, 166, 0.2) 100%)',
  },
}

const { token } = useAuth()
const { addToast } = useToast()

const selectedEmoji = ref(null)
const collectionPickerEmoji = ref(null)
const modalCopied = ref(false)
const comments = ref([])
const commentsTotal = ref(0)
const commentsLoading = ref(false)
const commentsLoadingMore = ref(false)
const commentsError = ref('')
const commentDraft = ref('')
const commentSubmitting = ref(false)
const deletingCommentId = ref(null)
const reportOpen = ref(false)
const reportSubmitting = ref(false)
const reportDraft = reactive({
  reason: 'spam',
  details: '',
})

const resetCommentState = () => {
  comments.value = []
  commentsTotal.value = 0
  commentsLoading.value = false
  commentsLoadingMore.value = false
  commentsError.value = ''
  commentDraft.value = ''
  commentSubmitting.value = false
  deletingCommentId.value = null
}

const resetReportState = () => {
  reportOpen.value = false
  reportSubmitting.value = false
  reportDraft.reason = 'spam'
  reportDraft.details = ''
}

const handleDelete = (emoji) => {
  emit('delete', emoji)
}

const handleUpdate = (emoji, payload) => {
  emit('update', emoji, payload)
}

const handleToggleLike = (emoji) => {
  emit('toggle-like', emoji)
}

const loadComments = async ({ append = false } = {}) => {
  if (!selectedEmoji.value) return

  const offset = append ? comments.value.length : 0
  commentsError.value = ''
  if (append) {
    commentsLoadingMore.value = true
  } else {
    commentsLoading.value = true
  }

  try {
    const response = await fetchEmojiComments(selectedEmoji.value.id, token.value, {
      limit: COMMENTS_PAGE_SIZE,
      offset,
    })
    const nextItems = response.items ?? []
    comments.value = append ? [...comments.value, ...nextItems] : nextItems
    commentsTotal.value = response.total ?? nextItems.length
    if (selectedEmoji.value) {
      selectedEmoji.value.comment_count = commentsTotal.value
    }
  } catch (error) {
    commentsError.value = error.message ?? 'Failed to load comments'
  } finally {
    commentsLoading.value = false
    commentsLoadingMore.value = false
  }
}

const handleEmojiClick = (emoji) => {
  selectedEmoji.value = emoji
}

const handleSaveToCollection = (emoji) => {
  collectionPickerEmoji.value = emoji
}

const closeModal = () => {
  selectedEmoji.value = null
  collectionPickerEmoji.value = null
  modalCopied.value = false
  resetCommentState()
  resetReportState()
}

const copyEmojiFromModal = async () => {
  if (!selectedEmoji.value) return
  try {
    await navigator.clipboard.writeText(selectedEmoji.value.symbol)
    modalCopied.value = true
    setTimeout(() => {
      modalCopied.value = false
    }, 1500)
  } catch {
    addToast('Failed to copy emoji', 'error')
  }
}

const handleCollectionsSaved = ({ collectionIds, createdCollection } = {}) => {
  const name = createdCollection?.name || createdCollection?.title
  if (name) {
    addToast(`Saved to ${name}`)
  } else if (collectionIds?.length) {
    addToast(`Saved to ${collectionIds.length} collection${collectionIds.length === 1 ? '' : 's'}`)
  } else {
    addToast('Saved to collections')
  }
  collectionPickerEmoji.value = null
}

const closeCollectionPicker = () => {
  collectionPickerEmoji.value = null
}

const openReportModal = () => {
  if (!props.isAuthenticated) {
    addToast('Log in to report emojis.', 'error')
    return
  }
  reportOpen.value = true
}

const closeReportModal = () => {
  resetReportState()
}

const submitReport = async () => {
  if (!selectedEmoji.value || !props.isAuthenticated) {
    addToast('Log in to report emojis.', 'error')
    return
  }

  reportSubmitting.value = true
  try {
    await reportEmoji(
      selectedEmoji.value.id,
      {
        reason: reportDraft.reason,
        details: reportDraft.details || undefined,
      },
      token.value,
    )
    addToast('Report submitted for review.')
    closeReportModal()
  } catch (error) {
    addToast(error.message ?? 'Failed to submit report', 'error')
  } finally {
    reportSubmitting.value = false
  }
}

const getCategoryTheme = (category) => categoryThemes[category] || categoryThemes.default

const getModalStyle = (emoji) => {
  const theme = getCategoryTheme(emoji?.category)
  return {
    '--modal-accent': theme.accent,
    '--modal-accent-soft': theme.accentSoft,
    '--modal-accent-strong': theme.accentStrong,
    '--modal-glow': theme.glow,
  }
}

const formatDate = (value) => {
  if (!value) return ''
  return new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const submitComment = async () => {
  if (!selectedEmoji.value || !props.isAuthenticated) {
    addToast('Log in to join the conversation.', 'error')
    return
  }

  const body = commentDraft.value.trim()
  if (!body) {
    addToast('Comment cannot be blank.', 'error')
    return
  }

  commentSubmitting.value = true
  try {
    const created = await createEmojiComment(
      selectedEmoji.value.id,
      { body },
      token.value,
    )
    comments.value = [...comments.value, created]
    commentsTotal.value += 1
    selectedEmoji.value.comment_count = commentsTotal.value
    commentDraft.value = ''
  } catch (error) {
    addToast(error.message ?? 'Failed to post comment', 'error')
  } finally {
    commentSubmitting.value = false
  }
}

const handleDeleteComment = async (comment) => {
  if (!props.isAuthenticated) return

  deletingCommentId.value = comment.id
  try {
    await deleteEmojiComment(comment.id, token.value)
    comments.value = comments.value.filter((item) => item.id !== comment.id)
    commentsTotal.value = Math.max(0, commentsTotal.value - 1)
    if (selectedEmoji.value) {
      selectedEmoji.value.comment_count = commentsTotal.value
    }
  } catch (error) {
    addToast(error.message ?? 'Failed to delete comment', 'error')
  } finally {
    deletingCommentId.value = null
  }
}

watch(selectedEmoji, (emoji) => {
  resetCommentState()
  resetReportState()
  if (emoji) {
    loadComments()
  }
})
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
          :is-authenticated="isAuthenticated"
          @delete="handleDelete"
          @update="handleUpdate"
          @toggle-like="handleToggleLike"
          @save-to-collection="handleSaveToCollection"
        />
      </div>
    </div>

    <Teleport to="body">
      <Transition name="modal">
        <div v-if="selectedEmoji" class="modal-overlay" role="dialog" aria-modal="true" @click="closeModal" @keydown.escape="closeModal">
          <div class="modal-content" :style="getModalStyle(selectedEmoji)" @click.stop>
            <button class="modal-close" @click="closeModal" aria-label="Close">✕</button>
            <div class="modal-layout">
              <aside class="modal-hero">
                <div class="modal-hero-top">
                  <span class="category-badge">{{ selectedEmoji.category || 'Curated' }}</span>
                  <button
                    type="button"
                    class="modal-copy-btn"
                    :class="{ copied: modalCopied }"
                    @click="copyEmojiFromModal"
                  >
                    {{ modalCopied ? 'Copied!' : 'Copy emoji' }}
                  </button>
                </div>

                <div class="modal-symbol-stage" aria-hidden="true">
                  <div class="modal-symbol-orb"></div>
                  <div class="emoji-symbol">{{ selectedEmoji.symbol }}</div>
                </div>

                <div class="modal-stat-grid">
                  <button
                    type="button"
                    class="modal-stat-card modal-like-btn"
                    :class="{ liked: selectedEmoji.is_liked, disabled: !isAuthenticated }"
                    :title="isAuthenticated ? (selectedEmoji.is_liked ? 'Unlike emoji' : 'Like emoji') : 'Log in to like'"
                    @click="handleToggleLike(selectedEmoji)"
                  >
                    <span class="modal-stat-icon">{{ selectedEmoji.is_liked ? '\u2764\uFE0F' : '\u2661' }}</span>
                    <span class="modal-stat-value">{{ selectedEmoji.like_count || 0 }}</span>
                    <span class="modal-stat-label">{{ selectedEmoji.is_liked ? 'Liked' : 'Likes' }}</span>
                  </button>

                  <div class="modal-stat-card modal-comment-count">
                    <span class="modal-stat-icon">💬</span>
                    <span class="modal-stat-value">{{ selectedEmoji.comment_count || 0 }}</span>
                    <span class="modal-stat-label">Comments</span>
                  </div>
                </div>

                <dl class="modal-facts">
                  <div v-if="selectedEmoji.submitter_name" class="modal-fact">
                    <dt>Creator</dt>
                    <dd>{{ selectedEmoji.submitter_name }}</dd>
                  </div>
                  <div v-if="selectedEmoji.created_at" class="modal-fact">
                    <dt>Added</dt>
                    <dd>{{ formatDate(selectedEmoji.created_at) }}</dd>
                  </div>
                </dl>
              </aside>

              <div class="modal-body">
                <div class="modal-title-block">
                  <p class="modal-kicker">Emoji details</p>
                  <h2>{{ selectedEmoji.title }}</h2>
                  <p v-if="selectedEmoji.description" class="emoji-description">
                    {{ selectedEmoji.description }}
                  </p>
                  <p v-else class="emoji-description empty-description">
                    No description yet, but the visual is doing the talking.
                  </p>
                </div>

                <div v-if="selectedEmoji.keywords?.length" class="emoji-keywords">
                  <span v-for="keyword in selectedEmoji.keywords" :key="keyword" class="keyword-tag">
                    #{{ keyword }}
                  </span>
                </div>

                <div class="modal-actions-row">
                  <button
                    type="button"
                    class="modal-collection-btn"
                    @click.stop="handleSaveToCollection(selectedEmoji)"
                  >
                    Save to collection
                  </button>
                  <button
                    v-if="isAuthenticated"
                    type="button"
                    class="modal-report-btn"
                    @click.stop="openReportModal"
                  >
                    Report emoji
                  </button>
                </div>

                <section class="comments-shell">
                  <div class="comments-head">
                    <div>
                      <p class="comments-kicker">Community notes</p>
                      <h3>Comments</h3>
                    </div>
                    <span>{{ commentsTotal }} total</span>
                  </div>

                  <div v-if="commentsLoading" class="comments-status">Loading comments…</div>
                  <div v-else-if="commentsError" class="comments-status error">{{ commentsError }}</div>
                  <div v-else-if="!comments.length" class="comments-status">No comments yet.</div>
                  <div v-else class="comments-list">
                    <article v-for="comment in comments" :key="comment.id" class="comment-card">
                      <div class="comment-top">
                        <div>
                          <strong>{{ comment.author_name || 'Anonymous' }}</strong>
                          <p>{{ new Date(comment.created_at).toLocaleString() }}</p>
                        </div>
                        <button
                          v-if="comment.can_delete"
                          type="button"
                          class="comment-delete-btn"
                          :disabled="deletingCommentId === comment.id"
                          @click="handleDeleteComment(comment)"
                        >
                          {{ deletingCommentId === comment.id ? 'Deleting…' : 'Delete' }}
                        </button>
                      </div>
                      <p class="comment-body">{{ comment.body }}</p>
                    </article>
                  </div>

                  <button
                    v-if="comments.length < commentsTotal"
                    type="button"
                    class="load-more-btn"
                    :disabled="commentsLoadingMore"
                    @click="loadComments({ append: true })"
                  >
                    {{ commentsLoadingMore ? 'Loading…' : 'Load more comments' }}
                  </button>

                  <div v-if="isAuthenticated" class="comment-composer">
                    <textarea
                      v-model="commentDraft"
                      rows="3"
                      maxlength="500"
                      placeholder="Share what you think about this emoji..."
                    />
                    <div class="comment-actions">
                      <span>{{ commentDraft.trim().length }}/500</span>
                      <button type="button" class="comment-submit-btn" :disabled="commentSubmitting" @click="submitComment">
                        {{ commentSubmitting ? 'Posting…' : 'Post comment' }}
                      </button>
                    </div>
                  </div>
                  <div v-else class="comment-gate">
                    Log in to comment on approved emojis.
                  </div>
                </section>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <Transition name="modal">
        <div v-if="reportOpen && selectedEmoji" class="modal-overlay report-overlay" role="dialog" aria-modal="true" @click="closeReportModal" @keydown.escape="closeReportModal">
          <div class="report-modal" @click.stop>
            <button class="modal-close" @click="closeReportModal" aria-label="Close">✕</button>
            <h3>Report {{ selectedEmoji.title }}</h3>
            <p class="report-copy">
              Help moderators review approved emojis that may need another look.
            </p>
            <label class="report-field">
              Reason
              <select v-model="reportDraft.reason">
                <option v-for="option in REPORT_REASONS" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
            <label class="report-field">
              Details
              <textarea
                v-model="reportDraft.details"
                rows="4"
                maxlength="500"
                placeholder="Optional details for the moderation team"
              />
            </label>
            <div class="report-actions">
              <button type="button" class="secondary-btn" @click="closeReportModal">Cancel</button>
              <button type="button" class="primary-btn" :disabled="reportSubmitting" @click="submitReport">
                {{ reportSubmitting ? 'Submitting…' : 'Submit report' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <CollectionPickerDialog
      :open="Boolean(collectionPickerEmoji)"
      :emoji="collectionPickerEmoji"
      :is-authenticated="isAuthenticated"
      @close="closeCollectionPicker"
      @saved="handleCollectionsSaved"
    />
  </section>
</template>

<style scoped>
.grid-container {
  position: relative;
  width: 100%;
}

.emoji-grid {
  display: grid;
  gap: 1.75rem;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  align-items: stretch;
}

@media (min-width: 1200px) {
  .emoji-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.emoji-item {
  cursor: pointer;
  min-width: 0;
  animation: cardRise 0.45s ease both;
}

.emoji-item:hover {
  z-index: 10;
}

.emoji-item:nth-child(2n) {
  animation-delay: 0.04s;
}

.emoji-item:nth-child(3n) {
  animation-delay: 0.08s;
}

.emoji-item:nth-child(4n) {
  animation-delay: 0.12s;
}

.empty {
  text-align: center;
  color: #6b7280;
  padding: 3rem;
}

@keyframes cardRise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
  backdrop-filter: blur(4px);
}

.modal-content,
.report-modal {
  position: relative;
  background: var(--color-bg-solid);
  border-radius: 1.5rem;
  width: min(1080px, 100%);
  box-shadow: var(--shadow-modal);
  animation: scaleIn 0.3s ease-out;
}

.modal-content {
  padding: 1rem;
  max-height: 90vh;
  overflow-y: auto;
  background:
    radial-gradient(circle at top right, var(--modal-accent-soft, rgba(99, 102, 241, 0.12)), transparent 22%),
    linear-gradient(180deg, color-mix(in srgb, var(--color-bg-solid) 94%, white 6%), var(--color-bg-solid));
}

.report-modal {
  padding: 2rem;
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
  top: 1.1rem;
  right: 1.1rem;
  background: color-mix(in srgb, var(--color-bg-solid) 80%, transparent);
  border: 1px solid var(--color-border);
  font-size: 1.4rem;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  z-index: 3;
}

.modal-layout {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  gap: 1rem;
  min-height: min(740px, calc(90vh - 2rem));
}

.modal-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.35rem;
  border-radius: 1.35rem;
  overflow: hidden;
  background:
    radial-gradient(circle at top, var(--modal-accent-strong, rgba(99, 102, 241, 0.24)), transparent 42%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.74));
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
}

[data-theme="dark"] .modal-hero {
  background:
    radial-gradient(circle at top, var(--modal-accent-strong, rgba(99, 102, 241, 0.24)), transparent 42%),
    linear-gradient(180deg, rgba(24, 24, 36, 0.95), rgba(17, 24, 39, 0.88));
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.modal-hero-top {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 0.75rem;
}

.modal-symbol-stage {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 280px;
  padding: 1rem;
  border-radius: 1.5rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.48), rgba(255, 255, 255, 0.12)),
    radial-gradient(circle at 50% 35%, var(--modal-accent-soft, rgba(99, 102, 241, 0.16)), transparent 58%);
  overflow: hidden;
}

[data-theme="dark"] .modal-symbol-stage {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)),
    radial-gradient(circle at 50% 35%, var(--modal-accent-soft, rgba(99, 102, 241, 0.16)), transparent 58%);
}

.modal-symbol-orb {
  position: absolute;
  inset: 16% 12%;
  border-radius: 50%;
  background: var(--modal-glow, radial-gradient(circle, rgba(255, 255, 255, 0.9), transparent 72%));
  filter: blur(1px);
}

.emoji-symbol {
  position: relative;
  font-size: clamp(5.5rem, 10vw, 8rem);
  line-height: 1;
  animation: bounceIn 0.5s ease-out;
  z-index: 1;
}

.modal-copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.65rem 1rem;
  border: 1px solid color-mix(in srgb, var(--modal-accent, #6366f1) 16%, var(--color-border-light));
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-bg-solid) 82%, transparent);
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.modal-copy-btn:hover,
.primary-btn:hover,
.comment-submit-btn:hover,
.modal-report-btn:hover,
.modal-collection-btn:hover,
.load-more-btn:hover,
.comment-delete-btn:hover,
.secondary-btn:hover {
  filter: brightness(0.98);
}

.modal-copy-btn.copied {
  background: var(--color-text-success);
  color: white;
  border-color: var(--color-text-success);
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

.modal-body h2,
.report-modal h3 {
  font-size: clamp(2.2rem, 4vw, 3.3rem);
  line-height: 0.95;
  letter-spacing: -0.04em;
  margin: 0;
  color: var(--color-text-heading);
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}

.modal-title-block {
  padding: 1.35rem 3.4rem 1rem 1.2rem;
}

.modal-kicker,
.comments-kicker {
  margin: 0 0 0.55rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--modal-accent, var(--color-text-link));
}

.emoji-description,
.report-copy {
  color: var(--color-text-muted);
  font-size: 1.02rem;
  max-width: 62ch;
  margin: 1rem 0 0;
  line-height: 1.6;
}

.empty-description {
  font-style: italic;
}

.category-badge {
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  padding: 0.42rem 0.95rem;
  background: color-mix(in srgb, var(--modal-accent, #6366f1) 14%, white);
  color: color-mix(in srgb, var(--modal-accent, #6366f1) 76%, var(--color-text-heading));
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--modal-accent, #6366f1) 20%, transparent);
  font-weight: 700;
  font-size: 0.84rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

[data-theme="dark"] .category-badge {
  background: color-mix(in srgb, var(--modal-accent, #6366f1) 20%, rgba(15, 23, 42, 0.65));
  color: #f8fafc;
}

.emoji-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  padding: 0 1.2rem;
}

.keyword-tag {
  padding: 0.48rem 0.82rem;
  background: color-mix(in srgb, var(--modal-accent, #6366f1) 10%, var(--color-bg-surface-raised));
  color: color-mix(in srgb, var(--modal-accent, #6366f1) 78%, var(--color-text-link));
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--modal-accent, #6366f1) 14%, var(--color-border));
  font-size: 0.88rem;
  font-weight: 600;
}

.modal-actions-row,
.comment-actions,
.report-actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.modal-actions-row {
  padding: 0 1.2rem;
}

.modal-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.modal-stat-card {
  display: grid;
  justify-items: start;
  gap: 0.2rem;
  padding: 1rem;
  border-radius: 1.15rem;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.5);
  color: var(--color-text);
  text-align: left;
}

[data-theme="dark"] .modal-stat-card {
  background: rgba(15, 23, 42, 0.38);
}

.modal-like-btn {
  cursor: pointer;
}

.modal-like-btn.liked {
  border-color: color-mix(in srgb, var(--modal-accent, #6366f1) 26%, transparent);
  background: color-mix(in srgb, var(--modal-accent, #6366f1) 12%, rgba(255, 255, 255, 0.5));
}

.modal-like-btn.disabled {
  cursor: default;
  opacity: 0.6;
}

.modal-comment-count {
  background: color-mix(in srgb, var(--modal-accent, #6366f1) 7%, rgba(255, 255, 255, 0.5));
}

.modal-stat-icon {
  font-size: 1.1rem;
}

.modal-stat-value {
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--color-text-heading);
}

.modal-stat-label {
  color: var(--color-text-secondary);
  font-size: 0.84rem;
  font-weight: 600;
}

.modal-facts {
  display: grid;
  gap: 0.75rem;
  margin: 0;
}

.modal-fact {
  display: grid;
  gap: 0.12rem;
  padding: 0.95rem 1rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.48);
  border: 1px solid var(--color-border);
}

[data-theme="dark"] .modal-fact {
  background: rgba(15, 23, 42, 0.35);
}

.modal-fact dt,
.modal-fact dd {
  margin: 0;
}

.modal-fact dt {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.modal-fact dd {
  color: var(--color-text-heading);
  font-weight: 600;
}

.modal-collection-btn,
.modal-report-btn,
.secondary-btn,
.primary-btn,
.comment-submit-btn,
.load-more-btn,
.comment-delete-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-weight: 700;
  cursor: pointer;
}

.modal-collection-btn,
.modal-report-btn {
  padding: 0.85rem 1.25rem;
}

.modal-collection-btn {
  border: none;
  background: linear-gradient(135deg, var(--modal-accent, #6366f1), color-mix(in srgb, var(--modal-accent, #6366f1) 58%, #f97316));
  color: white;
  box-shadow: 0 14px 28px color-mix(in srgb, var(--modal-accent, #6366f1) 22%, transparent);
}

.modal-report-btn,
.primary-btn,
.comment-submit-btn {
  border: 1px solid var(--color-border);
  background: var(--color-bg-solid);
  color: var(--color-text);
}

.comments-shell {
  display: grid;
  gap: 1rem;
  padding: 1.4rem 1.2rem 1.2rem;
  border: 1px solid var(--color-border);
  border-radius: 1.35rem;
  background:
    linear-gradient(180deg, var(--color-bg-surface-raised), var(--color-bg-solid)),
    linear-gradient(135deg, var(--modal-accent-soft, rgba(99, 102, 241, 0.1)), transparent 60%);
  text-align: left;
}

.comments-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.comments-head h3 {
  margin: 0;
  font-size: 1.3rem;
  color: var(--color-text-heading);
}

.comments-head span {
  color: var(--color-text-secondary);
  font-weight: 600;
}

.comments-status,
.comment-gate {
  padding: 1rem 1.1rem;
  border-radius: 1rem;
  background: var(--color-bg-surface-raised);
  color: var(--color-text-secondary);
}

.comments-status.error {
  color: var(--color-text-error);
}

.comments-list {
  display: grid;
  gap: 0.9rem;
}

.comment-card {
  padding: 1rem 1.1rem;
  border-radius: 1rem;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
}

.comment-top {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.comment-top strong {
  display: block;
}

.comment-top p,
.comment-body {
  margin: 0;
}

.comment-top p {
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

.comment-body {
  color: var(--color-text);
  line-height: 1.6;
  white-space: pre-wrap;
}

.comment-delete-btn,
.load-more-btn,
.secondary-btn {
  border: 1px solid var(--color-border);
  background: var(--color-bg-solid);
  color: var(--color-text);
  padding: 0.55rem 1rem;
}

.load-more-btn {
  margin-top: 0.9rem;
}

.comment-composer,
.report-field {
  display: grid;
  gap: 0.6rem;
}

.comment-composer {
  margin-top: 1rem;
}

.comment-composer textarea,
.report-field textarea,
.report-field select {
  width: 100%;
  border-radius: 1rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-input);
  color: var(--color-text);
  font: inherit;
  padding: 0.85rem 1rem;
}

.comment-actions {
  justify-content: space-between;
}

.comment-actions span {
  color: var(--color-text-secondary);
  font-size: 0.88rem;
}

.report-actions {
  margin-top: 1rem;
  justify-content: flex-end;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .modal-layout {
    grid-template-columns: 1fr;
  }

  .modal-title-block {
    padding-right: 3.2rem;
  }

  .modal-symbol-stage {
    min-height: 220px;
  }
}

@media (max-width: 640px) {
  .emoji-grid {
    gap: 1rem;
    grid-template-columns: 1fr;
  }

  .modal-content,
  .report-modal {
    padding: 0.75rem;
    border-radius: 1.25rem;
  }

  .modal-hero,
  .comments-shell {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .modal-title-block,
  .emoji-keywords,
  .modal-actions-row {
    padding-left: 0.25rem;
    padding-right: 0.25rem;
  }

  .modal-title-block {
    padding-top: 0.75rem;
  }

  .modal-stat-grid {
    grid-template-columns: 1fr;
  }

  .emoji-symbol {
    font-size: 5.25rem;
  }

  .report-actions {
    justify-content: stretch;
  }
}
</style>
