import { computed, ref, watchEffect } from 'vue'

const stored = localStorage.getItem('theme')
const theme = ref(stored || 'system')

const systemDark = ref(
  window.matchMedia('(prefers-color-scheme: dark)').matches
)

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  systemDark.value = e.matches
})

export function useTheme() {
  const isDark = computed(() => {
    if (theme.value === 'system') return systemDark.value
    return theme.value === 'dark'
  })

  watchEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
    if (theme.value === 'system') {
      localStorage.removeItem('theme')
    } else {
      localStorage.setItem('theme', theme.value)
    }
  })

  const toggleTheme = () => {
    const cycle = { system: 'light', light: 'dark', dark: 'system' }
    theme.value = cycle[theme.value] ?? 'system'
  }

  return { theme, isDark, toggleTheme }
}
