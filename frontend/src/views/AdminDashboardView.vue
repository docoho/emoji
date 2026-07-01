<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { fetchAdminDashboard } from '../services/api'

const router = useRouter()
const { token, user, signOut } = useAuth()
const { addToast } = useToast()

const dashboard = ref(null)
const loading = ref(true)

const formatNumber = (value) => new Intl.NumberFormat().format(value ?? 0)

const formatDate = (value) => {
  if (!value) return '-'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

const statusLabel = (value) => value.replace(/_/g, ' ')

const handleUnauthorized = () => {
  signOut()
  addToast('Please log in to access the admin dashboard.', 'error')
  router.replace({ name: 'login' })
}

const handleForbidden = () => {
  addToast('You do not have access to the admin dashboard.', 'error')
  router.replace({ name: 'home' })
}

const handleAdminError = (error) => {
  if (error.status === 401) {
    handleUnauthorized()
    return
  }
  if (error.status === 403) {
    handleForbidden()
    return
  }
  addToast(error.message ?? 'Failed to load admin dashboard.', 'error')
}

const loadDashboard = async () => {
  if (!token.value) {
    handleUnauthorized()
    return
  }

  loading.value = true
  try {
    dashboard.value = await fetchAdminDashboard(token.value)
  } catch (error) {
    handleAdminError(error)
  } finally {
    loading.value = false
  }
}

const metricCards = computed(() => {
  const data = dashboard.value ?? {}
  return [
    {
      label: 'Pending emojis',
      value: data.pending_emojis,
      note: `${formatNumber(data.approved_emojis)} approved`,
      tone: 'warning',
    },
    {
      label: 'Open reports',
      value: data.open_reports,
      note: `${formatNumber(data.actioned_reports)} actioned`,
      tone: 'danger',
    },
    {
      label: 'Users',
      value: data.total_users,
      note: `${formatNumber(data.active_users)} active`,
      tone: 'neutral',
    },
    {
      label: 'Engagement',
      value: data.total_likes,
      note: `${formatNumber(data.total_comments)} comments`,
      tone: 'success',
    },
  ]
})

const activityCards = computed(() => {
  const data = dashboard.value ?? {}
  return [
    { label: 'New users', value: data.new_users_7d },
    { label: 'New emojis', value: data.new_emojis_7d },
    { label: 'New reports', value: data.new_reports_7d },
    { label: 'Collections', value: data.total_collections },
  ]
})

const maxEmojiStatus = computed(() => {
  const counts = dashboard.value?.emoji_status_counts ?? []
  return Math.max(1, ...counts.map((item) => item.count))
})

const maxReportStatus = computed(() => {
  const counts = dashboard.value?.report_status_counts ?? []
  return Math.max(1, ...counts.map((item) => item.count))
})

watch(user, () => {
  if (user.value && !user.value.is_superuser) {
    handleForbidden()
  }
})

onMounted(() => {
  if (user.value && !user.value.is_superuser) {
    handleForbidden()
    return
  }
  loadDashboard()
})
</script>

<template>
  <main class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Admin dashboard</p>
        <h1>Platform health</h1>
        <p class="intro">A working snapshot of moderation load, community activity, and content volume.</p>
      </div>
      <div class="header-actions">
        <RouterLink class="secondary-link" :to="{ name: 'admin-moderation' }">
          Moderation queue
        </RouterLink>
        <button type="button" class="refresh-btn" :disabled="loading" @click="loadDashboard">
          {{ loading ? 'Refreshing' : 'Refresh' }}
        </button>
      </div>
    </header>

    <p v-if="loading && !dashboard" class="status-message">Loading admin dashboard...</p>

    <template v-else-if="dashboard">
      <section class="metric-grid" aria-label="Admin metrics">
        <article
          v-for="metric in metricCards"
          :key="metric.label"
          class="metric-card"
          :class="metric.tone"
        >
          <p>{{ metric.label }}</p>
          <strong>{{ formatNumber(metric.value) }}</strong>
          <span>{{ metric.note }}</span>
        </article>
      </section>

      <section class="dashboard-grid">
        <article class="panel">
          <div class="panel-heading">
            <h2>Seven-day activity</h2>
          </div>
          <div class="activity-list">
            <div v-for="item in activityCards" :key="item.label" class="activity-row">
              <span>{{ item.label }}</span>
              <strong>{{ formatNumber(item.value) }}</strong>
            </div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-heading">
            <h2>Emoji status</h2>
          </div>
          <div class="bar-list">
            <div v-for="item in dashboard.emoji_status_counts" :key="item.status" class="bar-row">
              <div class="bar-meta">
                <span>{{ statusLabel(item.status) }}</span>
                <strong>{{ formatNumber(item.count) }}</strong>
              </div>
              <div class="bar-track">
                <span class="bar-fill emoji" :style="{ width: `${(item.count / maxEmojiStatus) * 100}%` }" />
              </div>
            </div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-heading">
            <h2>Report status</h2>
          </div>
          <div class="bar-list">
            <div v-for="item in dashboard.report_status_counts" :key="item.status" class="bar-row">
              <div class="bar-meta">
                <span>{{ statusLabel(item.status) }}</span>
                <strong>{{ formatNumber(item.count) }}</strong>
              </div>
              <div class="bar-track">
                <span class="bar-fill report" :style="{ width: `${(item.count / maxReportStatus) * 100}%` }" />
              </div>
            </div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-heading">
            <h2>Top categories</h2>
          </div>
          <p v-if="!dashboard.top_categories.length" class="empty-text">No approved categories yet.</p>
          <div v-else class="category-list">
            <div v-for="item in dashboard.top_categories" :key="item.category" class="activity-row">
              <span>{{ item.category }}</span>
              <strong>{{ formatNumber(item.count) }}</strong>
            </div>
          </div>
        </article>
      </section>

      <section class="work-grid">
        <article class="panel">
          <div class="panel-heading">
            <h2>Recent pending emojis</h2>
            <RouterLink :to="{ name: 'admin-moderation' }">View all</RouterLink>
          </div>
          <p v-if="!dashboard.recent_pending_emojis.length" class="empty-text">No pending submissions.</p>
          <div v-else class="work-list">
            <div v-for="item in dashboard.recent_pending_emojis" :key="item.id" class="work-row">
              <span class="emoji-symbol">{{ item.symbol }}</span>
              <div>
                <strong>{{ item.title }}</strong>
                <span>
                  {{ item.submitter_name || 'Unknown submitter' }} · {{ formatDate(item.created_at) }}
                </span>
              </div>
            </div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-heading">
            <h2>Recent open reports</h2>
            <RouterLink :to="{ name: 'admin-moderation' }">View all</RouterLink>
          </div>
          <p v-if="!dashboard.recent_open_reports.length" class="empty-text">No open reports.</p>
          <div v-else class="work-list">
            <div v-for="item in dashboard.recent_open_reports" :key="item.id" class="work-row">
              <span class="emoji-symbol">{{ item.emoji_symbol }}</span>
              <div>
                <strong>{{ item.emoji_title }}</strong>
                <span>
                  {{ statusLabel(item.reason) }} · {{ item.reporter_name || 'Unknown reporter' }}
                </span>
              </div>
            </div>
          </div>
        </article>
      </section>
    </template>
  </main>
</template>

<style scoped>
.admin-page {
  min-height: 100vh;
  padding: 1.5rem 1rem 2.5rem;
  background: var(--bg-page-2);
  color: var(--color-text);
}

.page-header,
.metric-grid,
.dashboard-grid,
.work-grid,
.status-message {
  width: min(1180px, 100%);
  margin-inline: auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.eyebrow {
  margin: 0 0 0.25rem;
  color: var(--color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

.page-header h1 {
  margin: 0;
  color: var(--color-text-heading);
  font-size: clamp(1.8rem, 3vw, 2.5rem);
}

.intro {
  max-width: 42rem;
  margin: 0.55rem 0 0;
  color: var(--color-text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.secondary-link,
.refresh-btn {
  min-height: 2.5rem;
  border-radius: 8px;
  font-weight: 700;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  padding: 0 0.95rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface-solid);
  color: var(--color-text-heading);
}

.refresh-btn {
  border: none;
  background: #2563eb;
  color: #fff;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.9rem;
  margin-bottom: 1rem;
}

.metric-card,
.panel {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface-solid);
  box-shadow: var(--shadow-card);
}

.metric-card {
  padding: 1rem;
  border-left: 4px solid #64748b;
}

.metric-card.warning {
  border-left-color: #ca8a04;
}

.metric-card.danger {
  border-left-color: #dc2626;
}

.metric-card.success {
  border-left-color: #059669;
}

.metric-card p,
.metric-card span {
  margin: 0;
  color: var(--color-text-secondary);
}

.metric-card strong {
  display: block;
  margin: 0.35rem 0;
  color: var(--color-text-heading);
  font-size: 2rem;
  line-height: 1;
}

.dashboard-grid,
.work-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.panel {
  padding: 1rem;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.9rem;
}

.panel-heading h2 {
  margin: 0;
  color: var(--color-text-heading);
  font-size: 1rem;
}

.activity-list,
.bar-list,
.category-list,
.work-list {
  display: grid;
  gap: 0.75rem;
}

.activity-row,
.bar-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.activity-row span,
.bar-meta span,
.work-row span {
  color: var(--color-text-secondary);
}

.activity-row strong,
.bar-meta strong,
.work-row strong {
  color: var(--color-text-heading);
}

.bar-track {
  height: 0.5rem;
  margin-top: 0.35rem;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-tag-bg);
}

.bar-fill {
  display: block;
  height: 100%;
  min-width: 0.25rem;
  border-radius: inherit;
}

.bar-fill.emoji {
  background: #2563eb;
}

.bar-fill.report {
  background: #dc2626;
}

.work-row {
  display: grid;
  grid-template-columns: 2.5rem minmax(0, 1fr);
  gap: 0.75rem;
  align-items: center;
  padding: 0.75rem 0;
  border-top: 1px solid var(--color-border-light);
}

.work-row:first-child {
  border-top: none;
  padding-top: 0;
}

.work-row div {
  min-width: 0;
}

.work-row strong,
.work-row span {
  display: block;
  overflow-wrap: anywhere;
}

.emoji-symbol {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  border-radius: 8px;
  background: var(--color-tag-bg);
  font-size: 1.4rem;
}

.empty-text,
.status-message {
  color: var(--color-text-secondary);
}

@media (max-width: 900px) {
  .page-header,
  .dashboard-grid,
  .work-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    display: grid;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .header-actions {
    width: 100%;
  }

  .secondary-link,
  .refresh-btn {
    flex: 1;
    justify-content: center;
  }
}
</style>
