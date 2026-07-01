<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  collection: {
    type: Object,
    required: true,
  },
})

const formatDate = (value) => {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const normalized = computed(() => {
  const collection = props.collection || {}
  const emojiCount = collection.emoji_count ?? collection.item_count ?? collection.emojis?.length ?? collection.items?.length ?? 0
  return {
    id: collection.id,
    title: collection.title ?? collection.name ?? 'Untitled collection',
    description: collection.description ?? '',
    ownerName: collection.owner_name ?? collection.creator_name ?? collection.submitter_name ?? collection.username ?? '',
    emojiCount,
    isPublic: collection.is_public ?? collection.public ?? collection.kind === 'public',
    badgeLabel: collection.kind === 'personal' ? 'Personal' : 'Public',
    updatedAt: collection.updated_at ?? collection.modified_at ?? collection.created_at ?? '',
  }
})

const detailTo = computed(() => ({
  name: 'collection-detail',
  params: { id: normalized.value.id },
}))
</script>

<template>
  <RouterLink class="collection-link" :to="detailTo">
    <article class="collection-card">
      <div class="collection-topline">
        <span class="badge" :class="{ public: normalized.isPublic }">
          {{ normalized.badgeLabel }}
        </span>
        <span v-if="normalized.updatedAt" class="timestamp">
          Updated {{ formatDate(normalized.updatedAt) }}
        </span>
      </div>

      <h3>{{ normalized.title }}</h3>
      <p v-if="normalized.description" class="description">
        {{ normalized.description }}
      </p>
      <p v-else class="description muted">
        No description yet.
      </p>

      <div class="collection-footer">
        <div class="count-pill">
          <span class="count">{{ normalized.emojiCount }}</span>
          <span>emojis</span>
        </div>
        <span v-if="normalized.ownerName" class="owner">by {{ normalized.ownerName }}</span>
      </div>
    </article>
  </RouterLink>
</template>

<style scoped>
.collection-link {
  display: block;
  color: inherit;
  text-decoration: none;
}

.collection-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1.25rem;
  border-radius: 1.25rem;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-surface);
  backdrop-filter: blur(6px);
  box-shadow: var(--shadow-card);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.collection-link:hover .collection-card {
  transform: translateY(-3px);
  box-shadow: var(--shadow-card-hover);
}

.collection-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  background: var(--color-tag-bg);
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.badge.public {
  color: var(--color-text-success);
}

.timestamp {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

h3 {
  margin: 0;
  font-size: 1.15rem;
  color: var(--color-text-heading);
  line-height: 1.25;
}

.description {
  margin: 0;
  color: var(--color-text-secondary);
}

.description.muted {
  color: var(--color-text-muted);
}

.collection-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.count-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: var(--color-keyword-bg);
  color: var(--color-keyword-text);
  font-size: 0.9rem;
  font-weight: 600;
}

.count {
  font-size: 1rem;
  font-weight: 800;
}

.owner {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
</style>
