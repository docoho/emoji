import { computed, reactive } from 'vue'

function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

const state = reactive({
  token: (() => {
    const t = sessionStorage.getItem('auth_token') ?? ''
    return t && !isTokenExpired(t) ? t : ''
  })(),
  user: null,
})

if (state.token) {
  sessionStorage.setItem('auth_token', state.token)
} else {
  sessionStorage.removeItem('auth_token')
}

// Module-scoped listener: when api.js sees a 401 it dispatches this event,
// and we clear session state. Registered once at module load.
window.addEventListener('auth:unauthorized', () => {
  state.token = ''
  state.user = null
  sessionStorage.removeItem('auth_token')
})

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(state.token))

  const setSession = ({ token, user }) => {
    state.token = token ?? ''
    state.user = user ?? null
    if (state.token) {
      sessionStorage.setItem('auth_token', state.token)
    } else {
      sessionStorage.removeItem('auth_token')
    }
  }

  const signOut = () => {
    setSession({ token: '', user: null })
  }

  const checkExpiry = () => {
    if (state.token && isTokenExpired(state.token)) {
      signOut()
      return true
    }
    return false
  }

  return {
    token: computed(() => state.token),
    user: computed(() => state.user),
    isAuthenticated,
    setSession,
    signOut,
    checkExpiry,
  }
}
