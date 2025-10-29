import { mockEmojis } from '../data/mockEmojis'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export async function fetchEmojis(token) {
  try {
    const response = await fetch(`${API_BASE}/api/emojis`, {
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
    return mockEmojis
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
