<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import {
  fetchAdminEmojis,
  fetchAdminReports,
  moderateEmoji,
  updateAdminReport,
} from '../services/api'

const EMOJI_STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
]

const REPORT_STATUS_OPTIONS = [
  { value: 'open', label: 'Open' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: 'actioned', label: 'Actioned' },
]

const REPORT_REASON_OPTIONS = [
  { value: '', label: 'All reasons' },
  { value: 'spam', label: 'Spam' },
  { value: 'copyright', label: 'Copyright' },
  { value: 'offensive', label: 'Offensive' },
  { value: 'misleading', label: 'Misleading' },
  { value: 'other', label: 'Other' },
]

const CATEGORY_OPTIONS = [
  '',
  'People',
  'Nature',
  'Food',
  'Activities',
  'Travel',
  'Objects',
  'Symbols',
  'Flags',
]

const router = useRouter()
const { token, user, signOut } = useAuth()
const { addToast } = useToast()

const activeView = ref('emojis')

const emojiItems = ref([])
const emojiTotal = ref(0)
const emojiLoading = ref(true)
const emojiSubmittingId = ref(null)
const emojiSearchQuery = ref('')
const categoryFilter = ref('')
const emojiStatusFilter = ref('pending')
const emojiPage = ref(1)
const emojiPageSize = ref(10)
const reasonDrafts = ref({})

const reportItems = ref([])
const reportTotal = ref(0)
const reportLoading = ref(true)
const reportSubmittingId = ref(null)
const reportSearchQuery = ref('')
const reportStatusFilter = ref('open')
const reportReasonFilter = ref('')
const reportPage = ref(1)
const reportPageSize = ref(10)
const reportNoteDrafts = ref({})

const totalPages = computed(() => {
  const total = activeView.value === 'emojis' ? emojiTotal.value : reportTotal.value
  const size = activeView.value === 'emojis' ? emojiPageSize.value : reportPageSize.value
  return Math.max(1, Math.ceil(total / size))
})

const currentPage = computed(() => (
  activeView.value === 'emojis' ? emojiPage.value : reportPage.value
))

const handleUnauthorized = () => {
  signOut()
  addToast('Please log in to access moderation.', 'error')
  router.replace({ name: 'login' })
}

const handleForbidden = () => {
  addToast('You do not have access to the moderation dashboard.', 'error')
  router.replace({ name: 'home' })
}

const formatDate = (value) => {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

const handleAdminError = (error, fallbackMessage) => {
  if (error.status === 401) {
    handleUnauthorized()
    return true
  }
  if (error.status === 403) {
    handleForbidden()
    return true
  }
  addToast(error.message ?? fallbackMessage, 'error')
  return false
}

const loadEmojiQueue = async () => {
  if (!token.value) {
    handleUnauthorized()
    return
  }

  emojiLoading.value = true
  try {
    const response = await fetchAdminEmojis(token.value, {
      status: emojiStatusFilter.value,
      search: emojiSearchQuery.value || undefined,
      category: categoryFilter.value || undefined,
      limit: emojiPageSize.value,
      offset: (emojiPage.value - 1) * emojiPageSize.value,
    })
    emojiItems.value = response.items ?? []
    emojiTotal.value = response.total ?? 0
  } catch (error) {
    handleAdminError(error, 'Failed to load moderation queue.')
  } finally {
    emojiLoading.value = false
  }
}

const loadReportQueue = async () => {
  if (!token.value) {
    handleUnauthorized()
    return
  }

  reportLoading.value = true
  try {
    const response = await fetchAdminReports(token.value, {
      status: reportStatusFilter.value,
      reason: reportReasonFilter.value || undefined,
      search: reportSearchQuery.value || undefined,
      limit: reportPageSize.value,
      offset: (reportPage.value - 1) * reportPageSize.value,
    })
    reportItems.value = response.items ?? []
    reportTotal.value = response.total ?? 0
  } catch (error) {
    handleAdminError(error, 'Failed to load report queue.')
  } finally {
    reportLoading.value = false
  }
}

const loadActiveView = () => {
  if (activeView.value === 'emojis') {
    loadEmojiQueue()
  } else {
    loadReportQueue()
  }
}

const setView = (value) => {
  activeView.value = value
  loadActiveView()
}

const setEmojiStatus = (value) => {
  emojiStatusFilter.value = value
  emojiPage.value = 1
  loadEmojiQueue()
}

const setReportStatus = (value) => {
  reportStatusFilter.value = value
  reportPage.value = 1
  loadReportQueue()
}

const runEmojiSearch = () => {
  emojiPage.value = 1
  loadEmojiQueue()
}

const runReportSearch = () => {
  reportPage.value = 1
  loadReportQueue()
}

const nextPage = () => {
  if (currentPage.value >= totalPages.value) return
  if (activeView.value === 'emojis') {
    emojiPage.value += 1
    loadEmojiQueue()
  } else {
    reportPage.value += 1
    loadReportQueue()
  }
}

const prevPage = () => {
  if (currentPage.value <= 1) return
  if (activeView.value === 'emojis') {
    emojiPage.value -= 1
    loadEmojiQueue()
  } else {
    reportPage.value -= 1
    loadReportQueue()
  }
}

const reviewEmoji = async (emojiId, status) => {
  if (!token.value) {
    handleUnauthorized()
    return
  }

  emojiSubmittingId.value = emojiId
  try {
    await moderateEmoji(
      emojiId,
      {
        status,
        reason: status === 'rejected' ? reasonDrafts.value[emojiId] || null : null,
      },
      token.value,
    )
    reasonDrafts.value = {
      ...reasonDrafts.value,
      [emojiId]: '',
    }
    addToast(status === 'approved' ? 'Emoji approved.' : 'Emoji rejected.')
    await loadEmojiQueue()
  } catch (error) {
    handleAdminError(error, 'Failed to update moderation.')
  } finally {
    emojiSubmittingId.value = null
  }
}

const resolveReport = async (reportId, status) => {
  if (!token.value) {
    handleUnauthorized()
    return
  }

  reportSubmittingId.value = reportId
  try {
    await updateAdminReport(
      reportId,
      {
        status,
        admin_note: reportNoteDrafts.value[reportId] || null,
      },
      token.value,
    )
    reportNoteDrafts.value = {
      ...reportNoteDrafts.value,
      [reportId]: '',
    }
    addToast(status === 'dismissed' ? 'Report dismissed.' : 'Report marked actioned.')
    await loadReportQueue()
  } catch (error) {
    handleAdminError(error, 'Failed to update report.')
  } finally {
    reportSubmittingId.value = null
  }
}

watch(token, () => {
  if (token.value) {
    loadActiveView()
  }
})

onMounted(() => {
  if (user.value && !user.value.is_superuser) {
    handleForbidden()
    return
  }
  loadActiveView()
})
</script>

<template>
  <main class="page">
    <section class="hero">
      <p class="eyebrow">Admin moderation</p>
      <h1>Community review center</h1>
      <p class="intro">
        Review submitted emojis, process community reports, and keep the public gallery healthy.
      </p>
    </section>

    <section class="controls">
      <div class="view-tabs">
        <RouterLink class="view-tab" :to="{ name: 'admin-dashboard' }">
          Overview
        </RouterLink>
        <button
          type="button"
          class="view-tab"
          :class="{ active: activeView === 'emojis' }"
          @click="setView('emojis')"
        >
          Emoji queue
        </button>
        <button
          type="button"
          class="view-tab"
          :class="{ active: activeView === 'reports' }"
          @click="setView('reports')"
        >
          Reports queue
        </button>
      </div>

      <template v-if="activeView === 'emojis'">
        <div class="status-tabs">
          <button
            v-for="option in EMOJI_STATUS_OPTIONS"
            :key="option.value"
            type="button"
            class="status-tab"
            :class="{ active: emojiStatusFilter === option.value }"
            @click="setEmojiStatus(option.value)"
          >
            {{ option.label }}
          </button>
        </div>

        <div class="filter-row">
          <input
            v-model.trim="emojiSearchQuery"
            type="text"
            class="search-input"
            placeholder="Search by title, description, or keyword"
            @keyup.enter="runEmojiSearch"
          />
          <select v-model="categoryFilter" class="category-select" @change="runEmojiSearch">
            <option value="">All categories</option>
            <option v-for="category in CATEGORY_OPTIONS.filter(Boolean)" :key="category" :value="category">
              {{ category }}
            </option>
          </select>
          <button type="button" class="search-btn" @click="runEmojiSearch">Apply</button>
        </div>
      </template>

      <template v-else>
        <div class="status-tabs">
          <button
            v-for="option in REPORT_STATUS_OPTIONS"
            :key="option.value"
            type="button"
            class="status-tab"
            :class="{ active: reportStatusFilter === option.value }"
            @click="setReportStatus(option.value)"
          >
            {{ option.label }}
          </button>
        </div>

        <div class="filter-row">
          <input
            v-model.trim="reportSearchQuery"
            type="text"
            class="search-input"
            placeholder="Search by emoji title, reporter name, or reporter email"
            @keyup.enter="runReportSearch"
          />
          <select v-model="reportReasonFilter" class="category-select" @change="runReportSearch">
            <option v-for="option in REPORT_REASON_OPTIONS" :key="option.value || 'all'" :value="option.value">
              {{ option.label }}
            </option>
          </select>
          <button type="button" class="search-btn" @click="runReportSearch">Apply</button>
        </div>
      </template>
    </section>

    <section class="queue-shell">
      <template v-if="activeView === 'emojis'">
        <p v-if="emojiLoading" class="status-message">Loading moderation queue…</p>
        <p v-else-if="!emojiItems.length" class="status-message">No emojis match this moderation view.</p>
        <div v-else class="queue-list">
          <article v-for="item in emojiItems" :key="item.id" class="queue-card">
            <div class="card-top">
              <div class="emoji-mark">{{ item.symbol }}</div>
              <div class="card-heading">
                <div class="title-row">
                  <h2>{{ item.title }}</h2>
                  <span class="status-badge" :class="item.moderation_status">
                    {{ item.moderation_status }}
                  </span>
                </div>
                <p class="meta-line">
                  Submitted {{ formatDate(item.created_at) }}
                  <span v-if="item.submitter_name || item.submitter_email">
                    by {{ item.submitter_name || item.submitter_email }}
                  </span>
                </p>
                <p v-if="item.category" class="meta-line">{{ item.category }}</p>
              </div>
            </div>

            <p v-if="item.description" class="description">{{ item.description }}</p>

            <ul v-if="item.keywords?.length" class="keywords">
              <li v-for="keyword in item.keywords" :key="keyword">#{{ keyword }}</li>
            </ul>

            <div class="audit">
              <span>{{ item.like_count }} likes</span>
              <span v-if="item.moderated_at">Reviewed {{ formatDate(item.moderated_at) }}</span>
              <span v-if="item.moderated_by_name">by {{ item.moderated_by_name }}</span>
            </div>

            <label class="reason-field">
              Internal rejection note
              <textarea
                v-model.trim="reasonDrafts[item.id]"
                rows="3"
                placeholder="Optional note for admins only"
              />
            </label>

            <p v-if="item.moderation_reason" class="saved-reason">
              Saved note: {{ item.moderation_reason }}
            </p>

            <div class="actions">
              <button
                type="button"
                class="approve-btn"
                :disabled="emojiSubmittingId === item.id"
                @click="reviewEmoji(item.id, 'approved')"
              >
                {{ emojiSubmittingId === item.id ? 'Saving…' : 'Approve' }}
              </button>
              <button
                type="button"
                class="reject-btn"
                :disabled="emojiSubmittingId === item.id"
                @click="reviewEmoji(item.id, 'rejected')"
              >
                {{ emojiSubmittingId === item.id ? 'Saving…' : 'Reject' }}
              </button>
            </div>
          </article>
        </div>
      </template>

      <template v-else>
        <p v-if="reportLoading" class="status-message">Loading report queue…</p>
        <p v-else-if="!reportItems.length" class="status-message">No reports match this view.</p>
        <div v-else class="queue-list">
          <article v-for="item in reportItems" :key="item.id" class="queue-card">
            <div class="card-top">
              <div class="emoji-mark">{{ item.emoji_symbol }}</div>
              <div class="card-heading">
                <div class="title-row">
                  <h2>{{ item.emoji_title }}</h2>
                  <span class="status-badge" :class="item.status">
                    {{ item.status }}
                  </span>
                </div>
                <p class="meta-line">
                  Reported {{ formatDate(item.created_at) }}
                  <span>by {{ item.reporter_name || item.reporter_email }}</span>
                </p>
                <p class="meta-line">Reason: {{ item.reason }}</p>
              </div>
            </div>

            <p v-if="item.details" class="description">{{ item.details }}</p>
            <p v-if="item.admin_note" class="saved-reason">Admin note: {{ item.admin_note }}</p>

            <div class="audit">
              <span v-if="item.resolved_at">Resolved {{ formatDate(item.resolved_at) }}</span>
              <span v-if="item.resolved_by_name">by {{ item.resolved_by_name }}</span>
            </div>

            <label class="reason-field">
              Admin note
              <textarea
                v-model.trim="reportNoteDrafts[item.id]"
                rows="3"
                placeholder="Optional resolution note"
              />
            </label>

            <div class="actions">
              <button
                type="button"
                class="approve-btn"
                :disabled="reportSubmittingId === item.id"
                @click="resolveReport(item.id, 'dismissed')"
              >
                {{ reportSubmittingId === item.id ? 'Saving…' : 'Dismiss' }}
              </button>
              <button
                type="button"
                class="reject-btn"
                :disabled="reportSubmittingId === item.id"
                @click="resolveReport(item.id, 'actioned')"
              >
                {{ reportSubmittingId === item.id ? 'Saving…' : 'Actioned' }}
              </button>
            </div>
          </article>
        </div>
      </template>

      <div v-if="totalPages > 1" class="pagination">
        <button type="button" class="page-btn" :disabled="currentPage === 1" @click="prevPage">
          ← Previous
        </button>
        <span>
          Page {{ currentPage }} of {{ totalPages }} ·
          {{ activeView === 'emojis' ? emojiTotal : reportTotal }} items
        </span>
        <button type="button" class="page-btn" :disabled="currentPage >= totalPages" @click="nextPage">
          Next →
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 1.5rem 1rem 2rem;
  background:
    radial-gradient(circle at top left, rgba(248, 113, 113, 0.16), transparent 28rem),
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.14), transparent 24rem),
    linear-gradient(180deg, var(--bg-page-1), var(--bg-page-2));
  color: var(--color-text);
}

.hero,
.controls,
.queue-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.hero {
  margin-bottom: 1.5rem;
}

.eyebrow {
  margin: 0 0 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
  font-weight: 700;
  color: #b91c1c;
}

.hero h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
  color: var(--color-text-heading);
}

.intro {
  max-width: 46rem;
  margin: 0.75rem 0 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.controls {
  display: grid;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.view-tabs,
.status-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.view-tab,
.status-tab,
.search-btn,
.approve-btn,
.reject-btn,
.page-btn {
  border: none;
  border-radius: 999px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.view-tab,
.status-tab {
  display: inline-flex;
  align-items: center;
  padding: 0.7rem 1rem;
  background: rgba(15, 23, 42, 0.08);
  color: var(--color-text-secondary);
  text-decoration: none;
}

.view-tab.active,
.status-tab.active {
  background: linear-gradient(120deg, #dc2626, #ea580c);
  color: white;
  box-shadow: 0 14px 28px rgba(220, 38, 38, 0.22);
}

.filter-row {
  display: grid;
  gap: 0.75rem;
}

.search-input,
.category-select,
.reason-field textarea {
  width: 100%;
  border-radius: 1rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-input);
  color: var(--color-text);
  font: inherit;
}

.search-input,
.category-select {
  padding: 0.8rem 1rem;
}

.search-btn {
  padding: 0.8rem 1.2rem;
  background: linear-gradient(120deg, #1d4ed8, #0f766e);
  color: white;
}

.queue-shell {
  display: grid;
  gap: 1rem;
}

.status-message {
  margin: 0;
  padding: 1.25rem 1.5rem;
  border-radius: 1rem;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.queue-list {
  display: grid;
  gap: 1rem;
}

.queue-card {
  padding: 1.25rem;
  border-radius: 1.4rem;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.card-top {
  display: grid;
  gap: 1rem;
  align-items: start;
}

.emoji-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 5rem;
  height: 5rem;
  border-radius: 1.25rem;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.85), rgba(248, 250, 252, 0.5));
  font-size: 2.5rem;
}

.card-heading {
  min-width: 0;
}

.title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.title-row h2 {
  margin: 0;
  font-size: 1.35rem;
  color: var(--color-text-heading);
}

.status-badge {
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.status-badge.pending,
.status-badge.open {
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
}

.status-badge.approved,
.status-badge.dismissed {
  background: rgba(16, 185, 129, 0.14);
  color: #047857;
}

.status-badge.rejected,
.status-badge.actioned {
  background: rgba(220, 38, 38, 0.14);
  color: #b91c1c;
}

.meta-line,
.description,
.audit,
.saved-reason {
  margin: 0.55rem 0 0;
}

.meta-line,
.audit {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
}

.description {
  color: var(--color-text);
  line-height: 1.6;
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  list-style: none;
  padding: 0;
  margin: 0.9rem 0 0;
}

.keywords li {
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: var(--color-tag-bg);
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

.reason-field {
  display: grid;
  gap: 0.55rem;
  margin-top: 1rem;
  color: var(--color-text-secondary);
  font-weight: 600;
}

.reason-field textarea {
  padding: 0.9rem 1rem;
  resize: vertical;
}

.saved-reason {
  color: var(--color-text);
}

.actions,
.pagination {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: center;
}

.actions {
  margin-top: 1rem;
}

.approve-btn,
.reject-btn,
.page-btn {
  padding: 0.8rem 1.15rem;
}

.approve-btn {
  background: linear-gradient(120deg, #059669, #10b981);
  color: white;
}

.reject-btn {
  background: linear-gradient(120deg, #dc2626, #f97316);
  color: white;
}

.pagination {
  justify-content: center;
  padding: 0.5rem 0 1rem;
  color: var(--color-text-secondary);
}

.page-btn {
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.page-btn:disabled,
.approve-btn:disabled,
.reject-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (min-width: 780px) {
  .filter-row {
    grid-template-columns: minmax(0, 1fr) 220px auto;
  }

  .card-top {
    grid-template-columns: 5rem minmax(0, 1fr);
  }
}
</style>
