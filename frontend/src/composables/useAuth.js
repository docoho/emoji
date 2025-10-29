import { computed, reactive } from 'vue'

const state = reactive({
  token: localStorage.getItem('auth_token') ?? '',
  user: null,
})

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(state.token))

  const setSession = ({ token, user }) => {
    state.token = token ?? ''
    state.user = user ?? null
    if (state.token) {
      localStorage.setItem('auth_token', state.token)
    } else {
      localStorage.removeItem('auth_token')
    }
  }

  const signOut = () => {
    setSession({ token: '', user: null })
  }

  return {
    token: computed(() => state.token),
    user: computed(() => state.user),
    isAuthenticated,
    setSession,
    signOut,
  }
}
