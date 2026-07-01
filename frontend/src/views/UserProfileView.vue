<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import CollectionCard from '../components/CollectionCard.vue'
import EmojiGrid from '../components/EmojiGrid.vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'

const getApi = () => import('../services/api')

const route = useRoute()
const router = useRouter()
const { token, isAuthenticated, user } = useAuth()
const { addToast } = useToast()

const profile = ref(null)
const loading = ref(true)
const error = ref('')

const achievementTheme = {
  spark: { icon: '🌱', accent: '#fb7185' },
  gallery: { icon: '🖼️', accent: '#8b5cf6' },
  heart: { icon: '💗', accent: '#ec4899' },
  trophy: { icon: '🏆', accent: '#f59e0b' },
  megaphone: { icon: '📣', accent: '#0ea5e9' },
  palette: { icon: '🎨', accent: '#14b8a6' },
}

const activeTab = computed(() => {
  return route.query.tab === 'collections' ? 'collections' : 'emojis'
})

const isOwnProfile = computed(() => {
  return Boolean(user.value && profile.value && String(user.value.id) === String(profile.value.id))
})

const initial = (name) => {
  if (!name) return '?'
  return name.charAt(0).toUpperCase()
}

const formatMonthYear = (dateStr) => {
  const parsed = new Date(dateStr)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
  })
}

const formatNumber = (value) => {
  const numeric = Number(value || 0)
  return new Intl.NumberFormat('en-US').format(numeric)
}

const normalizeCollection = (value) => {
  const source = value || {}
  const emojis = source.emojis ?? source.items ?? source.emoji_items ?? []
  return {
    ...source,
    title: source.title ?? source.name ?? 'Untitled collection',
    description: source.description ?? '',
    owner_name: source.owner_name ?? source.creator_name ?? source.submitter_name ?? source.username ?? '',
    emoji_count: source.emoji_count ?? source.item_count ?? emojis.length,
    is_public: source.is_public ?? source.public ?? source.kind === 'public',
    emojis,
  }
}

const normalizeCollectionList = (response) => {
  if (Array.isArray(response)) return response.map(normalizeCollection)
  if (Array.isArray(response?.items)) return response.items.map(normalizeCollection)
  if (Array.isArray(response?.collections)) return response.collections.map(normalizeCollection)
  if (Array.isArray(response?.data)) return response.data.map(normalizeCollection)
  return []
}

const normalizeStats = (source = {}) => ({
  emoji_count: source.emoji_count ?? 0,
  total_likes_received: source.total_likes_received ?? 0,
  collection_count: source.collection_count ?? 0,
  public_collection_count: source.public_collection_count ?? 0,
  categories_used_count: source.categories_used_count ?? 0,
})

const buildAchievements = (stats) => {
  const definitions = [
    {
      id: 'first_submission',
      title: 'First Submission',
      description: 'Share your first emoji with the community.',
      icon_key: 'spark',
      progress_current: stats.emoji_count,
      progress_target: 1,
    },
    {
      id: 'emoji_trio',
      title: 'Emoji Trio',
      description: 'Build a mini gallery with three submitted emojis.',
      icon_key: 'gallery',
      progress_current: stats.emoji_count,
      progress_target: 3,
    },
    {
      id: 'liked_creator',
      title: 'Liked Creator',
      description: 'Earn your first like across all submitted emojis.',
      icon_key: 'heart',
      progress_current: stats.total_likes_received,
      progress_target: 1,
    },
    {
      id: 'crowd_favorite',
      title: 'Crowd Favorite',
      description: 'Reach ten likes across your emoji catalog.',
      icon_key: 'trophy',
      progress_current: stats.total_likes_received,
      progress_target: 10,
    },
    {
      id: 'public_curator',
      title: 'Public Curator',
      description: 'Publish your first public collection.',
      icon_key: 'megaphone',
      progress_current: stats.public_collection_count,
      progress_target: 1,
    },
    {
      id: 'variety_pack',
      title: 'Variety Pack',
      description: 'Use three distinct categories across your submissions.',
      icon_key: 'palette',
      progress_current: stats.categories_used_count,
      progress_target: 3,
    },
  ]

  return definitions.map((achievement) => ({
    ...achievement,
    earned: achievement.progress_current >= achievement.progress_target,
  }))
}

const normalizeAchievement = (value) => {
  const theme = achievementTheme[value?.icon_key] || { icon: '✨', accent: '#6366f1' }
  const progressCurrent = Number(value?.progress_current ?? 0)
  const progressTarget = Number(value?.progress_target ?? 0)
  return {
    id: value?.id ?? 'unknown',
    title: value?.title ?? 'Achievement',
    description: value?.description ?? '',
    icon_key: value?.icon_key ?? 'spark',
    icon: theme.icon,
    accent: theme.accent,
    earned: Boolean(value?.earned),
    progress_current: progressCurrent,
    progress_target: progressTarget,
  }
}

const normalizeProfile = (source) => {
  const normalizedCollections = normalizeCollectionList(source?.collections)
  const normalizedStats = normalizeStats({
    emoji_count: source?.stats?.emoji_count ?? source?.emoji_count,
    total_likes_received: source?.stats?.total_likes_received ?? source?.total_likes_received,
    collection_count: source?.stats?.collection_count ?? source?.collection_count,
    public_collection_count: source?.stats?.public_collection_count ?? 0,
    categories_used_count: source?.stats?.categories_used_count ?? 0,
  })
  const achievements = Array.isArray(source?.achievements) && source.achievements.length
    ? source.achievements
    : buildAchievements(normalizedStats)

  return {
    ...source,
    emojis: Array.isArray(source?.emojis) ? source.emojis : [],
    collections: normalizedCollections,
    stats: normalizedStats,
    achievements: achievements.map(normalizeAchievement),
    highlights: {
      top_emoji: source?.highlights?.top_emoji ?? null,
      recent_public_collections: normalizeCollectionList(source?.highlights?.recent_public_collections),
    },
  }
}

const visibleCollections = computed(() => {
  return normalizeCollectionList(profile.value?.collections)
})

const topEmoji = computed(() => {
  return profile.value?.highlights?.top_emoji ?? null
})

const highlightCollections = computed(() => {
  return profile.value?.highlights?.recent_public_collections ?? []
})

const profileStats = computed(() => {
  return normalizeStats(profile.value?.stats)
})

const statCards = computed(() => {
  const stats = profileStats.value
  return [
    { label: 'Emojis', value: stats.emoji_count, tone: 'rose' },
    { label: 'Likes Received', value: stats.total_likes_received, tone: 'gold' },
    { label: 'All Collections', value: stats.collection_count, tone: 'sky' },
    { label: 'Public Collections', value: stats.public_collection_count, tone: 'mint' },
    { label: 'Categories Used', value: stats.categories_used_count, tone: 'violet' },
  ]
})

const collectionEmptyMessage = computed(() => {
  return isOwnProfile.value ? 'You have not created any collections yet.' : 'No public collections yet.'
})

const showcaseMessage = computed(() => {
  return isOwnProfile.value
    ? 'Start sharing emojis to unlock your creator milestones.'
    : 'This creator has not shared any emojis yet.'
})

const syncAchievementProgress = () => {
  if (!profile.value) return
  profile.value.achievements = buildAchievements(profile.value.stats).map(normalizeAchievement)
}

const loadProfile = async () => {
  loading.value = true
  error.value = ''
  try {
    const api = await getApi()
    if (typeof api.fetchUserProfile !== 'function') {
      throw new Error('Profile data is unavailable')
    }
    const response = await api.fetchUserProfile(route.params.id, token.value)
    profile.value = normalizeProfile(response)
  } catch (err) {
    error.value = err?.message ?? 'Failed to load profile'
  } finally {
    loading.value = false
  }
}

const updateTab = async (tab) => {
  const query = { ...route.query }
  if (tab === 'collections') {
    query.tab = 'collections'
  } else {
    delete query.tab
  }
  await router.replace({
    name: route.name ?? 'user-profile',
    params: route.params,
    query,
  })
}

const handleToggleLike = async (emoji) => {
  if (!isAuthenticated.value || !profile.value) return
  try {
    const api = await getApi()
    const delta = emoji.is_liked ? -1 : 1
    if (emoji.is_liked) {
      await api.unlikeEmoji(emoji.id, token.value)
      emoji.is_liked = false
      emoji.like_count = Math.max(0, (emoji.like_count || 0) - 1)
    } else {
      await api.likeEmoji(emoji.id, token.value)
      emoji.is_liked = true
      emoji.like_count = (emoji.like_count || 0) + 1
    }

    profile.value.total_likes_received = Math.max(
      0,
      (profile.value.total_likes_received || 0) + delta,
    )
    profile.value.stats.total_likes_received = Math.max(
      0,
      (profile.value.stats?.total_likes_received || 0) + delta,
    )

    if (profile.value.highlights?.top_emoji?.id === emoji.id) {
      profile.value.highlights.top_emoji.like_count = emoji.like_count
      profile.value.highlights.top_emoji.is_liked = emoji.is_liked
    }

    syncAchievementProgress()
  } catch {
    addToast('Failed to toggle like', 'error')
  }
}

watch(
  () => route.params.id,
  () => {
    loadProfile()
  },
  { immediate: true },
)
</script>

<template>
  <main class="page">
    <div v-if="loading" class="status">Loading profile...</div>
    <div v-else-if="error" class="status error">{{ error }}</div>
    <div v-else-if="profile" class="profile">
      <section class="profile-hero">
        <div class="hero-copy">
          <div class="avatar">
            <img
              v-if="profile.avatar_url"
              :src="profile.avatar_url"
              :alt="`${profile.display_name || 'Anonymous'} avatar`"
              class="avatar-image"
            />
            <span v-else>{{ initial(profile.display_name) }}</span>
          </div>
          <div class="hero-text">
            <p class="eyebrow">{{ isOwnProfile ? 'Your creator space' : 'Creator profile' }}</p>
            <h1>{{ profile.display_name || 'Anonymous' }}</h1>
            <p class="joined">Member since {{ formatMonthYear(profile.created_at) }}</p>
            <p v-if="profile.bio" class="profile-bio">{{ profile.bio }}</p>
            <p class="hero-blurb">
              {{ showcaseMessage }}
            </p>
          </div>
        </div>

        <div class="hero-panel">
          <p class="hero-panel-label">Current momentum</p>
          <p class="hero-panel-value">{{ formatNumber(profileStats.total_likes_received) }}</p>
          <p class="hero-panel-copy">
            Total likes received across {{ formatNumber(profileStats.emoji_count) }} submitted emojis.
          </p>
        </div>
      </section>

      <section class="stats-grid" aria-label="Profile stats">
        <article
          v-for="stat in statCards"
          :key="stat.label"
          class="stat-card"
          :class="`tone-${stat.tone}`"
        >
          <span class="stat-label">{{ stat.label }}</span>
          <span class="stat-value">{{ formatNumber(stat.value) }}</span>
        </article>
      </section>

      <section class="showcase-grid">
        <div class="showcase-block achievements-block">
          <div class="section-heading">
            <div>
              <p class="section-kicker">Milestones</p>
              <h2>Creator achievements</h2>
            </div>
          </div>
          <div class="achievements-grid">
            <article
              v-for="achievement in profile.achievements"
              :key="achievement.id"
              class="achievement-card"
              :class="{ earned: achievement.earned }"
              :style="{ '--achievement-accent': achievement.accent }"
            >
              <div class="achievement-topline">
                <span class="achievement-icon" aria-hidden="true">{{ achievement.icon }}</span>
                <span class="achievement-state">
                  {{ achievement.earned ? 'Unlocked' : 'In progress' }}
                </span>
              </div>
              <h3>{{ achievement.title }}</h3>
              <p>{{ achievement.description }}</p>
              <div class="achievement-progress">
                <span>{{ formatNumber(achievement.progress_current) }}/{{ formatNumber(achievement.progress_target) }}</span>
                <div class="progress-track" aria-hidden="true">
                  <div
                    class="progress-fill"
                    :style="{ width: `${Math.min(100, (achievement.progress_current / achievement.progress_target) * 100)}%` }"
                  />
                </div>
              </div>
            </article>
          </div>
        </div>

        <div class="showcase-block spotlight-block">
          <div class="section-heading">
            <div>
              <p class="section-kicker">Highlights</p>
              <h2>Creator spotlight</h2>
            </div>
          </div>

          <article v-if="topEmoji" class="top-emoji-card">
            <div class="top-emoji-symbol" aria-hidden="true">{{ topEmoji.symbol }}</div>
            <div class="top-emoji-copy">
              <p class="spotlight-label">Top emoji</p>
              <h3>{{ topEmoji.title }}</h3>
              <p v-if="topEmoji.description">{{ topEmoji.description }}</p>
              <p v-else>Leading the pack with {{ formatNumber(topEmoji.like_count) }} likes.</p>
              <div class="top-emoji-meta">
                <span class="meta-pill">{{ formatNumber(topEmoji.like_count) }} likes</span>
                <span v-if="topEmoji.category" class="meta-pill soft">{{ topEmoji.category }}</span>
              </div>
            </div>
          </article>
          <div v-else class="top-emoji-empty">
            <h3>No featured emoji yet</h3>
            <p>{{ showcaseMessage }}</p>
          </div>

          <div class="recent-collections">
            <div class="recent-heading">
              <h3>Recent public collections</h3>
              <span v-if="highlightCollections.length" class="recent-caption">
                {{ formatNumber(highlightCollections.length) }} featured
              </span>
            </div>
            <div v-if="highlightCollections.length" class="highlight-collections-grid">
              <CollectionCard
                v-for="collection in highlightCollections"
                :key="collection.id"
                :collection="collection"
              />
            </div>
            <div v-else class="highlight-empty">
              <p>No public collections yet.</p>
            </div>
          </div>
        </div>
      </section>

      <div class="tabs">
        <button type="button" class="tab" :class="{ active: activeTab === 'emojis' }" @click="updateTab('emojis')">
          Submitted Emojis
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: activeTab === 'collections' }"
          @click="updateTab('collections')"
        >
          Collections
        </button>
      </div>

      <div v-if="activeTab === 'emojis'" class="profile-emojis">
        <h2 v-if="profile.emojis?.length">Submitted Emojis</h2>
        <EmojiGrid
          :emojis="profile.emojis || []"
          :is-authenticated="isAuthenticated"
          @toggle-like="handleToggleLike"
        />
        <p v-if="!profile.emojis?.length" class="empty">No emojis submitted yet.</p>
      </div>

      <div v-else class="profile-collections">
        <div v-if="visibleCollections.length" class="collections-grid">
          <CollectionCard
            v-for="collection in visibleCollections"
            :key="collection.id"
            :collection="collection"
          />
        </div>
        <div v-else class="empty-collections">
          <p>{{ collectionEmptyMessage }}</p>
          <RouterLink class="collections-link" :to="{ name: 'collections-index' }">
            Browse collections
          </RouterLink>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 2rem 1rem 3rem;
  background:
    radial-gradient(circle at top left, rgba(248, 113, 113, 0.16), transparent 28rem),
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.16), transparent 26rem),
    radial-gradient(circle at bottom, rgba(168, 85, 247, 0.14), transparent 24rem),
    radial-gradient(circle at top, var(--bg-page-1), var(--bg-page-2), var(--bg-page-3));
  color: var(--color-text);
}

.status {
  text-align: center;
  padding: 4rem;
  color: var(--color-text-secondary);
  font-size: 1.1rem;
}

.status.error {
  color: var(--color-text-error);
}

.profile {
  max-width: 1180px;
  margin: 0 auto;
}

.profile-hero {
  display: grid;
  gap: 1.25rem;
  padding: 1.4rem;
  border-radius: 1.75rem;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.3), transparent 45%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.02), rgba(15, 23, 42, 0.08)),
    var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  margin-bottom: 1.25rem;
}

.hero-copy {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.avatar {
  width: 5.75rem;
  height: 5.75rem;
  border-radius: 1.7rem;
  background: linear-gradient(140deg, #fb7185, #8b5cf6 58%, #0ea5e9);
  color: white;
  font-size: 2.25rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 18px 35px rgba(99, 102, 241, 0.24);
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-text {
  min-width: 0;
}

.eyebrow {
  margin: 0 0 0.45rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
  font-weight: 800;
  color: var(--color-text-link);
}

.profile-hero h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 3.2rem);
  color: var(--color-text-heading);
}

.joined {
  margin: 0.35rem 0 0;
  color: var(--color-text-muted);
  font-size: 0.95rem;
}

.profile-bio {
  margin: 0.85rem 0 0;
  max-width: 42rem;
  color: var(--color-text);
  line-height: 1.6;
}

.hero-blurb {
  margin: 0.9rem 0 0;
  max-width: 42rem;
  color: var(--color-text-secondary);
  font-size: 1rem;
}

.hero-panel {
  border-radius: 1.4rem;
  padding: 1.15rem 1.2rem;
  background: rgba(15, 23, 42, 0.82);
  color: white;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.22);
}

.hero-panel-label {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.72);
}

.hero-panel-value {
  margin: 0.35rem 0;
  font-size: clamp(2rem, 6vw, 2.8rem);
  font-weight: 800;
}

.hero-panel-copy {
  margin: 0;
  color: rgba(255, 255, 255, 0.8);
}

.stats-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  margin-bottom: 1.25rem;
}

.stat-card {
  padding: 1rem 1.05rem;
  border-radius: 1.35rem;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-surface-raised);
  box-shadow: var(--shadow-card);
}

.stat-card.tone-rose {
  background: linear-gradient(135deg, rgba(251, 113, 133, 0.18), var(--color-bg-surface-raised));
}

.stat-card.tone-gold {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), var(--color-bg-surface-raised));
}

.stat-card.tone-sky {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.18), var(--color-bg-surface-raised));
}

.stat-card.tone-mint {
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.18), var(--color-bg-surface-raised));
}

.stat-card.tone-violet {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.18), var(--color-bg-surface-raised));
}

.stat-label {
  display: block;
  margin-bottom: 0.45rem;
  color: var(--color-text-secondary);
  font-size: 0.82rem;
  font-weight: 700;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text-heading);
}

.showcase-grid {
  display: grid;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.showcase-block {
  padding: 1.2rem;
  border-radius: 1.6rem;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.section-heading,
.recent-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  flex-wrap: wrap;
}

.section-kicker {
  margin: 0 0 0.25rem;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-link);
}

.section-heading h2,
.recent-heading h3,
.top-emoji-copy h3,
.top-emoji-empty h3,
.achievement-card h3,
.profile-emojis h2 {
  margin: 0;
  color: var(--color-text-heading);
}

.achievements-grid {
  margin-top: 1rem;
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.achievement-card {
  padding: 1rem;
  border-radius: 1.2rem;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: linear-gradient(180deg, rgba(148, 163, 184, 0.08), rgba(148, 163, 184, 0.03));
}

.achievement-card.earned {
  border-color: color-mix(in srgb, var(--achievement-accent) 45%, white);
  background: linear-gradient(180deg, color-mix(in srgb, var(--achievement-accent) 22%, transparent), rgba(255, 255, 255, 0.04));
}

.achievement-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.achievement-icon {
  width: 2.2rem;
  height: 2.2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.8rem;
  background: color-mix(in srgb, var(--achievement-accent) 18%, transparent);
  font-size: 1.15rem;
}

.achievement-state {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.achievement-card p {
  margin: 0.45rem 0 0;
  color: var(--color-text-secondary);
}

.achievement-progress {
  margin-top: 0.85rem;
}

.achievement-progress span {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-text-heading);
}

.progress-track {
  width: 100%;
  height: 0.5rem;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.22);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--achievement-accent), color-mix(in srgb, var(--achievement-accent) 68%, white));
}

.top-emoji-card,
.top-emoji-empty,
.highlight-empty {
  margin-top: 1rem;
  border-radius: 1.3rem;
  border: 1px solid var(--color-border-light);
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.12), rgba(248, 250, 252, 0.06));
  padding: 1rem;
}

.top-emoji-card {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.top-emoji-symbol {
  width: 4.75rem;
  height: 4.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 1.4rem;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.18), rgba(139, 92, 246, 0.18));
  font-size: 2.25rem;
  flex-shrink: 0;
}

.spotlight-label {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-link);
}

.top-emoji-copy p,
.top-emoji-empty p,
.highlight-empty p,
.recent-caption,
.empty,
.empty-collections p {
  color: var(--color-text-secondary);
}

.top-emoji-copy p {
  margin-bottom: 0;
}

.top-emoji-meta {
  margin-top: 0.85rem;
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.4rem 0.7rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.86);
  color: white;
  font-size: 0.86rem;
  font-weight: 700;
}

.meta-pill.soft {
  background: var(--color-tag-bg);
  color: var(--color-text-secondary);
}

.recent-collections {
  margin-top: 1.15rem;
}

.highlight-collections-grid,
.collections-grid {
  margin-top: 1rem;
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}

.tabs {
  display: flex;
  gap: 0.75rem;
  padding: 0.35rem;
  margin-bottom: 1rem;
  border-radius: 999px;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.tab {
  flex: 1;
  padding: 0.8rem 1rem;
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: 700;
}

.tab.active {
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
}

.profile-emojis h2 {
  font-size: 1.3rem;
  margin: 0 0 1rem;
}

.empty {
  text-align: center;
  padding: 2rem;
}

.empty-collections {
  text-align: center;
  padding: 2rem;
  border-radius: 1.5rem;
  background: var(--color-bg-surface-raised);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.collections-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 1rem;
  border-radius: 999px;
  background: linear-gradient(120deg, #6366f1, #ec4899);
  color: white;
  font-weight: 700;
}

@media (min-width: 860px) {
  .profile-hero {
    grid-template-columns: minmax(0, 1.8fr) minmax(280px, 0.9fr);
    align-items: stretch;
  }

  .showcase-grid {
    grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
  }
}

@media (max-width: 720px) {
  .page {
    padding-inline: 0.85rem;
  }

  .hero-copy {
    align-items: flex-start;
  }

  .top-emoji-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .tabs {
    flex-direction: column;
    border-radius: 1.2rem;
  }

  .tab {
    width: 100%;
  }
}
</style>
