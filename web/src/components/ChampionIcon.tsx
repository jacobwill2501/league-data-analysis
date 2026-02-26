import { useState } from 'react'
import Avatar from '@mui/material/Avatar'
import { getDDragonKey } from '../utils/championMapping'

const DDRAGON_VERSION = '16.4.1'
const LOCAL_BASE = `${import.meta.env.BASE_URL}images/champions/`
const CDN_BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img/champion/`

interface Props {
  name: string
}

export function ChampionIcon({ name }: Props) {
  // 0 → try local, 1 → try CDN, 2 → show letter avatar
  const [errorLevel, setErrorLevel] = useState(0)
  const key = getDDragonKey(name)

  const src =
    errorLevel === 0 ? `${LOCAL_BASE}${key}.png`
    : errorLevel === 1 ? `${CDN_BASE}${key}.png`
    : undefined

  const handleError = () => setErrorLevel(prev => Math.min(prev + 1, 2))

  return (
    <Avatar
      src={src}
      alt={name}
      imgProps={{ loading: 'lazy', onError: handleError }}
      sx={{ width: 32, height: 32, fontSize: 12 }}
    >
      {name[0]}
    </Avatar>
  )
}
