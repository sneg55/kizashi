import { useTheme } from '../lib/theme'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to the ${next} theme`}
      className="data cursor-pointer border border-rule px-2 py-1 text-micro text-ink-soft transition-colors hover:border-rule-strong hover:text-ink"
    >
      {next === 'dark' ? 'dark' : 'light'}
    </button>
  )
}
