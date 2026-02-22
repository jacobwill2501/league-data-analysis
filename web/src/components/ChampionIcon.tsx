import { useState } from 'react'
import { getDDragonKey } from '../utils/championMapping'

const DDRAGON_VERSION = '15.4.1'
const BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img/champion/`

interface Props {
  name: string
}

export function ChampionIcon({ name }: Props) {
  const [error, setError] = useState(false)
  const key = getDDragonKey(name)

  if (error) {
    return (
      <span className="inline-flex items-center justify-center w-8 h-8 rounded bg-gray-200 dark:bg-gray-700 text-[10px] text-gray-500 dark:text-gray-400 shrink-0">
        ?
      </span>
    )
  }

  return (
    <img
      src={`${BASE}${key}.png`}
      alt={name}
      width={32}
      height={32}
      loading="lazy"
      className="rounded shrink-0"
      onError={() => setError(true)}
    />
  )
}
