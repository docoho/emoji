
// Always use relative path to allow Vite proxy to handle forwarding to backend
// This ensures it works from any device on the network (not just localhost)
const API_BASE = ''

async function buildApiError(response, fallbackMessage) {
  const errorBody = await response.json().catch(() => ({}))
  const error = new Error(errorBody.detail ?? fallbackMessage)
  error.status = response.status
  return error
}

function normalizeCollectionPayload(payload = {}) {
  const name = payload.name ?? payload.title ?? ''
  const description = payload.description ?? undefined
  let kind = payload.kind

  if (!kind) {
    if (payload.is_public === true || payload.public === true) {
      kind = 'public'
    } else if (payload.is_public === false || payload.public === false) {
      kind = 'personal'
    }
  }

  return {
    name,
    description,
    ...(kind ? { kind } : {}),
  }
}

function buildQueryString(query) {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '' || value === false) continue
    params.append(key, value === true ? 'true' : value)
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

async function request(path, {
  method = 'GET',
  token,
  body,
  query,
  fallbackErrorMessage = 'Request failed',
} = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${API_BASE}${path}${buildQueryString(query)}`, {
    method,
    headers: Object.keys(headers).length ? headers : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (response.status === 401 && token) {
    // Token was rejected (expired, revoked via token_version bump, or invalid).
    // Notify the auth layer so it can clear session state without coupling
    // this module to the composable.
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  }

  if (!response.ok) throw await buildApiError(response, fallbackErrorMessage)
  if (response.status === 204) return undefined
  return response.json().catch(() => ({}))
}

export async function fetchEmojis(token, params = {}) {
  // Divergent from `request()` because of the dev-mode mock-data fallback.
  const query = {
    search: params.search,
    category: params.category,
    sort: params.sort,
    limit: params.limit,
    offset: params.offset,
    favorites: params.favorites ? true : undefined,
  }
  try {
    return await request(`/api/emojis`, {
      token,
      query,
      fallbackErrorMessage: 'Failed to load emojis',
    })
  } catch (error) {
    // Only fall back to mock data on a true network failure (no HTTP status).
    // HTTP errors (4xx/5xx) must propagate so dev sees real backend signal.
    if (import.meta.env.DEV && error.status === undefined) {
      console.warn('Backend unreachable, using mock emojis:', error)
      const { mockEmojis } = await import('../data/mockEmojis')
      return { items: mockEmojis, total: mockEmojis.length, limit: 50, offset: 0 }
    }
    throw error
  }
}

export async function submitEmoji(payload, token) {
  return request('/api/emojis', {
    method: 'POST',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to submit emoji',
  })
}

export async function registerUser(payload) {
  return request('/api/auth/register', {
    method: 'POST',
    body: payload,
    fallbackErrorMessage: 'Registration failed',
  })
}

export async function loginUser(payload) {
  return request('/api/auth/login', {
    method: 'POST',
    body: payload,
    fallbackErrorMessage: 'Login failed',
  })
}

export async function fetchCurrentUser(token) {
  if (!token) return null
  try {
    return await request('/api/auth/me', { token })
  } catch {
    return null
  }
}

export async function updateEmoji(id, payload, token) {
  return request(`/api/emojis/${id}`, {
    method: 'PUT',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to update emoji',
  })
}

export async function fetchCreatorEmojis(token, status) {
  return request('/api/creator/emojis', {
    token,
    query: { status },
    fallbackErrorMessage: 'Failed to load creator emojis',
  })
}

export async function createCreatorEmoji(payload, token) {
  return request('/api/creator/emojis', {
    method: 'POST',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to save creator emoji',
  })
}

export async function updateCreatorEmoji(emojiId, payload, token) {
  return request(`/api/creator/emojis/${emojiId}`, {
    method: 'PUT',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to update creator emoji',
  })
}

export async function submitCreatorEmoji(emojiId, token) {
  return request(`/api/creator/emojis/${emojiId}/submit`, {
    method: 'POST',
    token,
    fallbackErrorMessage: 'Failed to submit creator emoji',
  })
}

export async function duplicateCreatorEmoji(emojiId, token) {
  return request(`/api/creator/emojis/${emojiId}/duplicate`, {
    method: 'POST',
    token,
    fallbackErrorMessage: 'Failed to duplicate emoji',
  })
}

export async function fetchCreatorAnalytics(token) {
  return request('/api/creator/analytics', {
    token,
    fallbackErrorMessage: 'Failed to load creator analytics',
  })
}

export async function deleteEmoji(id, token) {
  return request(`/api/emojis/${id}`, {
    method: 'DELETE',
    token,
    fallbackErrorMessage: 'Failed to delete emoji',
  })
}

export async function fetchEmojiCollections(emojiId, token) {
  return request(`/api/emojis/${emojiId}/collections`, {
    token,
    fallbackErrorMessage: 'Failed to load collections',
  })
}

export async function saveEmojiCollections(emojiId, collectionIds, token) {
  return request(`/api/emojis/${emojiId}/collections`, {
    method: 'PUT',
    token,
    body: { collection_ids: collectionIds },
    fallbackErrorMessage: 'Failed to save collections',
  })
}

export async function createCollection(payload, token) {
  return request('/api/collections', {
    method: 'POST',
    token,
    body: normalizeCollectionPayload(payload),
    fallbackErrorMessage: 'Failed to create collection',
  })
}

export async function fetchCollections(token, params = {}) {
  return request('/api/collections', {
    token,
    query: {
      owner_id: params.owner_id,
      search: params.search,
      sort: params.sort,
      limit: params.limit,
      offset: params.offset,
    },
    fallbackErrorMessage: 'Failed to load collections',
  })
}

export async function fetchAdminEmojis(token, params = {}) {
  return request('/api/admin/emojis', {
    token,
    query: {
      status: params.status,
      search: params.search,
      category: params.category,
      submitter_id: params.submitter_id,
      limit: params.limit,
      offset: params.offset,
    },
    fallbackErrorMessage: 'Failed to load moderation queue',
  })
}

export async function fetchAdminDashboard(token) {
  return request('/api/admin/dashboard', {
    token,
    fallbackErrorMessage: 'Failed to load admin dashboard',
  })
}

export async function fetchAdminReports(token, params = {}) {
  return request('/api/admin/reports', {
    token,
    query: {
      status: params.status,
      reason: params.reason,
      search: params.search,
      limit: params.limit,
      offset: params.offset,
    },
    fallbackErrorMessage: 'Failed to load report queue',
  })
}

export async function moderateEmoji(emojiId, payload, token) {
  return request(`/api/admin/emojis/${emojiId}/moderation`, {
    method: 'PATCH',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to update moderation status',
  })
}

export async function updateAdminReport(reportId, payload, token) {
  return request(`/api/admin/reports/${reportId}`, {
    method: 'PATCH',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to update report',
  })
}

export async function fetchCollection(collectionId, token, params = {}) {
  return request(`/api/collections/${collectionId}`, {
    token,
    query: {
      search: params.search,
      category: params.category,
      sort: params.sort,
      limit: params.limit,
      offset: params.offset,
    },
    fallbackErrorMessage: 'Failed to load collection',
  })
}

export async function updateCollection(collectionId, payload, token) {
  return request(`/api/collections/${collectionId}`, {
    method: 'PUT',
    token,
    body: normalizeCollectionPayload(payload),
    fallbackErrorMessage: 'Failed to update collection',
  })
}

export async function deleteCollection(collectionId, token) {
  return request(`/api/collections/${collectionId}`, {
    method: 'DELETE',
    token,
    fallbackErrorMessage: 'Failed to delete collection',
  })
}

export async function fetchUserCollections(userId, token, params = {}) {
  return fetchCollections(token, { ...params, owner_id: userId })
}

export async function requestPasswordReset(email) {
  return request('/api/auth/password-reset/request', {
    method: 'POST',
    body: { email },
    fallbackErrorMessage: 'Failed to request password reset',
  })
}

export async function confirmPasswordReset(token, newPassword) {
  return request('/api/auth/password-reset/confirm', {
    method: 'POST',
    body: { token, new_password: newPassword },
    fallbackErrorMessage: 'Failed to reset password',
  })
}

export async function initiateGoogleLogin(redirectTo = '/') {
  return request('/api/auth/oauth/google/login', {
    method: 'POST',
    body: { redirect_to: redirectTo },
    fallbackErrorMessage: 'Failed to initiate Google login',
  })
}

export async function exchangeOAuthCode(code) {
  return request('/api/auth/oauth/exchange', {
    method: 'POST',
    body: { code },
    fallbackErrorMessage: 'Failed to exchange OAuth code',
  })
}

export async function likeEmoji(emojiId, token) {
  return request(`/api/emojis/${emojiId}/like`, {
    method: 'POST',
    token,
    fallbackErrorMessage: 'Failed to like emoji',
  })
}

export async function unlikeEmoji(emojiId, token) {
  return request(`/api/emojis/${emojiId}/like`, {
    method: 'DELETE',
    token,
    fallbackErrorMessage: 'Failed to unlike emoji',
  })
}

export async function reportEmoji(emojiId, payload, token) {
  return request(`/api/emojis/${emojiId}/reports`, {
    method: 'POST',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to submit report',
  })
}

export async function fetchEmojiComments(emojiId, token, params = {}) {
  return request(`/api/emojis/${emojiId}/comments`, {
    token,
    query: { limit: params.limit, offset: params.offset },
    fallbackErrorMessage: 'Failed to load comments',
  })
}

export async function createEmojiComment(emojiId, payload, token) {
  return request(`/api/emojis/${emojiId}/comments`, {
    method: 'POST',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to post comment',
  })
}

export async function deleteEmojiComment(commentId, token) {
  return request(`/api/comments/${commentId}`, {
    method: 'DELETE',
    token,
    fallbackErrorMessage: 'Failed to delete comment',
  })
}

export async function fetchUserProfile(userId, token) {
  return request(`/api/users/${userId}`, {
    token,
    fallbackErrorMessage: 'Failed to load profile',
  })
}

export async function updateCurrentUserProfile(payload, token) {
  return request('/api/users/me', {
    method: 'PATCH',
    token,
    body: payload,
    fallbackErrorMessage: 'Failed to update profile',
  })
}
