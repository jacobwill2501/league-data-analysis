import type { EloFilter } from '../types/analysis'

const ELO_OPTIONS: { value: EloFilter; label: string }[] = [
  { value: 'emerald_plus', label: 'Emerald+' },
  { value: 'diamond_plus', label: 'Diamond+' },
  { value: 'diamond2_plus', label: 'Diamond 2+' },
]

interface Props {
  elo: EloFilter
  onEloChange: (elo: EloFilter) => void
  theme: 'dark' | 'light'
  onThemeToggle: () => void
}

export function Header({ elo, onEloChange, theme, onThemeToggle }: Props) {
  return (
    <header className="sticky top-0 z-20 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center gap-4 flex-wrap">
      <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100 shrink-0">
        Champion Mastery Analysis
      </h1>

      <div className="flex gap-1 ml-auto shrink-0">
        {ELO_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => onEloChange(opt.value)}
            className={[
              'px-3 py-1.5 rounded text-sm font-medium transition-colors',
              elo === opt.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700',
            ].join(' ')}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <button
        onClick={onThemeToggle}
        aria-label="Toggle theme"
        className="shrink-0 w-9 h-9 flex items-center justify-center rounded text-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
      >
        {theme === 'dark' ? '☀️' : '🌙'}
      </button>
    </header>
  )
}
