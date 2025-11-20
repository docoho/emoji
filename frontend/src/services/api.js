import { mockEmojis } from '../data/mockEmojis'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function fetchEmojis(token, params = {}) {
  const queryParams = new URLSearchParams()
  if (params.search) queryParams.append('search', params.search)
  if (params.category) queryParams.append('category', params.category)
  if (params.sort) queryParams.append('sort', params.sort)
  if (params.limit) queryParams.append('limit', params.limit)
  if (params.offset) queryParams.append('offset', params.offset)

  const url = `${API_BASE}/api/emojis${queryParams.toString() ? `?${queryParams}` : ''}`

  try {
    const response = await fetch(url, {
      headers: token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : undefined,
    })
    if (!response.ok) throw new Error('Failed to load emojis')
    return await response.json()
  } catch (error) {
    console.warn('Falling back to mock emojis:', error)
    return { items: mockEmojis, total: mockEmojis.length, limit: 50, offset: 0 }
  }
}

export async function submitEmoji(payload, token) {
  const response = await fetch(`${API_BASE}/api/emojis`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    const message = errorBody.detail ?? 'Failed to submit emoji'
    throw new Error(message)
  }

  return response.json()
}

export async function registerUser(payload) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail ?? 'Registration failed')
  }

  return response.json()
}

export async function loginUser(payload) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail ?? 'Login failed')
  }

  return response.json()
}

export async function fetchCurrentUser(token) {
  if (!token) return null

  const response = await fetch(`${API_BASE}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    return null
  }

  return response.json()
}

export async function updateEmoji(id, payload, token) {
  const response = await fetch(`${API_BASE}/api/emojis/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail ?? 'Failed to update emoji')
  }

  return response.json()
}

export async function deleteEmoji(id, token) {
  const response = await fetch(`${API_BASE}/api/emojis/${id}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail ?? 'Failed to delete emoji')
  }
}

export async function requestPasswordReset(email) {
  const response = await fetch(`${API_BASE}/api/auth/password-reset/request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail ?? 'Failed to request password reset')
  }

  return response.json()
}

export async function confirmPasswordReset(token, newPassword) {
  const response = await fetch(`${API_BASE}/api/auth/password-reset/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token, new_password: newPassword }),
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail ?? 'Failed to reset password')
  }

  return response.json()
}
