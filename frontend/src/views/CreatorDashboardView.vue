<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import EmojiSubmitForm from '../components/EmojiSubmitForm.vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import {
  createCreatorEmoji,
  deleteEmoji,
  duplicateCreatorEmoji,
  fetchCreatorAnalytics,
  fetchCreatorEmojis,
  submitCreatorEmoji,
  updateCreatorEmoji,
  updateCurrentUserProfile,
} from '../services/api'

const { token, user, setSession } = useAuth()
const { addToast } = useToast()

const loading = ref(true)
const error = ref('')
const savingProfile = ref(false)
const activeTab = ref('drafts')
const editingEmoji = ref(null)

const drafts = ref([])
const pendingItems = ref([])
const approvedItems = ref([])
const rejectedItems = ref([])
const analytics = ref({
  draft_count: 0,
  pending_count: 0,
  approved_count: 0,
  rejected_count: 0,
  total_likes_received: 0,
  top_emojis: [],
})

const profileForm = reactive({
  display_name: '',
  avatar_url: '',
  bio: '',
})

const allManagedItems = computed(() => [
  ...drafts.value,
  ...pendingItems.value,
  ...approvedItems.value,
  ...rejectedItems.value,
])

const submissionSections = computed(() => [
  {
    key: 'pending',
    title: 'Pending review',
    description: 'Items waiting for moderation.',
    items: pendingItems.value,
  },
  {
    key: 'rejected',
    title: 'Rejected',
    description: 'Needs changes before you resubmit.',
    items: rejectedItems.value,
  },
  {
    key: 'approved',
    title: 'Approved',
    description: 'Live entries already visible to the community.',
    items: approvedItems.value,
  },
])

const dashboardStats = computed(() => [
  { label: 'Drafts', value: analytics.value.draft_count, tone: 'rose' },
  { label: 'Pending', value: analytics.value.pending_count, tone: 'amber' },
  { label: 'Approved', value: analytics.value.approved_count, tone: 'sky' },
  { label: 'Rejected', value: analytics.value.rejected_count, tone: 'slate' },
  { label: 'Likes received', value: analytics.value.total_likes_received, tone: 'mint' },
])

const isEditing = computed(() => Boolean(editingEmoji.value))
const composerTitle = computed(() => {
  if (!editingEmoji.value) return 'Shape your next emoji'
  return `Edit ${editingEmoji.value.title}`
})
const composerDescription = computed(() => {
  if (!editingEmoji.value) {
    return 'Keep experiments private as drafts, then send your best work to moderation when it feels ready.'
  }
  if (editingEmoji.value.moderation_status === 'rejected') {
    return 'Refine the rejected emoji here, then use resubmit when you want it back in the review queue.'
  }
  return 'Update your creator entry without leaving the dashboard.'
})
const composerPrimaryLabel = computed(() => (editingEmoji.value ? 'Save changes' : 'Submit for review'))
const composerAllowsDraft = computed(() => !editingEmoji.value)

const profilePreviewInitial = computed(() => {
  const name = profileForm.display_name.trim() || user.value?.display_name || user.value?.email || '?'
  return name.charAt(0).toUpperCase()
})

const syncProfileForm = () => {
  profileForm.display_name = user.value?.display_name ?? ''
  profileForm.avatar_url = user.value?.avatar_url ?? ''
  profileForm.bio = user.value?.bio ?? ''
}

const refreshEditingEmoji = () => {
  if (!editingEmoji.value) return
  const nextValue = allManagedItems.value.find((item) => item.id === editingEmoji.value.id)
  editingEmoji.value = nextValue ?? null
}

const loadDashboard = async () => {
  loading.value = true
  error.value = ''

  try {
    const [draftResponse, pendingResponse, approvedResponse, rejectedResponse, analyticsResponse] = await Promise.all([
      fetchCreatorEmojis(token.value, 'draft'),
      fetchCreatorEmojis(token.value, 'pending'),
      fetchCreatorEmojis(token.value, 'approved'),
      fetchCreatorEmojis(token.value, 'rejected'),
      fetchCreatorAnalytics(token.value),
    ])

    drafts.value = draftResponse.items ?? []
    pendingItems.value = pendingResponse.items ?? []
    approvedItems.value = approvedResponse.items ?? []
    rejectedItems.value = rejectedResponse.items ?? []
    analytics.value = analyticsResponse
    refreshEditingEmoji()
  } catch (loadError) {
    error.value = loadError.message ?? 'Failed to load creator dashboard'
  } finally {
    loading.value = false
  }
}

const beginEditing = (emoji, tab = 'drafts') => {
  editingEmoji.value = { ...emoji }
  activeTab.value = tab
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const cancelEditing = () => {
  editingEmoji.value = null
}

const handleComposerSubmit = async (payload) => {
  const requestPayload = {
    symbol: payload.symbol,
    title: payload.title,
    description: payload.description,
    category: payload.category,
    keywords: payload.keywords,
  }

  try {
    if (editingEmoji.value) {
      await updateCreatorEmoji(editingEmoji.value.id, requestPayload, token.value)
      addToast('Emoji updated.')
      editingEmoji.value = null
    } else {
      await createCreatorEmoji({ ...requestPayload, intent: payload.intent }, token.value)
      addToast(payload.intent === 'draft' ? 'Draft saved.' : 'Emoji submitted for review.')
      activeTab.value = payload.intent === 'draft' ? 'drafts' : 'submissions'
    }

    await loadDashboard()
  } catch (submitError) {
    addToast(submitError.message ?? 'Unable to save emoji', 'error')
    throw submitError
  }
}

const handleSubmitItem = async (emoji) => {
  try {
    await submitCreatorEmoji(emoji.id, token.value)
    addToast(emoji.moderation_status === 'rejected' ? 'Emoji resubmitted for review.' : 'Draft submitted for review.')
    if (editingEmoji.value?.id === emoji.id) {
      editingEmoji.value = null
    }
    activeTab.value = 'submissions'
    await loadDashboard()
  } catch (submitError) {
    addToast(submitError.message ?? 'Unable to submit emoji', 'error')
  }
}

const handleDuplicateItem = async (emoji) => {
  try {
    await duplicateCreatorEmoji(emoji.id, token.value)
    addToast('Draft copy created.')
    activeTab.value = 'drafts'
    await loadDashboard()
  } catch (duplicateError) {
    addToast(duplicateError.message ?? 'Unable to duplicate emoji', 'error')
  }
}

const handleDeleteItem = async (emoji) => {
  try {
    await deleteEmoji(emoji.id, token.value)
    addToast(emoji.moderation_status === 'draft' ? 'Draft deleted.' : 'Emoji deleted.')
    if (editingEmoji.value?.id === emoji.id) {
      editingEmoji.value = null
    }
    await loadDashboard()
  } catch (deleteError) {
    addToast(deleteError.message ?? 'Unable to delete emoji', 'error')
  }
}

const saveProfile = async () => {
  savingProfile.value = true
  try {
    const updatedUser = await updateCurrentUserProfile(
      {
        display_name: profileForm.display_name || null,
        avatar_url: profileForm.avatar_url || null,
        bio: profileForm.bio || null,
      },
      token.value,
    )
    setSession({ token: token.value, user: updatedUser })
    addToast('Profile updated.')
  } catch (profileError) {
    addToast(profileError.message ?? 'Unable to update profile', 'error')
  } finally {
    savingProfile.value = false
  }
}

const formatDate = (value) => {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

watch(
  user,
  () => {
    syncProfileForm()
  },
  { immediate: true },
)

loadDashboard()
</script>

<template>
  <main class="page">
    <div v-if="loading" class="status">Loading your creator dashboard...</div>
    <div v-else-if="error" class="status error">{{ error }}</div>
    <div v-else class="dashboard">
      <section class="hero">
        <div class="hero-aura hero-aura-left"></div>
        <div class="hero-aura hero-aura-right"></div>

        <div class="hero-copy">
          <p class="eyebrow">Creator dashboard</p>
          <h1>Build privately. Publish the best.</h1>
          <p class="hero-description">
            Draft fresh ideas, track review status, and polish the public profile people see when they land on your work.
          </p>

          <div class="hero-highlights">
            <article class="hero-highlight tone-rose">
              <span>Drafts</span>
              <strong>{{ analytics.draft_count }}</strong>
            </article>
            <article class="hero-highlight tone-amber">
              <span>In review</span>
              <strong>{{ analytics.pending_count }}</strong>
            </article>
            <article class="hero-highlight tone-mint">
              <span>Likes</span>
              <strong>{{ analytics.total_likes_received }}</strong>
            </article>
          </div>
        </div>

        <aside class="hero-profile">
          <div class="hero-profile-card">
            <div class="hero-avatar">
              <img v-if="profileForm.avatar_url" :src="profileForm.avatar_url" alt="Creator avatar" />
              <span v-else>{{ profilePreviewInitial }}</span>
            </div>
            <div class="hero-profile-copy">
              <p class="hero-profile-label">Public profile</p>
              <strong>{{ profileForm.display_name || user?.display_name || user?.email || 'Anonymous creator' }}</strong>
              <span>{{ analytics.approved_count }} approved emoji{{ analytics.approved_count === 1 ? '' : 's' }}</span>
            </div>
          </div>

          <RouterLink
            v-if="user?.id"
            class="hero-link"
            :to="{ name: 'user-profile', params: { id: user.id } }"
          >
            View public profile
          </RouterLink>
        </aside>
      </section>

      <section class="composer-grid">
        <EmojiSubmitForm
          :on-submit="handleComposerSubmit"
          :initial-value="editingEmoji"
          :form-title="composerTitle"
          :form-description="composerDescription"
          :primary-label="composerPrimaryLabel"
          :allow-draft="composerAllowsDraft"
          :reset-on-success="!isEditing"
          :show-cancel="isEditing"
          :on-cancel="cancelEditing"
        />

        <aside class="snapshot-card">
          <div class="snapshot-heading">
            <p class="snapshot-kicker">At a glance</p>
            <h2>Current pipeline</h2>
          </div>
          <div class="snapshot-grid">
            <article
              v-for="stat in dashboardStats"
              :key="stat.label"
              class="snapshot-stat"
              :class="`tone-${stat.tone}`"
            >
              <span>{{ stat.label }}</span>
              <strong>{{ stat.value }}</strong>
            </article>
          </div>
          <p class="snapshot-note">
            Drafts stay private until you explicitly submit them. Approved emojis are the only ones that can collect likes.
          </p>
        </aside>
      </section>

      <div class="tabs">
        <button type="button" class="tab" :class="{ active: activeTab === 'drafts' }" @click="activeTab = 'drafts'">
          Drafts
        </button>
        <button type="button" class="tab" :class="{ active: activeTab === 'submissions' }" @click="activeTab = 'submissions'">
          Submissions
        </button>
        <button type="button" class="tab" :class="{ active: activeTab === 'analytics' }" @click="activeTab = 'analytics'">
          Analytics
        </button>
        <button type="button" class="tab" :class="{ active: activeTab === 'profile' }" @click="activeTab = 'profile'">
          Profile
        </button>
      </div>

      <section v-if="activeTab === 'drafts'" class="tab-panel">
        <div v-if="drafts.length" class="managed-grid">
          <article v-for="emoji in drafts" :key="emoji.id" class="managed-card">
            <div class="managed-layout">
              <div class="emoji-mark">{{ emoji.symbol }}</div>
              <div class="managed-main">
                <div class="managed-header">
                  <p class="status-pill draft">Draft</p>
                </div>
                <p class="meta-line">Created {{ formatDate(emoji.created_at) }}</p>
              </div>
            </div>
            <div class="card-actions">
              <button type="button" class="ghost-btn" @click="beginEditing(emoji, 'drafts')">Edit</button>
              <button type="button" class="ghost-btn" @click="handleSubmitItem(emoji)">Submit</button>
              <button type="button" class="danger-btn" @click="handleDeleteItem(emoji)">Delete</button>
            </div>
          </article>
        </div>
        <div v-else class="empty-card">
          <h3>No drafts yet</h3>
          <p>Start with a rough idea in the composer, save it privately, and it will appear here.</p>
        </div>
      </section>

      <section v-else-if="activeTab === 'submissions'" class="tab-panel submissions-panel">
        <section v-for="section in submissionSections" :key="section.key" class="submission-section">
          <div class="section-heading">
            <div>
              <h2>{{ section.title }}</h2>
              <p>{{ section.description }}</p>
            </div>
          </div>

          <div v-if="section.items.length" class="managed-grid">
            <article v-for="emoji in section.items" :key="emoji.id" class="managed-card">
              <div class="managed-layout">
                <div class="emoji-mark">{{ emoji.symbol }}</div>
                <div class="managed-main">
                <div class="managed-header">
                  <p class="status-pill" :class="emoji.moderation_status">{{ emoji.moderation_status }}</p>
                </div>
                  <p class="meta-line">
                    {{ formatDate(emoji.created_at) }}
                    <span v-if="emoji.moderation_status === 'approved'">
                      · {{ emoji.like_count || 0 }} like{{ (emoji.like_count || 0) === 1 ? '' : 's' }}
                    </span>
                  </p>
                </div>
              </div>
              <p v-if="emoji.moderation_reason" class="reason-note">Rejection note: {{ emoji.moderation_reason }}</p>
              <div class="card-actions">
                <button type="button" class="ghost-btn" @click="beginEditing(emoji, 'submissions')">Edit</button>
                <button
                  v-if="emoji.moderation_status === 'rejected'"
                  type="button"
                  class="ghost-btn"
                  @click="handleSubmitItem(emoji)"
                >
                  Resubmit
                </button>
                <button type="button" class="ghost-btn" @click="handleDuplicateItem(emoji)">Dupli</button>
                <button type="button" class="danger-btn" @click="handleDeleteItem(emoji)">Delete</button>
              </div>
            </article>
          </div>

          <div v-else class="empty-card compact">
            <p>No {{ section.key }} items right now.</p>
          </div>
        </section>
      </section>

      <section v-else-if="activeTab === 'analytics'" class="tab-panel analytics-panel">
        <div class="analytics-grid">
          <article
            v-for="stat in dashboardStats"
            :key="stat.label"
            class="analytics-card"
            :class="`tone-${stat.tone}`"
          >
            <span>{{ stat.label }}</span>
            <strong>{{ stat.value }}</strong>
          </article>
        </div>

        <section class="top-emojis-card">
          <div class="section-heading">
            <div>
              <h2>Top approved emojis</h2>
              <p>Lifetime ranking across approved entries, with newest wins breaking like-count ties.</p>
            </div>
          </div>

          <div v-if="analytics.top_emojis?.length" class="top-list">
            <article v-for="emoji in analytics.top_emojis" :key="emoji.id" class="top-item">
              <div class="emoji-mark small">{{ emoji.symbol }}</div>
              <div class="top-copy">
                <strong>{{ emoji.title }}</strong>
                <span>{{ emoji.like_count || 0 }} likes · {{ formatDate(emoji.created_at) }}</span>
              </div>
            </article>
          </div>
          <div v-else class="empty-card compact">
            <p>No approved emojis have collected likes yet.</p>
          </div>
        </section>
      </section>

      <section v-else class="tab-panel profile-panel">
        <div class="profile-layout">
          <form class="profile-form" @submit.prevent="saveProfile">
            <div class="section-heading">
              <div>
                <h2>Public profile settings</h2>
                <p>These fields show up on your public creator page and in the dashboard welcome state.</p>
              </div>
            </div>

            <label>
              Display name
              <input v-model.trim="profileForm.display_name" maxlength="128" />
            </label>

            <label>
              Avatar URL
              <input
                v-model.trim="profileForm.avatar_url"
                type="url"
                maxlength="512"
                placeholder="https://example.com/avatar.png"
              />
            </label>

            <label>
              Short bio
              <textarea
                v-model.trim="profileForm.bio"
                rows="4"
                maxlength="280"
                placeholder="Tell people what kind of emojis you love to make."
              />
            </label>

            <button type="submit" class="primary-btn" :disabled="savingProfile">
              {{ savingProfile ? 'Saving…' : 'Save profile' }}
            </button>
          </form>

          <aside class="profile-preview">
            <div class="preview-avatar">
              <img
                v-if="profileForm.avatar_url"
                :src="profileForm.avatar_url"
                alt="Creator avatar preview"
              />
              <span v-else>{{ profilePreviewInitial }}</span>
            </div>
            <h3>{{ profileForm.display_name || user?.display_name || user?.email || 'Anonymous creator' }}</h3>
            <p class="preview-label">Public profile preview</p>
            <p class="preview-bio">
              {{ profileForm.bio || 'Add a short bio so visitors know what kind of emoji creator you are.' }}
            </p>
          </aside>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 1.5rem 1rem 3rem;
  background:
    radial-gradient(circle at top left, rgba(244, 114, 182, 0.14), transparent 24rem),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.16), transparent 24rem),
    radial-gradient(circle at bottom, rgba(251, 191, 36, 0.12), transparent 28rem),
    radial-gradient(circle at top, var(--bg-page-1), var(--bg-page-2), var(--bg-page-3));
}

.status {
  padding: 4rem 1rem;
  text-align: center;
  color: var(--color-text-secondary);
}

.status.error {
  color: var(--color-text-error);
}

.dashboard {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  gap: 1.25rem;
}

.hero {
  position: relative;
  display: grid;
  gap: 1rem;
  padding: 1.15rem;
  border-radius: 1.65rem;
  border: 1px solid var(--color-border);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.52), rgba(255, 255, 255, 0.18) 55%, transparent 100%),
    linear-gradient(120deg, rgba(99, 102, 241, 0.08), rgba(236, 72, 153, 0.03) 45%, rgba(56, 189, 248, 0.1)),
    var(--color-bg-surface-raised);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  isolation: isolate;
}

.hero-aura {
  position: absolute;
  border-radius: 999px;
  pointer-events: none;
  filter: blur(10px);
  opacity: 0.7;
  z-index: -1;
}

.hero-aura-left {
  top: -2.5rem;
  left: -1rem;
  width: 10rem;
  height: 10rem;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.18), transparent 70%);
}

.hero-aura-right {
  right: -2rem;
  bottom: -3rem;
  width: 12rem;
  height: 12rem;
  background: radial-gradient(circle, rgba(236, 72, 153, 0.14), transparent 72%);
}

.hero-copy {
  max-width: 38rem;
  display: grid;
  gap: 0.75rem;
}

.hero-copy h1,
.hero-copy p {
  margin: 0;
}

.hero-copy h1 {
  max-width: 11ch;
  font-size: clamp(2.2rem, 5vw, 4.15rem);
  line-height: 0.96;
  letter-spacing: -0.05em;
  color: #0f172a;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.7rem;
  font-weight: 800;
  color: #4f46e5;
}

.hero-description {
  max-width: 35rem;
  font-size: clamp(0.98rem, 1.7vw, 1.1rem);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.hero-highlights {
  display: grid;
  gap: 0.65rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.hero-highlight {
  padding: 0.8rem 0.9rem;
  border-radius: 1.2rem;
  border: 1px solid rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(10px);
  display: grid;
  gap: 0.15rem;
}

.hero-highlight span {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.hero-highlight strong {
  font-size: 1.35rem;
  color: var(--color-text-heading);
}

.hero-profile {
  display: grid;
  gap: 0.75rem;
  align-content: space-between;
}

.hero-profile-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.85rem;
  align-items: center;
  padding: 0.9rem 1rem;
  border-radius: 1.35rem;
  border: 1px solid rgba(99, 102, 241, 0.14);
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(10px);
}

.hero-avatar {
  width: 3.4rem;
  height: 3.4rem;
  border-radius: 1.1rem;
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.4)),
    rgba(99, 102, 241, 0.18);
  display: grid;
  place-items: center;
  overflow: hidden;
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-text-heading);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.hero-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-profile-copy {
  display: grid;
  gap: 0.2rem;
  min-width: 0;
}

.hero-profile-copy strong,
.hero-profile-copy span,
.hero-profile-label {
  margin: 0;
}

.hero-profile-copy strong {
  font-size: 1rem;
  color: var(--color-text-heading);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hero-profile-copy span {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.hero-profile-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-link);
  font-weight: 800;
}

.hero-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.85rem;
  padding: 0.75rem 1.05rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--color-text-heading);
  border: 1px solid rgba(99, 102, 241, 0.2);
  font-weight: 700;
  text-decoration: none;
  box-shadow: 0 10px 24px rgba(99, 102, 241, 0.08);
}

.composer-grid {
  display: grid;
  gap: 1rem;
}

.snapshot-card {
  padding: 1.5rem;
  border-radius: 1.6rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface-raised);
  box-shadow: var(--shadow-card);
  display: grid;
  gap: 1rem;
}

.snapshot-heading h2,
.snapshot-heading p,
.snapshot-note {
  margin: 0;
}

.snapshot-kicker {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
  font-weight: 800;
  color: var(--color-text-link);
}

.snapshot-grid,
.analytics-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
}

.snapshot-stat,
.analytics-card {
  padding: 1rem;
  border-radius: 1.2rem;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-surface);
  display: grid;
  gap: 0.35rem;
}

.snapshot-stat strong,
.analytics-card strong {
  font-size: 1.45rem;
  color: var(--color-text-heading);
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.tab {
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  color: var(--color-text);
  border-radius: 999px;
  padding: 0.7rem 1rem;
  font-weight: 700;
  cursor: pointer;
}

.tab.active {
  border-color: transparent;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: #fff;
}

.tab-panel,
.top-emojis-card {
  display: grid;
  gap: 1rem;
}

.submissions-panel {
  gap: 1.25rem;
}

.submission-section,
.top-emojis-card,
.profile-form,
.profile-preview {
  padding: 1.4rem;
  border-radius: 1.6rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface-raised);
  box-shadow: var(--shadow-card);
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.section-heading h2,
.section-heading p {
  margin: 0;
}

.section-heading p {
  color: var(--color-text-secondary);
}

.managed-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.managed-card {
  padding: 1.15rem;
  border-radius: 1.45rem;
  border: 1px solid var(--color-border-light);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.4), transparent 55%),
    var(--color-bg-surface);
  display: grid;
  gap: 1rem;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.managed-layout {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1rem;
  align-items: center;
}

.emoji-mark {
  display: grid;
  place-items: center;
  width: 4.25rem;
  height: 4.25rem;
  border-radius: 1.25rem;
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.25)),
    rgba(99, 102, 241, 0.14);
  font-size: 2.2rem;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.emoji-mark.small {
  width: 2.8rem;
  height: 2.8rem;
  font-size: 1.4rem;
}

.meta-line,
.reason-note {
  margin: 0;
}

.managed-main {
  display: grid;
  gap: 0.45rem;
  min-width: 0;
}

.managed-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 1.8rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.76rem;
  text-transform: capitalize;
  font-weight: 800;
  background: rgba(148, 163, 184, 0.18);
  color: var(--color-text-heading);
}

.status-pill.draft {
  background: rgba(244, 114, 182, 0.16);
  color: #be185d;
}

.status-pill.pending {
  background: rgba(251, 191, 36, 0.18);
  color: #92400e;
}

.status-pill.approved {
  background: rgba(16, 185, 129, 0.16);
  color: #047857;
}

.status-pill.rejected {
  background: rgba(239, 68, 68, 0.14);
  color: #b91c1c;
}

.meta-line {
  color: var(--color-text-secondary);
}

.reason-note {
  padding: 0.85rem 0.95rem;
  border-radius: 1rem;
  background: rgba(239, 68, 68, 0.08);
  color: #b91c1c;
}

.card-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.6rem;
  padding-top: 0.2rem;
}

.ghost-btn,
.danger-btn,
.primary-btn {
  width: 100%;
  min-width: 0;
  border: none;
  border-radius: 0.85rem;
  padding: 0.72rem 0.4rem;
  font-size: clamp(0.82rem, 1.4vw, 0.98rem);
  line-height: 1.1;
  text-align: center;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
}

.ghost-btn {
  background: rgba(99, 102, 241, 0.12);
  color: var(--color-text-heading);
}

.danger-btn {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.primary-btn {
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: #fff;
}

.primary-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.empty-card {
  padding: 1.6rem;
  border-radius: 1.35rem;
  border: 1px dashed var(--color-border);
  background: var(--color-bg-surface);
  color: var(--color-text-secondary);
}

.empty-card h3,
.empty-card p {
  margin: 0;
}

.empty-card.compact {
  padding: 1.1rem;
}

.top-list {
  display: grid;
  gap: 0.85rem;
}

.top-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.85rem;
  align-items: center;
}

.top-copy {
  display: grid;
  gap: 0.2rem;
}

.top-copy span {
  color: var(--color-text-secondary);
}

.profile-layout {
  display: grid;
  gap: 1rem;
}

.profile-form {
  display: grid;
  gap: 1rem;
}

.profile-form label {
  display: grid;
  gap: 0.4rem;
  font-weight: 700;
  color: var(--color-text-heading);
}

.profile-form input,
.profile-form textarea {
  border-radius: 0.85rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-input);
  color: var(--color-text);
  padding: 0.75rem 0.9rem;
  font: inherit;
}

.profile-preview {
  display: grid;
  justify-items: start;
  align-content: start;
  gap: 0.75rem;
}

.preview-avatar {
  width: 5.25rem;
  height: 5.25rem;
  border-radius: 1.5rem;
  background: rgba(99, 102, 241, 0.12);
  display: grid;
  place-items: center;
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-heading);
  overflow: hidden;
}

.preview-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-preview h3,
.profile-preview p {
  margin: 0;
}

.preview-label {
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 800;
  color: var(--color-text-link);
}

.preview-bio {
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.tone-rose {
  background: rgba(244, 114, 182, 0.09);
}

.tone-amber {
  background: rgba(251, 191, 36, 0.11);
}

.tone-sky {
  background: rgba(56, 189, 248, 0.1);
}

.tone-slate {
  background: rgba(148, 163, 184, 0.1);
}

.tone-mint {
  background: rgba(16, 185, 129, 0.09);
}

@media (min-width: 900px) {
  .hero {
    grid-template-columns: minmax(0, 1.6fr) minmax(15rem, 0.72fr);
    align-items: stretch;
    gap: 1.1rem;
    padding: 1.3rem;
  }

  .hero-profile {
    min-width: 0;
  }
}

@media (max-width: 680px) {
  .hero {
    padding: 1rem;
    border-radius: 1.45rem;
  }

  .hero-copy h1 {
    max-width: 9ch;
    font-size: clamp(2rem, 11vw, 3rem);
  }

  .hero-highlights {
    grid-template-columns: 1fr;
  }

  .hero-link {
    width: 100%;
  }
}

[data-theme="dark"] .hero {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.01) 55%, transparent 100%),
    linear-gradient(120deg, rgba(99, 102, 241, 0.18), rgba(236, 72, 153, 0.06) 45%, rgba(56, 189, 248, 0.12)),
    var(--color-bg-surface-raised);
}

[data-theme="dark"] .hero-copy h1 {
  color: var(--color-text-heading);
}

[data-theme="dark"] .hero-highlight,
[data-theme="dark"] .hero-profile-card,
[data-theme="dark"] .hero-link {
  background: rgba(15, 23, 42, 0.46);
  border-color: rgba(148, 163, 184, 0.2);
}

[data-theme="dark"] .hero-avatar {
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.03)),
    rgba(99, 102, 241, 0.22);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

[data-theme="dark"] .managed-card {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 55%),
    var(--color-bg-surface);
  box-shadow: 0 14px 28px rgba(0, 0, 0, 0.28);
}

[data-theme="dark"] .emoji-mark {
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.02)),
    rgba(99, 102, 241, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

@media (max-width: 560px) {
  .managed-layout {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 960px) {
  .page {
    padding: 2rem 1.5rem 3.5rem;
  }

  .composer-grid,
  .profile-layout {
    grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.85fr);
    align-items: start;
  }
}
</style>
